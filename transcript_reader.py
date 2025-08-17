#!/usr/bin/env python3
"""Transcript reader that extracts Claude's messages from the conversation log."""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
import re

class TranscriptReader:
    def __init__(self, transcript_path, session_id=None):
        self.transcript_path = Path(transcript_path)
        self.session_id = session_id
        self.state_file = Path('/tmp/claude_voice_state.json')
        self.state = self.load_state()
        self.last_positions = self.state.get('transcript_positions', {})
        
        # If we have a session ID and it's different from the stored one, reset positions
        if session_id and self.state.get('current_session_id') != session_id:
            self.last_positions = {}  # Clear all positions for new session
    
    def load_state(self):
        """Load combined state from /tmp/."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'transcript_positions': {},
            'task_context': {}
        }
    
    def save_last_position(self, position):
        """Save the last read position for this transcript."""
        self.last_positions[str(self.transcript_path)] = position
        self.state['transcript_positions'] = self.last_positions
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except:
            # If /tmp/ write fails, silently continue (non-critical)
            pass
    
    def extract_recent_messages(self, hook_type=None, since_position=None):
        """Extract recent Claude messages from the transcript."""
        if not self.transcript_path.exists():
            return []
        
        messages = []
        
        # Determine starting position
        if since_position is not None:
            start_position = since_position
        else:
            start_position = self.last_positions.get(str(self.transcript_path), 0)
        
        current_position = start_position
        
        try:
            with open(self.transcript_path, 'r') as f:
                # Skip to the starting position
                if start_position > 0:
                    f.seek(start_position)
                
                # Read lines without using tell() in the loop
                lines = f.readlines()
                
                for line in lines:
                    current_position += len(line.encode('utf-8'))
                    
                    try:
                        entry = json.loads(line.strip())
                        
                        # Look for assistant messages
                        if entry.get('type') == 'assistant' and 'message' in entry:
                            msg = entry['message']
                            if msg.get('role') == 'assistant' and 'content' in msg:
                                content_list = msg['content']
                                
                                # Extract text content
                                for content_item in content_list:
                                    if content_item.get('type') == 'text':
                                        text = content_item.get('text', '').strip()
                                        if text:
                                            messages.append({
                                                'text': text,
                                                'timestamp': entry.get('timestamp'),
                                                'uuid': entry.get('uuid'),
                                                'position': current_position
                                            })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading transcript: {e}", file=sys.stderr)
        
        # Save the last position we read
        if current_position > start_position:
            self.save_last_position(current_position)
        
        return messages
    
    def get_last_message(self, max_length=350, min_length=50):
        """Get the most recent Claude message with intelligent extraction.
        
        Args:
            max_length: Maximum character length for the message
            min_length: Minimum character length to consider (helps avoid "Done." only)
        """
        messages = self.extract_recent_messages()
        
        if not messages:
            return None
        
        last_msg = messages[-1]['text']
        
        # Clean up the message first
        last_msg = self.clean_message_for_speech(last_msg)
        
        if not last_msg:
            return None
        
        # If message is already short enough, return it
        if len(last_msg) <= max_length:
            return last_msg
        
        # Extract meaningful sentences up to max_length
        extracted = self.extract_meaningful_summary(last_msg, max_length, min_length)
        
        return extracted
    
    def extract_meaningful_summary(self, text, max_length=350, min_length=50):
        """Extract a meaningful summary from text, handling various formats intelligently.
        
        Args:
            text: The full text to summarize
            max_length: Maximum character length
            min_length: Minimum character length to aim for
        """
        # Handle numbered or bulleted lists specially
        # Check if the text contains list items (but not just numbers in sentences)
        list_pattern = r'\n\s*(\d+\.|\*|\-)\s+'
        if re.search(list_pattern, text):
            return self.extract_list_summary(text, max_length)
        
        # Split into sentences with improved regex
        # This handles periods that aren't sentence endings better
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*\n'
        sentences = re.split(sentence_pattern, text)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return text[:max_length-3] + '...' if len(text) > max_length else text
        
        # Build summary by adding sentences until we approach max_length
        summary = ""
        target_length = int(max_length * 0.9)  # Leave some buffer
        
        for i, sentence in enumerate(sentences):
            # Add proper punctuation if missing
            if sentence and not sentence[-1] in '.!?':
                sentence += '.'
            
            # Check if adding this sentence would exceed our target
            potential_summary = summary + (" " if summary else "") + sentence
            
            if len(potential_summary) <= target_length:
                summary = potential_summary
                # Continue adding sentences until we get closer to our target
                # Only stop if we've used a good portion of available space
                if len(summary) >= min_length and len(summary) >= int(target_length * 0.6):
                    # Look ahead - if next sentence is short and fits, include it
                    if i + 1 < len(sentences):
                        next_sentence = sentences[i + 1]
                        if not next_sentence[-1] in '.!?':
                            next_sentence += '.'
                        next_potential = summary + " " + next_sentence
                        if len(next_potential) <= max_length:
                            summary = next_potential
                    break
            else:
                # If first sentence is too long, truncate it
                if not summary:
                    # Try to find a good breaking point
                    break_points = ['. ', ', ', ' - ', ': ']
                    for bp in break_points:
                        if bp in sentence[:target_length]:
                            pos = sentence[:target_length].rfind(bp)
                            summary = sentence[:pos + 1]
                            break
                    else:
                        # No good break point, just truncate
                        summary = sentence[:max_length-3] + '...'
                break
        
        # If we only got a very short summary, try to add more context
        if summary and len(summary) < min_length and len(sentences) > 1:
            # Add part of the next sentence if it helps
            remaining_space = max_length - len(summary) - 1
            if remaining_space > 20 and len(sentences) > 1:
                next_part = sentences[1][:remaining_space-3]
                if len(next_part) > 10:
                    summary += " " + next_part + "..."
        
        return summary if summary else text[:max_length-3] + '...'
    
    def extract_list_summary(self, text, max_length):
        """Extract summary from numbered or bulleted lists.
        
        Ensures we don't cut off in the middle of a list item.
        """
        # First check if there's an intro before the list
        intro = ""
        list_start_pattern = r'\n\s*(\d+\.|\*|\-)\s+'
        match = re.search(list_start_pattern, text)
        if match:
            intro = text[:match.start()].strip()
            list_text = text[match.start():]
        else:
            list_text = text
        
        # Split by list items - handle both newline and inline lists
        # First try newline-separated lists
        if '\n' in list_text:
            list_items = re.split(r'\n\s*(?:\d+\.|\*|\-)\s+', list_text)
        else:
            # Handle inline numbered lists like "1. item 2. item"
            list_items = re.split(r'\s*\d+\.\s+', list_text)
        
        # Clean up items
        list_items = [item.strip() for item in list_items if item.strip()]
        
        # If we have an intro, start with that
        if intro:
            summary = intro
            if not summary.endswith(':'):
                summary += ":"
        else:
            summary = ""
        
        items_included = 0
        items_text = []
        
        for item in list_items:
            # Remove any remaining list markers
            item = re.sub(r'^(\d+\.|\*|\-)\s+', '', item)
            # Remove trailing periods from list items
            item = item.rstrip('.')
            
            if item:
                items_text.append(item)
                items_included += 1
                # Limit to 2-3 items for conciseness
                if items_included >= 2:
                    break
        
        # Format the items
        if items_text:
            if len(items_text) == 1:
                summary += f" {items_text[0]}"
            elif len(items_text) == 2:
                summary += f" {items_text[0]}, {items_text[1].lower()}"
            else:
                summary += f" {items_text[0]}, {items_text[1].lower()}"
            
            # Add "and more" if there are additional items
            remaining = len(list_items) - items_included
            if remaining > 0:
                more_text = f" and {remaining} more"
                if len(summary + more_text) <= max_length:
                    summary += more_text
        
        # Ensure proper ending punctuation
        if summary and not summary[-1] in '.!?':
            summary += '.'
        
        return summary if summary else "Completed tasks"
    
    def clean_message_for_speech(self, text):
        """Clean up message for speech synthesis."""
        # Skip code blocks
        if '```' in text:
            parts = text.split('```')
            # Return first non-code part
            return parts[0].strip()
        
        # Skip JSON responses
        if text.strip().startswith('{') and text.strip().endswith('}'):
            return None
        
        # Skip messages that are mostly paths or technical
        if text.count('/') > 5 or text.count('\\') > 5:
            return None
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)        # Inline code
        
        return text.strip()
    
    def get_messages_since_last_check(self):
        """Get all messages since the last check."""
        messages = self.extract_recent_messages()
        
        cleaned_messages = []
        for msg in messages:
            cleaned_text = self.clean_message_for_speech(msg['text'])
            if cleaned_text:
                cleaned_messages.append(cleaned_text)
        
        return cleaned_messages
    
    def detect_approval_request(self, text):
        """
        Detect if a message contains an approval/confirmation request.
        
        Args:
            text (str): Message text to check
            
        Returns:
            bool: True if approval request detected
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Patterns that indicate approval needed
        approval_patterns = [
            "would you like",
            "should i proceed",
            "shall i continue",
            "do you want",
            "is this okay",
            "confirm",
            "approve",
            "permission to",
            "may i",
            "can i proceed",
            "before i continue",
            "do you approve",
            "is it okay to",
            "should i go ahead",
            "ready to proceed",
            "waiting for your",
            "need your approval",
            "requires your approval",
            "please confirm",
            "yes or no",
            "y/n",
            "(y/n)",
            "[y/n]",
            "proceed with",
            "continue with",
            "allow me to",
            "i'll need to",
            "i need to",
            "about to",
            "going to make",
            "will make the following",
            "before making",
            "requires permission",
            "awaiting confirmation",
            "please respond",
            "your response",
            "let me know if",
            "if you'd like me to"
        ]
        
        return any(pattern in text_lower for pattern in approval_patterns)

def main():
    parser = argparse.ArgumentParser(description="Extract Claude messages from transcript")
    parser.add_argument("--transcript", required=True, help="Path to transcript file")
    parser.add_argument("--mode", choices=['last', 'recent', 'all'], default='last',
                        help="Mode: last (most recent), recent (since last check), all")
    parser.add_argument("--max-length", type=int, default=200,
                        help="Maximum message length for speech")
    
    args = parser.parse_args()
    
    reader = TranscriptReader(args.transcript)
    
    if args.mode == 'last':
        message = reader.get_last_message(args.max_length)
        if message:
            print(message)
    elif args.mode == 'recent':
        messages = reader.get_messages_since_last_check()
        for msg in messages:
            print(msg)
            print("---")
    elif args.mode == 'all':
        messages = reader.extract_recent_messages(since_position=0)
        for msg in messages:
            cleaned = reader.clean_message_for_speech(msg['text'])
            if cleaned:
                print(cleaned)
                print("---")

if __name__ == "__main__":
    main()