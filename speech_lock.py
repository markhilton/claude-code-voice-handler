#!/usr/bin/env python3
"""
Speech lock manager to prevent overlapping announcements across processes.
"""

import fcntl
import time
import os
from pathlib import Path
from contextlib import contextmanager


class SpeechLock:
    """
    File-based lock to prevent multiple processes from speaking simultaneously.
    Uses fcntl for proper inter-process locking.
    """
    
    def __init__(self, lock_file="/tmp/claude_voice_speech.lock", timeout=10.0):
        """
        Initialize speech lock.
        
        Args:
            lock_file (str): Path to lock file
            timeout (float): Maximum time to wait for lock
        """
        self.lock_file = Path(lock_file)
        self.timeout = timeout
        self.lock_fd = None
        
        # Ensure lock file exists
        self.lock_file.touch()
    
    @contextmanager
    def acquire(self, min_spacing=1.0):
        """
        Acquire speech lock with context manager.
        
        Args:
            min_spacing (float): Minimum seconds between speech events
            
        Yields:
            None when lock is acquired
        """
        start_time = time.time()
        
        # Open lock file
        self.lock_fd = open(self.lock_file, 'w')
        
        try:
            # Try to acquire exclusive lock with timeout
            while True:
                try:
                    fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break  # Lock acquired
                except IOError:
                    # Lock is held by another process
                    if time.time() - start_time > self.timeout:
                        raise TimeoutError(f"Could not acquire speech lock within {self.timeout}s")
                    time.sleep(0.1)  # Wait a bit before retrying
            
            # Check last speech time from lock file
            last_speech_file = Path("/tmp/claude_voice_last_speech.time")
            if last_speech_file.exists():
                try:
                    with open(last_speech_file, 'r') as f:
                        last_speech_time = float(f.read().strip())
                    
                    # Enforce minimum spacing
                    time_since_last = time.time() - last_speech_time
                    if time_since_last < min_spacing:
                        wait_time = min_spacing - time_since_last
                        time.sleep(wait_time)
                except (ValueError, IOError):
                    pass  # Ignore errors reading time file
            
            # Yield control back to caller with lock held
            yield
            
            # Update last speech time
            with open(last_speech_file, 'w') as f:
                f.write(str(time.time()))
                
        finally:
            # Release lock
            if self.lock_fd:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                self.lock_fd = None