"""
OpenAI GPT conversation processor with function calling support.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class PluginResult:
    """Result from a plugin execution."""
    plugin_name: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


class ConversationProcessor:
    """Process conversations using OpenAI GPT with function calling."""

    def __init__(
        self,
        api_key: str,
        system_prompt: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 150,
        temperature: float = 0.7,
        plugins: Optional[List["ExternalPlugin"]] = None
    ):
        """
        Initialize conversation processor.

        Args:
            api_key: OpenAI API key
            system_prompt: System prompt for the conversation
            model: GPT model to use
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-2)
            plugins: List of external plugins for function calling
        """
        self.client = OpenAI(api_key=api_key)
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.plugins = plugins or []

        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []

        # Token tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        # Pending action (e.g., transfer, hangup)
        self._pending_action: Optional[Dict] = None

    @property
    def total_input_tokens(self) -> int:
        """Get total input tokens for cost tracking."""
        return self._total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        """Get total output tokens for cost tracking."""
        return self._total_output_tokens

    @property
    def pending_action(self) -> Optional[Dict]:
        """Get pending action from last tool call."""
        return self._pending_action

    def clear_pending_action(self):
        """Clear pending action."""
        self._pending_action = None

    async def process(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process user input and generate response.

        Args:
            user_input: User's speech transcription
            context: Optional context (caller info, etc.)

        Returns:
            Assistant's response text
        """
        if not user_input or not user_input.strip():
            return ""

        self._pending_action = None

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        try:
            # Build messages
            messages = self._build_messages(context)

            # Prepare tools from plugins
            tools = self._build_tools() if self.plugins else None

            # Call GPT API
            response = await asyncio.to_thread(
                self._call_gpt_api,
                messages,
                tools
            )

            # Track tokens
            if response.usage:
                self._total_input_tokens += response.usage.prompt_tokens
                self._total_output_tokens += response.usage.completion_tokens

            # Handle response
            message = response.choices[0].message

            # Handle tool calls if any
            if message.tool_calls:
                return await self._handle_tool_calls(message, context)

            # Regular response
            assistant_response = message.content or ""
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_response
            })

            return assistant_response

        except Exception as e:
            logger.error(f"GPT processing error: {e}")
            return "I'm sorry, I'm having trouble processing your request. Could you please try again?"

    def _build_messages(self, context: Optional[Dict] = None) -> List[Dict]:
        """Build messages array with system prompt and context."""
        system_content = self.system_prompt

        # Add context to system prompt if provided
        if context:
            context_str = "\n\nCurrent context:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
            system_content += context_str

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self.conversation_history)
        return messages

    def _build_tools(self) -> List[Dict]:
        """Build tools array from plugins."""
        return [plugin.to_openai_tool() for plugin in self.plugins]

    def _call_gpt_api(self, messages: List[Dict], tools: Optional[List[Dict]]):
        """Make synchronous call to GPT API."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self.client.chat.completions.create(**kwargs)

    async def _handle_tool_calls(
        self,
        message,
        context: Optional[Dict]
    ) -> str:
        """
        Handle tool calls from GPT response.

        Args:
            message: GPT response message with tool calls
            context: Conversation context

        Returns:
            Final response after processing tool calls
        """
        # Add assistant message with tool calls to history
        self.conversation_history.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        })

        # Process each tool call
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            logger.info(f"Executing tool: {function_name} with args: {function_args}")

            # Find and execute the plugin
            result = await self._execute_plugin(function_name, function_args, context)

            # Check for special actions
            if result.data.get("action") in ["transfer", "hangup"]:
                self._pending_action = result.data

            # Add tool result to history
            self.conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result.data if result.success else {"error": result.error})
            })

        # Get final response from GPT with tool results
        messages = self._build_messages(context)
        response = await asyncio.to_thread(
            self._call_gpt_api,
            messages,
            None  # No tools on follow-up
        )

        if response.usage:
            self._total_input_tokens += response.usage.prompt_tokens
            self._total_output_tokens += response.usage.completion_tokens

        final_response = response.choices[0].message.content or ""
        self.conversation_history.append({
            "role": "assistant",
            "content": final_response
        })

        return final_response

    async def _execute_plugin(
        self,
        plugin_name: str,
        args: Dict[str, Any],
        context: Optional[Dict]
    ) -> PluginResult:
        """Execute a plugin by name."""
        for plugin in self.plugins:
            if plugin.name == plugin_name:
                try:
                    result = await plugin.execute(args, context or {})
                    return PluginResult(
                        plugin_name=plugin_name,
                        success=True,
                        data=result
                    )
                except Exception as e:
                    logger.error(f"Plugin {plugin_name} error: {e}")
                    return PluginResult(
                        plugin_name=plugin_name,
                        success=False,
                        data={},
                        error=str(e)
                    )

        return PluginResult(
            plugin_name=plugin_name,
            success=False,
            data={},
            error=f"Plugin {plugin_name} not found"
        )

    def get_transcript(self) -> List[Dict[str, str]]:
        """Get conversation transcript (user and assistant messages only)."""
        return [
            msg for msg in self.conversation_history
            if msg["role"] in ("user", "assistant") and "tool_calls" not in msg
        ]

    def reset(self):
        """Reset conversation state."""
        self.conversation_history = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._pending_action = None


# Import ExternalPlugin base class for type hints
from dialer.voice_agent.plugins.base import ExternalPlugin
