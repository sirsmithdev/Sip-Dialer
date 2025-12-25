"""
Base class for external API plugins.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PluginParameter:
    """Definition of a plugin parameter."""
    name: str
    type: str  # string, number, boolean, integer, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None  # For restricted values


class ExternalPlugin(ABC):
    """
    Base class for external API plugins.

    Plugins allow the voice agent to call external APIs during conversations.
    They are exposed to the LLM via OpenAI function calling.

    Example:
        class WeatherPlugin(ExternalPlugin):
            name = "get_weather"
            description = "Get current weather for a city"
            parameters = [
                PluginParameter("city", "string", "City name", required=True)
            ]

            async def execute(self, params, context):
                city = params["city"]
                # Call weather API...
                return {"temperature": 72, "condition": "sunny"}
    """

    # Plugin metadata (override in subclass)
    name: str = "base_plugin"
    description: str = "Base plugin"
    parameters: List[PluginParameter] = []

    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the plugin with given parameters.

        Args:
            params: Parameters from the LLM function call
            context: Conversation context (caller info, etc.)

        Returns:
            Result dictionary to return to the LLM
        """
        pass

    def to_openai_tool(self) -> Dict[str, Any]:
        """
        Convert to OpenAI function calling format.

        Returns:
            Tool definition for OpenAI API
        """
        properties = {}
        required = []

        for param in self.parameters:
            prop_def = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop_def["enum"] = param.enum

            properties[param.name] = prop_def

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate parameters against plugin definition.

        Args:
            params: Parameters to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        for param in self.parameters:
            if param.required and param.name not in params:
                raise ValueError(f"Missing required parameter: {param.name}")

            if param.name in params:
                value = params[param.name]

                # Type validation
                if param.type == "string" and not isinstance(value, str):
                    raise ValueError(f"Parameter {param.name} must be a string")
                elif param.type == "integer" and not isinstance(value, int):
                    raise ValueError(f"Parameter {param.name} must be an integer")
                elif param.type == "number" and not isinstance(value, (int, float)):
                    raise ValueError(f"Parameter {param.name} must be a number")
                elif param.type == "boolean" and not isinstance(value, bool):
                    raise ValueError(f"Parameter {param.name} must be a boolean")

                # Enum validation
                if param.enum and value not in param.enum:
                    raise ValueError(
                        f"Parameter {param.name} must be one of: {param.enum}"
                    )

        return True
