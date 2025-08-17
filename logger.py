#!/usr/bin/env python3
"""
Centralized logging system for voice handler debugging with automatic log rotation.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path


class VoiceLogger:
    """
    Centralized logging system for voice handler debugging.
    
    Provides structured logging with levels, timestamps, and context tracking.
    Logs are written to /tmp/claude_voice.log with automatic rotation.
    """
    
    def __init__(self, log_file="/tmp/claude_voice.log", debug_mode=True, max_size_mb=10):
        """
        Initialize the logger with file and console handlers, with automatic rotation.
        
        Args:
            log_file (str): Path to log file in /tmp/
            debug_mode (bool): Enable debug level logging
            max_size_mb (int): Maximum log file size in MB before rotation
        """
        self.log_file = Path(log_file)
        self.debug_mode = debug_mode
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert to bytes
        
        # Check and rotate log file if needed
        self._check_and_rotate_log()
        
        # Configure logger
        self.logger = logging.getLogger("VoiceHandler")
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # File handler with detailed format
        file_handler = logging.FileHandler(self.log_file, mode='a')
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Keep track of session
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_info(f"=== NEW SESSION STARTED: {self.session_id} ===")
    
    def _check_and_rotate_log(self):
        """
        Check log file size and rotate if it exceeds the maximum.
        Keeps one backup file and starts fresh.
        """
        if not self.log_file.exists():
            return
        
        try:
            file_size = self.log_file.stat().st_size
            
            if file_size > self.max_size_bytes:
                # Create backup filename with timestamp
                backup_file = self.log_file.parent / f"{self.log_file.stem}_backup{self.log_file.suffix}"
                
                # Remove old backup if it exists
                if backup_file.exists():
                    backup_file.unlink()
                
                # Move current log to backup
                self.log_file.rename(backup_file)
                
                # Create new empty log file
                self.log_file.touch()
                
                # Log rotation event to new file
                with open(self.log_file, 'w') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | INFO | Log rotated (previous size: {file_size / 1024 / 1024:.2f}MB)\n")
        except Exception as e:
            # If rotation fails, continue without interrupting the service
            pass
    
    def log_debug(self, message, **context):
        """Log debug level message with optional context."""
        if context:
            message = f"{message} | Context: {json.dumps(context, default=str)}"
        self.logger.debug(message)
    
    def log_info(self, message, **context):
        """Log info level message with optional context."""
        # Periodically check log size (every 100 log entries)
        if hasattr(self, '_log_count'):
            self._log_count += 1
            if self._log_count % 100 == 0:
                self._check_and_rotate_log()
        else:
            self._log_count = 1
        
        if context:
            message = f"{message} | {json.dumps(context, default=str)}"
        self.logger.info(message)
    
    def log_warning(self, message, **context):
        """Log warning level message with optional context."""
        if context:
            message = f"{message} | Context: {json.dumps(context, default=str)}"
        self.logger.warning(message)
    
    def log_error(self, message, exception=None, **context):
        """Log error level message with exception details."""
        import traceback
        if exception:
            message = f"{message} | Exception: {str(exception)}"
            if self.debug_mode:
                message += f"\nTraceback:\n{traceback.format_exc()}"
        if context:
            message = f"{message} | Context: {json.dumps(context, default=str)}"
        self.logger.error(message)
    
    def log_hook_event(self, hook_type, tool=None, stdin_data=None, **kwargs):
        """Log hook event with structured data."""
        event_data = {
            "hook": hook_type,
            "tool": tool,
            "file": kwargs.get("file"),
            "command": kwargs.get("command"),
            "query": kwargs.get("query")
        }
        # Remove None values
        event_data = {k: v for k, v in event_data.items() if v is not None}
        
        # Log additional stdin data if present
        if stdin_data:
            if isinstance(stdin_data, dict):
                event_data["stdin_keys"] = list(stdin_data.keys())
                # Log specific important fields
                if "tool_name" in stdin_data:
                    event_data["stdin_tool"] = stdin_data["tool_name"]
                if "tool_input" in stdin_data:
                    event_data["has_tool_input"] = True
                if "tool_output" in stdin_data:
                    event_data["has_tool_output"] = True
                if "transcript_path" in stdin_data:
                    event_data["has_transcript"] = True
            else:
                event_data["stdin_type"] = type(stdin_data).__name__
        
        self.log_info(f"Hook Event Received", **event_data)
    
    def log_message_flow(self, stage, message=None, **details):
        """Log the message generation and processing flow."""
        log_msg = f"Message Flow: {stage}"
        if message:
            # Truncate long messages for readability
            display_msg = message[:100] + "..." if len(message) > 100 else message
            log_msg += f" - '{display_msg}'"
        self.log_info(log_msg, **details)
    
    def log_tts_event(self, provider, success, voice=None, error=None, text=None):
        """Log TTS operations with optional text content."""
        if success:
            log_data = {"voice": voice}
            if text:
                # Truncate very long text for logging
                log_data["spoken_text"] = text[:200] + "..." if len(text) > 200 else text
            self.log_info(f"TTS Success: {provider}", **log_data)
        else:
            self.log_warning(f"TTS Failed: {provider}", voice=voice, error=str(error))
    
    def log_stdin_data(self, data):
        """Log stdin data received from Claude Code."""
        if isinstance(data, dict):
            self.log_debug("Stdin data received (JSON)", keys=list(data.keys()))
        elif data:
            truncated = data[:200] + "..." if len(data) > 200 else data
            self.log_debug(f"Stdin data received (text): {truncated}")
        else:
            self.log_debug("No stdin data received")


# Initialize global logger
logger = VoiceLogger()