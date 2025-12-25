# AI Voice Agent for Sip-Dialer

## Overview
Add an AI-powered voice agent to handle inbound calls using **only OpenAI APIs** (Whisper, GPT-4o, TTS).

## Architecture (Simple)

```
Inbound Call → PJSUA2 SIP → Audio Buffer → VAD (detect speech end)
                                              ↓
                              ┌───────────────┴───────────────┐
                              │    OpenAI Pipeline            │
                              │  Whisper → GPT-4o → TTS      │
                              └───────────────┬───────────────┘
                                              ↓
                              Audio Response → Play to Caller
```

## Components to Build

### 1. New Module: `backend/dialer/voice_agent/`
| File | Purpose |
|------|---------|
| `session.py` | Main orchestrator - manages conversation loop |
| `vad.py` | Simple energy-based voice activity detection |
| `transcriber.py` | OpenAI Whisper wrapper (speech-to-text) |
| `llm_processor.py` | GPT-4o conversation with function calling |
| `synthesizer.py` | OpenAI TTS with MinIO caching |
| `audio_converter.py` | PCM/ulaw/WAV format conversions |
| `plugins/base.py` | Base class for external API plugins |
| `plugins/customer_lookup.py` | Example: fetch customer data |
| `plugins/transfer_call.py` | Transfer call to human agent |

### 2. Database Models: `backend/app/models/voice_agent.py`
- **VoiceAgentConfig**: System prompt, OpenAI settings, voice, timeouts
- **InboundRoute**: Map DID patterns to agent configs
- **VoiceAgentConversation**: Store transcripts, costs, outcomes

### 3. Modify Existing Files
| File | Change |
|------|--------|
| `dialer/sip_engine/pjsua_client.py` | Add `onIncomingCall` handler |
| `dialer/sip_engine/media_handler.py` | Add audio streaming methods |
| `app/models/call_log.py` | Add `voice_agent_conversation_id` FK |
| `app/config.py` | Add voice agent settings |

### 4. New API Endpoints: `backend/app/api/v1/endpoints/voice_agent.py`
- `POST /voice-agents` - Create agent config
- `GET /voice-agents` - List agent configs
- `PUT /voice-agents/{id}` - Update config
- `POST /inbound-routes` - Create routing rule
- `GET /conversations` - List conversation logs

## Conversation Flow

```python
1. Inbound call arrives → SIP engine answers
2. Play greeting: "Hello, how can I help you today?"
3. Loop:
   a. Listen for speech (VAD detects end of utterance)
   b. Transcribe audio → Whisper API
   c. Process text → GPT-4o (with function calling for external APIs)
   d. If tool call: execute plugin, feed result back to GPT
   e. Synthesize response → TTS API (check cache first)
   f. Play audio to caller
   g. Check for transfer/hangup actions
4. End call, save conversation log
```

## Plugin System (Flexible External API)

```python
class ExternalPlugin(ABC):
    name: str
    description: str
    parameters: List[PluginParameter]

    async def execute(self, params: Dict, context: Dict) -> Dict:
        # Call external API here
        pass

    def to_openai_tool(self) -> Dict:
        # Convert to OpenAI function format
        pass
```

Example usage in GPT:
- User: "What's my account balance?"
- GPT calls: `lookup_customer(phone_number="+15551234567")`
- Plugin fetches from external CRM API
- GPT responds: "Your balance is $150.00"

## Cost Estimate (per 1000 calls, ~3 min avg)

| API | Usage | Cost |
|-----|-------|------|
| Whisper | 3000 min | ~$18 |
| GPT-4o-mini | ~500K tokens | ~$0.30 |
| TTS | ~150K chars | ~$2.25 |
| **Total** | | **~$21/1000 calls** |

## Scaling (10-50 concurrent)

- Use async/await throughout
- Cache TTS responses in MinIO (greetings, common phrases)
- Connection pooling for OpenAI API
- Rate limiting per organization

## Implementation Order

### Step 1: Database & Models
- [ ] Create `voice_agent.py` models
- [ ] Create Alembic migration
- [ ] Add Pydantic schemas

### Step 2: OpenAI Wrappers
- [ ] `transcriber.py` - Whisper integration
- [ ] `synthesizer.py` - TTS with caching
- [ ] `llm_processor.py` - GPT-4o with function calling

### Step 3: Audio Processing
- [ ] `vad.py` - Voice activity detection
- [ ] `audio_converter.py` - Format conversions
- [ ] Modify `media_handler.py` for streaming

### Step 4: Voice Agent Core
- [ ] `session.py` - Main conversation orchestrator
- [ ] Modify `pjsua_client.py` for inbound calls
- [ ] Integration with existing call logging

### Step 5: Plugin System
- [ ] `plugins/base.py` - Base class
- [ ] `plugins/customer_lookup.py` - Example plugin
- [ ] `plugins/transfer_call.py` - Call transfer

### Step 6: API & Integration
- [ ] REST endpoints for configuration
- [ ] WebSocket events for real-time updates
- [ ] Frontend components (optional)

## Critical Files to Modify

1. `/tmp/Sip-dialer/backend/dialer/sip_engine/pjsua_client.py`
2. `/tmp/Sip-dialer/backend/dialer/sip_engine/media_handler.py`
3. `/tmp/Sip-dialer/backend/app/models/call_log.py`
4. `/tmp/Sip-dialer/backend/app/config.py`

## New Files to Create

```
backend/dialer/voice_agent/
├── __init__.py
├── session.py
├── vad.py
├── transcriber.py
├── llm_processor.py
├── synthesizer.py
├── audio_converter.py
└── plugins/
    ├── __init__.py
    ├── base.py
    ├── customer_lookup.py
    └── transfer_call.py

backend/app/models/voice_agent.py
backend/app/schemas/voice_agent.py
backend/app/api/v1/endpoints/voice_agent.py
backend/app/services/voice_agent_service.py
backend/app/services/tts_cache_service.py

frontend/src/pages/VoiceAgent/
├── index.tsx                    # Voice Agent dashboard
├── AgentConfigList.tsx          # List all agent configs
├── AgentConfigForm.tsx          # Create/edit agent config
├── InboundRoutes.tsx            # Manage DID routing
├── ConversationLogs.tsx         # View conversation transcripts
└── components/
    ├── SystemPromptEditor.tsx   # Edit system prompt
    ├── PluginConfig.tsx         # Configure plugins
    └── ConversationPlayer.tsx   # Playback with transcript

frontend/src/components/Layout/Sidebar.tsx  # Add "Voice Agent" menu item
```

## Frontend Requirements

### New Menu Item: "Voice Agent"
Add to sidebar navigation with sub-pages:
- **Dashboard** - Active calls, stats, recent conversations
- **Agent Configs** - Create/manage AI agent configurations
- **Inbound Routes** - Map phone numbers to agents
- **Conversations** - Browse transcripts and analytics

### Key UI Components
1. **System Prompt Editor** - Monaco/CodeMirror for editing prompts
2. **Voice Preview** - Test TTS with different voices
3. **Plugin Configuration** - Enable/configure external API plugins
4. **Live Conversation View** - Real-time transcript via WebSocket
5. **Conversation Playback** - Audio player synced with transcript
