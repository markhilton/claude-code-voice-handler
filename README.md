# Claude Code Voice Handler - Real-Time AI Voice Notifications for Claude Code

Transform your Claude Code experience with natural voice announcements! This sophisticated voice notification system provides real-time, context-aware speech output for Claude Code's actions and responses. Perfect for developers who want audio feedback while coding with Claude AI.

**Keywords**: Claude Code voice integration, Claude Code TTS, AI coding assistant voice notifications, Claude API voice output, text-to-speech for Claude, Claude Code hooks, AI pair programming voice

## Why Use Voice Notifications with Claude Code?

Voice notifications enhance your Claude Code workflow by:

- **Staying in the zone** - No need to watch the screen while Claude works
- **Multi-tasking** - Listen to Claude's progress while reviewing other code
- **Accessibility** - Audio feedback for visual accessibility needs
- **Ambient awareness** - Know when Claude needs your input without constant monitoring
- **Productivity boost** - Audio cues for task completions and approval requests

## Features

- **Natural Voice Output**: Uses OpenAI's TTS API for lifelike speech with 6 voice options
- **Smart Text Compression**: Uses GPT-4o-mini to automatically condense verbose responses for natural speech
- **Multiple Personalities**: Choose from butler, casual, or friendly professional modes
- **Personalized Interactions**: Supports user nicknames and personality-based responses
- **Context-Aware Announcements**: Intelligent messages based on Claude's specific actions and tools
- **Todo Task Tracking**: Announces task completions when using TodoWrite tool
- **Approval Request Detection**: Immediately alerts when Claude needs permission for actions
- **Time-Aware Greetings**: Contextual greetings based on time of day
- **Task Summary Generation**: Summarizes completed operations at session end
- **Duplicate Prevention**: Smart deduplication to avoid repeated announcements
- **Rate Limiting**: Prevents announcement spam for repetitive tool usage
- **File Type Recognition**: Announces file types when editing (e.g., "Editing Python file")
- **Transcript Reading**: Extracts and announces Claude's actual responses
- **Automatic Fallback**: Seamlessly falls back to system TTS when OpenAI is unavailable
- **Cross-Platform**: Works on macOS (say), Linux (espeak), and Windows (SAPI)

## Quick Start - 2 Minute Setup

Get voice notifications working in just 2 steps:

```bash
# Step 1: Clone to Claude hooks directory
git clone https://github.com/markhilton/claude-code-voice-handler ~/.claude/hooks/voice_notifications

# Step 2: Add your OpenAI API key (optional, for best voices)
export OPENAI_API_KEY='your-api-key-here'
```

That's it! The system auto-configures on first run. See detailed installation below for customization.

## Installation

### Prerequisites

1. **uv** - The fast Python package manager (installs automatically with Claude Code)

   ```bash
   # If you don't have uv installed:
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **OpenAI API Key** (Optional - for natural voices)
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```
   Add to your shell profile (`.zshrc`, `.bashrc`) to persist.

### One-Step Setup

Clone the repository directly into your Claude Code hooks directory:

```bash
git clone https://github.com/markhilton/claude-code-voice-handler ~/.claude/hooks/voice_notifications
```

**That's it!** No additional setup required. The `uv` package manager will automatically handle all dependencies on first run.

### Configure Claude Code

