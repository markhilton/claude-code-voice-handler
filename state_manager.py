#!/usr/bin/env python3
"""
State management for voice handler - handles persistent state and context tracking.
"""

import json
from pathlib import Path
from datetime import datetime


class StateManager:
    """
    Manages persistent state and task context across multiple hook invocations.
    """
    
    def __init__(self, state_file_path='/tmp/claude_voice_state.json'):
        """
        Initialize state manager with file path.
        
        Args:
            state_file_path (str): Path to state file
        """
        self.state_file = Path(state_file_path)
        self.state = self.load_state()
        self.task_context = self.state.get('task_context', self.get_default_task_context())
        self.last_speech_time = self.state.get('last_speech_time', 0)
        self.last_todos = self.state.get('last_todos', [])
        self.initial_summary_announced = self.state.get('initial_summary_announced', False)
        self.current_session_id = self.state.get('current_session_id', None)
    
    def get_default_task_context(self):
        """
        Initialize a fresh task context for tracking operations.
        
        Returns:
            dict: Empty task context with tracking arrays
        """
        return {
            "files_created": [],
            "files_modified": [],
            "files_deleted": [],
            "commands_run": [],
            "searches_performed": [],
            "start_time": datetime.now().isoformat(),
            "operations_count": 0
        }
    
    def load_state(self):
        """
        Load persistent state from temporary storage.
        
        Returns:
            dict: Saved state or default state if none exists
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    # Clean up old transcript positions (older than 7 days)
                    if 'transcript_positions' in state:
                        state['transcript_positions'] = self.clean_old_positions(state['transcript_positions'])
                    return state
            except:
                pass
        return {
            'transcript_positions': {},
            'task_context': self.get_default_task_context()
        }
    
    def clean_old_positions(self, positions):
        """
        Clean up transcript position tracking.
        
        Args:
            positions (dict): Current transcript positions
            
        Returns:
            dict: Cleaned positions dictionary
        """
        cleaned = {}
        for path, pos in positions.items():
            if Path(path).exists():
                cleaned[path] = pos
        return cleaned
    
    def save_state(self):
        """
        Persist current state to temporary storage.
        """
        self.state['task_context'] = self.task_context
        self.state['last_speech_time'] = self.last_speech_time
        self.state['last_todos'] = self.last_todos
        self.state['initial_summary_announced'] = self.initial_summary_announced
        self.state['current_session_id'] = self.current_session_id
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            # If /tmp/ write fails, silently continue (non-critical)
            pass
    
    def update_context(self, hook_type, tool_name=None, file_path=None, **kwargs):
        """
        Track Claude's operations for context-aware announcements.
        
        Args:
            hook_type (str): Type of hook event
            tool_name (str, optional): Name of tool being used
            file_path (str, optional): Path to file being operated on
            **kwargs: Additional context
        """
        self.task_context["operations_count"] += 1
        
        if tool_name == "Write" and file_path:
            self.task_context["files_created"].append(file_path)
        elif tool_name in ["Edit", "MultiEdit"] and file_path:
            self.task_context["files_modified"].append(file_path)
        elif tool_name == "Bash" and kwargs.get("command"):
            self.task_context["commands_run"].append(kwargs["command"])
        elif tool_name in ["Grep", "Glob", "WebSearch"] and kwargs.get("query"):
            self.task_context["searches_performed"].append(kwargs["query"])
        
        self.save_state()
    
    def reset_task_context(self):
        """Reset task context for new session."""
        self.task_context = self.get_default_task_context()
        self.initial_summary_announced = False
        self.last_todos = []  # Clear todo list from previous session
        # Clear transcript positions for a fresh start
        if 'transcript_positions' in self.state:
            self.state['transcript_positions'] = {}
        self.save_state()
    
    def detect_completed_todos(self, new_todos):
        """
        Detect which todos were marked as completed.
        
        Args:
            new_todos (list): New todo list from stdin data
            
        Returns:
            list: List of completed todo descriptions
        """
        completed = []
        
        # Create lookup of old todos by id
        old_todos_by_id = {todo.get('id'): todo for todo in self.last_todos}
        
        # Check for status changes
        for todo in new_todos:
            todo_id = todo.get('id')
            old_todo = old_todos_by_id.get(todo_id)
            
            if old_todo:
                # Check if status changed from non-completed to completed
                old_status = old_todo.get('status', 'pending')
                new_status = todo.get('status', 'pending')
                
                if old_status != 'completed' and new_status == 'completed':
                    completed.append(todo.get('content', 'task'))
        
        # Update stored todos
        self.last_todos = new_todos
        self.save_state()
        
        return completed