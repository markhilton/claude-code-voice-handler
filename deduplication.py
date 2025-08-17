#!/usr/bin/env python3
"""
Message deduplication to prevent repeated announcements.
"""

import hashlib
import time


class MessageDeduplicator:
    """
    Prevents duplicate announcements within a time window.
    """
    
    def __init__(self, cache_duration=5.0):
        """
        Initialize the deduplicator.
        
        Args:
            cache_duration (float): Seconds to keep announcements in cache
        """
        self.cache_duration = cache_duration
        self.recent_announcements = []  # List of (message_hash, timestamp) tuples
        self.last_announcement_text = ""  # Track last spoken text
    
    def is_duplicate(self, message):
        """
        Check if this message is a duplicate of a recent announcement.
        
        Args:
            message (str): The message to check
            
        Returns:
            bool: True if this is a duplicate, False otherwise
        """
        if not message:
            return False
            
        # Check for exact duplicate of last announcement
        if message == self.last_announcement_text:
            return True
        
        # Create hash of the message for comparison
        message_hash = hashlib.md5(message.encode()).hexdigest()
        current_time = time.time()
        
        # Clean up old announcements from cache
        self.recent_announcements = [
            (h, t) for h, t in self.recent_announcements 
            if current_time - t < self.cache_duration
        ]
        
        # Check if this message hash is in recent announcements
        for recent_hash, _ in self.recent_announcements:
            if recent_hash == message_hash:
                return True
        
        # Not a duplicate - add to cache
        self.recent_announcements.append((message_hash, current_time))
        self.last_announcement_text = message
        return False
    
    def clear_cache(self):
        """Clear the deduplication cache."""
        self.recent_announcements.clear()
        self.last_announcement_text = ""