Add these hooks to your Claude Code settings (`~/.claude/settings.json` or project-specific `.claude/settings.local.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/hooks/voice_notifications/voice_handler.py --hook PreToolUse"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/hooks/voice_notifications/voice_handler.py --hook PostToolUse"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/hooks/voice_notifications/voice_handler.py --hook Stop"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/hooks/voice_notifications/voice_handler.py --hook UserPromptSubmit"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/hooks/voice_notifications/voice_handler.py --hook Notification"
          }
        ]
      }
    ]
  }
}
```

**Note**: The hook names are case-sensitive. Additional hooks like `SessionStart`, `SubagentStop`, and `PreCompact` can be added following the same pattern if desired.

## Configuration

Edit `config.json` to customize the voice handler:

### TTS Provider

```json
{
  "voice_settings": {
    "tts_provider": "openai", // or "system" for OS default
    "openai_voice": "nova" // OpenAI voice selection
  }
}
```

### Available OpenAI Voices

- **nova**: Natural and warm (recommended)
- **alloy**: Neutral and balanced
- **echo**: Smooth and articulate
- **fable**: Expressive British accent
- **onyx**: Deep and authoritative
- **shimmer**: Gentle and soothing

### Personality Modes

Set the personality mode and user nickname in config.json:

```json
{
  "voice_settings": {
    "personality": "butler", // Options: butler, casual, friendly_professional
    "user_nickname": "Mark" // Your name for personalized announcements
  }
}
```

Each personality mode affects:

- **Greetings**: Time-aware and personalized with nickname
- **Acknowledgments**: Style of confirming actions
- **Completions**: How tasks are summarized
- **Approval Requests**: Tone when asking for permission
- **Speech Formality**: Overall tone and word choice

Examples:

- **Butler**: "Very well, Mark. I shall attend to your request immediately"
- **Casual**: "Hey Mark, on it"
- **Friendly Professional**: "Good morning, Mark. Processing your request"

### Customizing Phrases

Modify the personality modes in config.json:

```json
{
  "personality_modes": {
    "butler": {
      "greetings": ["How may I assist you", "At your command"],
      "acknowledgments": ["Very well", "Certainly"],
      "completions": ["The task is complete", "Your request has been fulfilled"]
    }
  }
}
```

## Usage

### As Claude Code Hooks

Once configured, the voice handler automatically announces:

- Session starts with time-aware greetings
- Tool usage (reading, editing, searching files)
- Command execution
- Task completions with summaries
- Claude's actual responses when sessions end

### Standalone Testing

Test the voice handler directly:

```bash
# Test with a message
python voice_handler.py --message "Test message" --voice nova

# Test specific hook simulation
python voice_handler.py --hook Stop --tool Edit --file example.py
```

### Debug Mode

View debug logs to troubleshoot issues:

```bash
tail -f /tmp/claude_voice_debug.log
```

## File Structure

```
voice_notifications/
├── voice_handler.py       # Main orchestrator - handles hooks and coordinates all modules
├── message_generator.py   # Generates context-aware messages with personality modes
├── tts_provider.py        # TTS abstraction layer for OpenAI and system TTS
├── transcript_reader.py   # Extracts Claude's responses from conversation transcripts
├── state_manager.py       # Manages persistent state and task context tracking
├── logger.py              # Centralized logging system for debugging
├── deduplication.py       # Prevents duplicate announcements
├── speech_lock.py         # Inter-process lock for preventing overlapping speech
├── config.json            # Voice settings, personality modes, and phrases
├── sound_mapping.json     # Tool-to-announcement mappings
├── README.md              # This documentation
└── LICENSE                # MIT license
```

## How It Works

### Architecture

The voice notification system uses a modular architecture:

1. **Hook Processing** (`voice_handler.py`):

   - Receives hook events from Claude Code via stdin
   - Determines which hooks should trigger announcements
   - Routes to appropriate processing methods
   - Manages rate limiting and deduplication

2. **Message Generation** (`message_generator.py`):

   - Creates contextual messages based on hook type and tool
   - Applies personality modes (butler, casual, friendly_professional)
   - Formats task completions and file operations
   - Generates personalized greetings and completions

3. **Text-to-Speech** (`tts_provider.py`):

   - Primary: OpenAI TTS with 6 voice options
   - Compression: Uses GPT-4o-mini to condense verbose text
   - Fallback: System TTS (macOS say, Linux espeak, Windows SAPI)
   - Formats technical text for natural speech

4. **Transcript Processing** (`transcript_reader.py`):

   - Reads Claude's actual responses from transcript files
   - Extracts meaningful summaries from long responses
   - Detects approval requests for immediate alerts
   - Maintains position tracking to avoid re-reading

5. **State Management** (`state_manager.py`):
   - Tracks task context (files created/modified, commands run)
   - Stores todo list state for completion detection
   - Persists state in `/tmp/claude_voice_state.json`
   - Manages initial summary announcement flags

### Hook-Specific Behavior

- **UserPromptSubmit**: Returns personalized acknowledgment with user's nickname
- **PreToolUse**:
  - Announces tool actions ("Reading", "Editing", "Searching")
  - Detects and announces todo completions
  - Rate-limited to prevent spam (3-second interval per tool)
- **PostToolUse**:
  - Reads and announces Claude's responses from transcript
  - Detects approval requests for immediate alerts
  - Announces initial summary after user prompt
- **Stop**: Generates personalized task completion summary
- **Notification**: Alerts for permission requests and waiting for input

### Automatic Setup

The setup is completely automated using `uv`:

1. **Clone & Go**: Just clone the repo to `~/.claude/hooks/voice_notifications`
2. **Auto-Setup**: On first run, `uv` automatically:
   - Creates a virtual environment
   - Installs all dependencies from inline script metadata
   - Manages Python packages
3. **No Maintenance**: Dependencies are locked and managed by `uv`

## Cost Considerations

When using OpenAI TTS:

- **TTS (tts-1 model)**: $15.00 per 1M characters
- **Text compression (GPT-4o-mini)**: $0.15 per 1M input tokens, $0.60 per 1M output tokens
- **Average cost per announcement**: ~$0.0015 (negligible)
- **Compression Strategy**: Only compresses messages >50 characters to minimize API calls
- **Code Block Handling**: Automatically summarizes code blocks instead of reading syntax

## Fallback Behavior

The handler automatically falls back to system TTS when:

- OpenAI API key is not set
- Network connection fails
- OpenAI API returns an error
- Required Python packages are not installed

System TTS options:

- **macOS**: Uses `say` command with configurable voices
- **Linux**: Uses `espeak`
- **Windows**: Uses Windows Speech API

## Troubleshooting

### No Voice Output

1. Check if OpenAI API key is set:

```bash
echo $OPENAI_API_KEY
```

2. Verify dependencies are installed:

```bash
cd ~/.claude/hooks/voice_notifications
python -c "import openai, sounddevice, soundfile; print('All packages installed')"
```

3. Check the comprehensive debug logs:

```bash
tail -f /tmp/claude_voice.log
```

4. Test the handler directly:

```bash
python voice_handler.py --message "Test announcement" --hook Stop
```

### Debugging Specific Issues

#### Logs Structure

The logging system (`logger.py`) provides detailed debugging:

- Session tracking with timestamps
- Hook event logging with full context
- Message flow tracking
- TTS success/failure events
- Stdin data parsing

Example log entry:

```
2024-01-15 14:32:10 | INFO     | process_pre_tool_use | Hook Event Received | {"hook": "PreToolUse", "tool": "Edit", "file": "test.py"}
```

### First Run Takes Long

This is normal - `uv` is setting up the environment and installing dependencies. Subsequent runs will be instant.

### Voice Not Natural

Ensure `tts_provider` is set to `"openai"` in config.json and your API key is valid.

### Too Verbose/Too Brief

Adjust the text compression by modifying the `compress_text_for_speech` method in voice_handler.py.

## Advanced Customization

### Tool-Specific Announcements

The system provides different announcement styles for different tools:

#### File Operations

- **Read**: Announces "Reading {filename}"
- **Edit/Write/MultiEdit**: Announces "Editing {file_type} {filename}"
  - Recognizes 50+ file types (Python, JavaScript, JSON, etc.)
  - Example: "Editing Python file message_generator.py"

#### Todo Tracking

- Detects when todos are marked as completed
- Announces task completions immediately
- Formats announcements based on task type:
  - "add" → "Added..."
  - "fix" → "Fixed..."
  - "update" → "Updated..."

#### Rate Limiting

- Tools are rate-limited to prevent announcement spam
- Default: 3-second minimum interval between same tool announcements
- TodoWrite completions always announce (no rate limiting)

### Silencing Specific Tools

Add tool names to the `silent_tools` list in voice_handler.py:

```python
self.silent_tools = ["LS", "Glob"]  # Won't announce these tools
```

### Custom Tool Phrases

Modify `tool_action_phrases` in message_generator.py:

```python
self.tool_action_phrases = {
    "Read": "Reading",
    "Edit": "Editing",
    "Write": "Writing",
    "Grep": "Searching",
    "Bash": "Running",
    # Add or modify phrases
}
```

### Active Voice Hooks

Control which hooks trigger announcements in voice_handler.py:

```python
self.active_voice_hooks = {
    "UserPromptSubmit",  # Initial acknowledgment
    "PreToolUse",        # Tool start announcements
    "PostToolUse",       # Response announcements
    "Stop",              # Completion summary
    "Notification"       # Permission requests
}
```

### Context Tracking

The handler tracks extensive context:

- Files created/modified/deleted
- Commands executed
- Searches performed
- Todo list states
- Last speech timestamps
- Transcript read positions
- Initial summary flags

This data persists in `/tmp/claude_voice_state.json` during a session.

### Speech Timing Control

```python
# In voice_handler.py
self.min_speech_delay = 1.0  # Minimum seconds between announcements
self.min_tool_announcement_interval = 3.0  # Minimum seconds between same tool
```

### Message Deduplication

The deduplication system prevents repeated announcements:

- Exact message matching
- Hash-based similarity detection
- 5-second cache duration by default
- Configurable in deduplication.py

## Compatibility

- **Claude Code**: Fully compatible with Claude Code hooks system
- **Operating Systems**: macOS, Linux, Windows
- **Python**: 3.8+ (managed automatically by uv)
- **Claude Code Version**: Works with all versions supporting hooks

## Performance & Resource Usage

- **Lightweight**: Minimal CPU usage, runs only when Claude performs actions
- **Fast**: Sub-second response time for announcements
- **Efficient**: Smart caching prevents redundant API calls
- **Low Cost**: ~$0.0015 per announcement with OpenAI TTS

## Community & Support

- **Issues**: [Report bugs or request features](https://github.com/markhilton/claude-code-voice-handler/issues)
- **Discussions**: Share your voice configurations and personality modes
- **Pull Requests**: Contributions welcome!

## Related Projects

Looking for more Claude Code enhancements? Check out:

- [Claude Code Extensions](https://github.com/anthropics/claude-code)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)

## Contributing

We welcome contributions! Whether it's:

- New personality modes
- Additional language support
- Voice provider integrations
- Bug fixes and improvements

Please feel free to submit issues and pull requests!

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic
- Uses OpenAI's TTS API for natural speech synthesis
- Inspired by the developer community's need for better AI pair programming experiences

## Tags

`claude-desktop` `claude-code` `voice-notifications` `text-to-speech` `tts` `ai-assistant` `developer-tools` `productivity` `accessibility` `openai-tts` `hooks` `claude-api` `voice-integration` `ai-coding` `pair-programming`
