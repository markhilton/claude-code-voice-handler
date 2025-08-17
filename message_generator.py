#!/usr/bin/env python3
"""
Message generation and personality management for voice notifications.
"""

import random
from pathlib import Path
from datetime import datetime


class MessageGenerator:
    """
    Generates contextual messages with personality modes.
    """
    
    def __init__(self, config=None, sound_mapping=None, state_manager=None):
        """
        Initialize message generator.
        
        Args:
            config (dict): Voice configuration
            sound_mapping (dict): Sound mapping configuration
            state_manager: StateManager instance for task context
        """
        self.config = config or {}
        self.sound_mapping = sound_mapping or {}
        self.state_manager = state_manager
        
        # Natural action phrases for tools
        self.tool_action_phrases = {
            "Read": "Reading",
            "NotebookRead": "Reading notebook",
            "Edit": "Editing", 
            "MultiEdit": "Editing",
            "Write": "Writing",
            "NotebookEdit": "Editing notebook",
            "Grep": "Searching",
            "Glob": "Finding files",
            "LS": "Listing",
            "Bash": "Running",
            "Task": "Starting task",
            "WebFetch": "Fetching",
            "WebSearch": "Searching",
            "TodoWrite": "",  # Special handling for todo completions
            "ExitPlanMode": ""
        }
    
    def get_personality_mode(self):
        """
        Retrieve the active personality mode configuration.
        
        Returns:
            dict: Personality phrases
        """
        personality = self.config.get("voice_settings", {}).get("personality", "friendly_professional")
        return self.config.get("personality_modes", {}).get(personality, {})
    
    def get_time_aware_greeting(self, include_name=False):
        """
        Generate a contextual greeting based on current time.
        
        Args:
            include_name (bool): Whether to include user's nickname
            
        Returns:
            str: Time-appropriate greeting
        """
        hour = datetime.now().hour
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 17:
            period = "afternoon"
        elif 17 <= hour < 21:
            period = "evening"
        else:
            period = "night"
        
        greetings = self.config.get("time_aware_greetings", {}).get(period, ["Hello"])
        greeting = random.choice(greetings)
        
        # Add personalized name if requested
        if include_name:
            user_nickname = self.config.get("voice_settings", {}).get("user_nickname")
            if user_nickname:
                greeting = f"{greeting}, {user_nickname}"
        
        return greeting
    
    def get_task_summary(self):
        """
        Create a summary of operations performed during the CURRENT session only.
        
        Returns:
            str: Human-readable task summary or None if no operations
        """
        if not self.state_manager:
            return None
            
        task_context = self.state_manager.task_context
        
        # Check operations count - if zero, this is likely a fresh session
        if task_context.get("operations_count", 0) == 0:
            return None  # Don't announce anything for empty sessions
        
        summary_parts = []
        
        # Count operations
        created = len(set(task_context.get("files_created", [])))
        modified = len(set(task_context.get("files_modified", [])))
        commands = len(task_context.get("commands_run", []))
        searches = len(task_context.get("searches_performed", []))
        
        summaries = self.config.get("task_summaries", {})
        
        if created > 0:
            templates = summaries.get("file_operations", {}).get("created", ["Created files"])
            summary_parts.append(random.choice(templates).format(count=created))
        
        if modified > 0:
            templates = summaries.get("file_operations", {}).get("modified", ["Modified files"])
            summary_parts.append(random.choice(templates).format(count=modified))
        
        if commands > 0:
            summary_parts.append(f"Ran {commands} commands")
        
        if searches > 0:
            summary_parts.append(f"Performed {searches} searches")
        
        # Only return summary if we actually did something
        if summary_parts:
            return ". ".join(summary_parts)
        
        return None  # Return None for empty sessions instead of generic message
    
    def get_contextual_message(self, hook_type, tool_name=None, file_path=None, **kwargs):
        """
        Generate context-appropriate announcement message.
        
        Args:
            hook_type (str): Type of hook event
            tool_name (str, optional): Tool being executed
            file_path (str, optional): File being operated on
            **kwargs: Additional context
            
        Returns:
            str: Contextual announcement message
        """
        personality = self.get_personality_mode()
        contextual = self.config.get("contextual_phrases", {})
        
        # Special handling for different scenarios
        if hook_type == "UserPromptSubmit":
            # Don't return a greeting - we'll speak the initial summary instead
            return None
        
        # Handle PreToolUse with natural action phrases
        if hook_type == "PreToolUse" and tool_name:
            if tool_name in self.tool_action_phrases:
                return self.tool_action_phrases[tool_name]
        
        if hook_type == "Stop":
            # Get summary before clearing (returns None if no operations)
            summary = self.get_task_summary()
            # Don't reset here - let UserPromptSubmit handle reset for new sessions
            # This preserves context if user continues in same session
            return summary  # Can be None, which is handled by caller
        
        # Tool-specific messages
        if tool_name:
            if tool_name in ["Read", "NotebookRead"] and file_path:
                templates = contextual.get("examining_file", ["Looking at file"])
                filename = Path(file_path).name if file_path else "file"
                return random.choice(templates).format(filename=filename)
            
            elif tool_name in ["Edit", "Write", "MultiEdit"] and file_path:
                templates = contextual.get("making_changes", ["Editing file"])
                filename = Path(file_path).name if file_path else "file"
                return random.choice(templates).format(filename=filename)
            
            elif tool_name in ["Grep", "Glob", "WebSearch"]:
                templates = contextual.get("searching", ["Searching"])
                query = kwargs.get("query", "items")
                return random.choice(templates).format(query=query)
            
            elif tool_name == "Bash":
                templates = contextual.get("running_command", ["Running command"])
                command = kwargs.get("command", "command")
                # Shorten long commands
                if len(command) > 30:
                    command = command[:27] + "..."
                return random.choice(templates).format(command=command)
        
        # Check sound mapping for fallback
        return self.get_mapped_message(hook_type, tool_name)
    
    def get_mapped_message(self, hook_type, tool_name=None):
        """
        Fallback message retrieval from sound mapping configuration.
        
        Args:
            hook_type (str): Hook event type
            tool_name (str, optional): Tool name
            
        Returns:
            str: Mapped message or default notification
        """
        if tool_name:
            tools = self.sound_mapping.get("tools", {})
            if tool_name in tools:
                tool_msg = tools[tool_name]
                return random.choice(tool_msg) if isinstance(tool_msg, list) else tool_msg
        
        hook_events = self.sound_mapping.get("hook_events", {})
        if hook_type in hook_events:
            hook_msg = hook_events[hook_type]
            if isinstance(hook_msg, list):
                return random.choice(hook_msg)
            return hook_msg
        
        return "Claude Code notification"
    
    def apply_personality_to_message(self, message, hook_type="Stop"):
        """
        Enhance Claude's actual output with personality-specific modifications.
        
        Args:
            message (str): Original message from Claude
            hook_type (str): Hook context for personality application
            
        Returns:
            str: Personality-enhanced message
        """
        personality = self.get_personality_mode()
        message_lower = message.lower()
        
        # Check if it's a completion message
        completion_indicators = ['done', 'complete', 'finished', 'fixed', 'updated', 'created', 'implemented']
        is_completion = any(indicator in message_lower for indicator in completion_indicators)
        
        # Check if it's an acknowledgment
        ack_indicators = ['i\'ll', 'let me', 'i can', 'i will', 'sure', 'yes']
        is_acknowledgment = any(indicator in message_lower for indicator in ack_indicators)
        
        # Apply personality-based modifications
        if hook_type == "Stop" and is_completion:
            # Add a personality-based completion suffix
            completions = personality.get("completions", [])
            if completions and random.random() < 0.3:  # 30% chance
                suffix = random.choice(completions)
                # Don't duplicate if already ends similarly
                if not any(end in message_lower for end in ['done', 'complete', 'finished']):
                    message = f"{message}. {suffix}"
        
        elif is_acknowledgment:
            # For acknowledgments, sometimes prepend a personality phrase
            acks = personality.get("acknowledgments", [])
            if acks and random.random() < 0.2:  # 20% chance
                prefix = random.choice(acks)
                message = f"{prefix}. {message}"
        
        # For butler mode, make it more formal
        current_personality = self.config.get("voice_settings", {}).get("personality", "friendly_professional")
        if current_personality == "butler":
            # Add formal touches
            message = message.replace("I'll", "I shall")
            message = message.replace("I've", "I have")
            message = message.replace("Let me", "Allow me to")
            if random.random() < 0.1:  # 10% chance
                message = f"Very well. {message}"
        
        elif current_personality == "casual":
            # Make it more casual
            if random.random() < 0.15:  # 15% chance
                casual_intros = ["Alright", "Cool", "Okay"]
                message = f"{random.choice(casual_intros)}, {message.lower()}"
        
        return message
    
    def format_todo_completion(self, task):
        """
        Format a todo task completion for announcement.
        
        Args:
            task (str): Task description
            
        Returns:
            str: Formatted completion message
        """
        task_lower = task.lower()
        
        # Convert task description to past tense/completion form
        if task_lower.startswith('add '):
            return f"Added {task[4:]}"
        elif task_lower.startswith('modify '):
            return f"Modified {task[7:]}"
        elif task_lower.startswith('update '):
            return f"Updated {task[7:]}"
        elif task_lower.startswith('create '):
            return f"Created {task[7:]}"
        elif task_lower.startswith('fix '):
            return f"Fixed {task[4:]}"
        elif task_lower.startswith('test '):
            return f"Tested {task[5:]}"
        elif task_lower.startswith('examine '):
            return f"Examined {task[8:]}"
        else:
            # Generic completion message
            return f"Completed: {task}"
    
    def get_personalized_acknowledgment(self):
        """
        Generate a personalized initial acknowledgment with user's name.
        
        Returns:
            str: Personalized acknowledgment message
        """
        user_nickname = self.config.get("voice_settings", {}).get("user_nickname")
        personality = self.get_personality_mode()
        current_personality = self.config.get("voice_settings", {}).get("personality", "friendly_professional")
        
        # Get appropriate acknowledgment based on personality
        if current_personality == "butler":
            if user_nickname:
                return f"Very well, {user_nickname}. I shall attend to your request immediately"
            return "Very well. I shall attend to your request immediately"
        elif current_personality == "casual":
            if user_nickname:
                return f"Hey {user_nickname}, on it"
            return "Hey there, on it"
        else:  # friendly_professional
            if user_nickname:
                greeting = self.get_time_aware_greeting(include_name=False)
                return f"{greeting}, {user_nickname}. Processing your request"
            return "Processing your request"
    
    def get_personalized_completion(self, summary=None):
        """
        Generate a personalized task completion message.
        
        Args:
            summary (str, optional): Task summary to include
            
        Returns:
            str: Personalized completion message or None if no work done
        """
        user_nickname = self.config.get("voice_settings", {}).get("user_nickname")
        personality = self.get_personality_mode()
        current_personality = self.config.get("voice_settings", {}).get("personality", "friendly_professional")
        
        # Get base completion message
        if summary:
            base_message = summary
        else:
            base_message = self.get_task_summary()
        
        # If no work was done (base_message is None), return None to skip announcement
        if not base_message:
            return None
        
        # Add personalized touch based on personality
        if current_personality == "butler":
            if user_nickname:
                return f"{base_message}. Is there anything else I can help you with, {user_nickname}?"
            return f"{base_message}. Is there anything else I can help you with?"
        elif current_personality == "casual":
            if user_nickname:
                return f"{base_message}. All done, {user_nickname}"
            return f"{base_message}. All done"
        else:  # friendly_professional
            if user_nickname:
                return f"{base_message}. Task completed, {user_nickname}"
            return f"{base_message}. Task completed"
    
    def get_approval_request_message(self, tool_name=None):
        """
        Generate a message for approval/confirmation requests.
        
        Args:
            tool_name (str, optional): Name of the tool requiring approval
            
        Returns:
            str: Approval request message with user's name and tool details
        """
        user_nickname = self.config.get("voice_settings", {}).get("user_nickname")
        current_personality = self.config.get("voice_settings", {}).get("personality", "friendly_professional")
        
        # Create specific message based on tool name
        if tool_name:
            # Map tool names to more natural descriptions
            tool_descriptions = {
                "Edit": "edit a file",
                "Write": "write a file", 
                "MultiEdit": "edit multiple sections",
                "NotebookEdit": "edit a notebook",
                "Delete": "delete a file",
                "Move": "move a file",
                "Create": "create a file",
                "Update": "update a file",
                "Bash": "run a command",
                "Execute": "execute code"
            }
            
            action = tool_descriptions.get(tool_name, f"use {tool_name}")
            
            if current_personality == "butler":
                if user_nickname:
                    return f"Pardon me, {user_nickname}, Claude needs your permission to {action}"
                return f"Pardon me, Claude needs your permission to {action}"
            elif current_personality == "casual":
                if user_nickname:
                    return f"Hey {user_nickname}, Claude needs your permission to {action}"
                return f"Hey, Claude needs your permission to {action}"
            else:  # friendly_professional
                if user_nickname:
                    return f"{user_nickname}, Claude needs your permission to {action}"
                return f"Claude needs your permission to {action}"
        
        # Fallback to generic message if no tool name
        if current_personality == "butler":
            if user_nickname:
                return f"Pardon me, {user_nickname}, this action requires your attention"
            return "Pardon me, this action requires your attention"
        elif current_personality == "casual":
            if user_nickname:
                return f"Hey {user_nickname}, this action requires your attention"
            return "Hey, this action requires your attention"
        else:  # friendly_professional
            if user_nickname:
                return f"Hey {user_nickname}, this action requires your attention"
            return "This action requires your attention"
    
    def format_read_announcement(self, file_path):
        """
        Format a Read tool announcement with the filename and type.
        
        Args:
            file_path (str): Full path to the file being read
            
        Returns:
            str: Formatted announcement like "Reading config" for config.json
        """
        from pathlib import Path
        
        # Extract filename and extension
        path = Path(file_path)
        extension = path.suffix.lower().lstrip('.')
        
        # For common programming files, just use the stem to avoid duplicate "file" words
        # when TTS converts extensions like .py to "python file"
        programming_extensions = {'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'go', 'rs', 'rb', 'php', 'swift', 'kt', 'scala'}
        
        if extension in programming_extensions:
            # Use stem only for programming files to avoid "Reading logger.py" becoming "Reading logger python file"
            return f"Reading {path.stem}"
        else:
            # For other files, include the full name
            return f"Reading {path.name}"
    
    def format_edit_announcement(self, file_path):
        """
        Format an Edit/Write tool announcement with the filename and type.
        
        Args:
            file_path (str): Full path to the file being edited
            
        Returns:
            str: Formatted announcement like "Editing Python file message_generator.py"
        """
        from pathlib import Path
        
        # Extract filename and extension
        path = Path(file_path)
        filename = path.name  # Full filename including extension
        extension = path.suffix.lower().lstrip('.')  # Extension without dot
        
        # Map extensions to readable file types
        file_type_map = {
            'py': 'Python file',
            'js': 'JavaScript file',
            'json': 'JSON file',
            'md': 'markdown file',
            'txt': 'text file',
            'yaml': 'YAML file',
            'yml': 'YAML file',
            'tsx': 'TypeScript file',
            'ts': 'TypeScript file',
            'jsx': 'React file',
            'vue': 'Vue file',
            'html': 'HTML file',
            'css': 'CSS file',
            'scss': 'SASS file',
            'sh': 'shell script',
            'bash': 'bash script',
            'xml': 'XML file',
            'toml': 'TOML file',
            'ini': 'config file',
            'cfg': 'config file',
            'env': 'environment file',
            'gitignore': 'gitignore',
            'dockerfile': 'Dockerfile',
            'makefile': 'Makefile',
            'rs': 'Rust file',
            'go': 'Go file',
            'java': 'Java file',
            'c': 'C file',
            'cpp': 'C++ file',
            'h': 'header file',
            'hpp': 'C++ header',
            'rb': 'Ruby file',
            'php': 'PHP file',
            'sql': 'SQL file',
            'r': 'R file',
            'swift': 'Swift file',
            'kt': 'Kotlin file',
            'scala': 'Scala file',
            'lua': 'Lua file',
            'pl': 'Perl file'
        }
        
        # Get file type description
        if extension:
            file_type = file_type_map.get(extension, f'{extension} file')
            # Use stem (filename without extension) when we specify the file type
            # to avoid saying "Python file logger.py" which becomes "Python file logger python file"
            filename_without_ext = path.stem
            return f"Editing {file_type} {filename_without_ext}"
        else:
            return f"Editing {filename}"