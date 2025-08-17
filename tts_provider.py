#!/usr/bin/env python3
"""
Text-to-speech provider abstraction - handles both OpenAI and system TTS.
"""

import os
import subprocess
import platform
import tempfile
import time
from pathlib import Path

# Optional imports for OpenAI TTS
try:
    from openai import OpenAI
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class TTSProvider:
    """
    Manages text-to-speech output with multiple provider support.
    """
    
    def __init__(self, config=None, logger=None):
        """
        Initialize TTS provider with configuration.
        
        Args:
            config (dict): Voice configuration
            logger: Logger instance
        """
        self.config = config or {}
        self.logger = logger
        self.openai_client = None
        
        # Initialize OpenAI client if available and configured
        if OPENAI_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            try:
                self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                if self.logger:
                    self.logger.log_info("OpenAI client initialized successfully")
            except Exception as e:
                if self.logger:
                    self.logger.log_error("Failed to initialize OpenAI client", exception=e)
                self.openai_client = None
    
    def compress_text_for_speech(self, text):
        """
        Use GPT-4o-mini to compress verbose text for natural speech.
        
        Args:
            text (str): Original text to compress
            
        Returns:
            str: Compressed, speech-optimized text
        """
        if not self.openai_client:
            return text
        
        # Skip compression for short messages (under 50 characters)
        # These are already concise and compression may actually expand them
        if len(text) < 50:
            if self.logger:
                self.logger.log_debug(f"Skipping compression for short message ({len(text)} chars)")
            return text
            
        try:
            prompt = f"""You are an assistant that makes long technical responses more concise for voice output.
Your task is to rephrase the following text to be shorter and more conversational,
while preserving all key information. Focus only on the most important details.
Be brief but clear, as this will be spoken aloud.

IMPORTANT HANDLING FOR CODE BLOCKS:
- Do not include full code blocks in your response
- Instead, briefly mention "I've created code for X" or "Here's a script that does Y"
- For large code blocks, just say something like "I've written a Python function that handles user authentication"
- DO NOT attempt to read out the actual code syntax
- Only describe what the code does in 1 sentences maximum

Original text:
{text}

Return only the compressed text, without any explanation or introduction."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1024,
            )
            
            compressed = response.choices[0].message.content
            
            if self.logger:
                self.logger.log_debug(f"Compressed text from {len(text)} to {len(compressed)} chars")
            
            return compressed
            
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error compressing text", exception=e)
            return text
    
    def format_message_for_speech(self, message):
        """
        Format technical text for natural speech output.
        
        Args:
            message (str): Technical message text
            
        Returns:
            str: Speech-formatted message
        """
        # Replace underscores and hyphens
        message = message.replace('_', ' ').replace('-', ' ')
        # Replace file extensions (process .json before .js to avoid conflicts)
        message = message.replace('.py', ' python file')
        message = message.replace('.json', ' JSON file')
        message = message.replace('.js', ' javascript file')
        message = message.replace('.md', ' markdown file')
        return message
    
    def speak_with_openai(self, message, voice="nova"):
        """
        Generate and play speech using OpenAI's TTS API.
        
        Args:
            message (str): Text to speak
            voice (str): OpenAI voice selection
            
        Returns:
            bool: True if successful, False if failed
        """
        if not self.openai_client:
            if self.logger:
                self.logger.log_debug("OpenAI client not available, falling back to system TTS")
            return False
        
        # Skip very short messages (under 3 characters) as they're likely not meaningful
        if len(message.strip()) < 3:
            if self.logger:
                self.logger.log_debug(f"Skipping very short message: '{message}'")
            return True  # Return true to avoid fallback
            
        try:
            # Log original message
            if self.logger:
                self.logger.log_info(f"OpenAI TTS Original text: '{message}'")
            
            # Compress the message for better speech
            compressed_message = self.compress_text_for_speech(message)
            
            # Log compressed message if different from original
            if self.logger:
                if compressed_message != message:
                    self.logger.log_info(f"OpenAI TTS Compressed text: '{compressed_message}'")
                else:
                    self.logger.log_debug("OpenAI TTS: No compression needed (message unchanged)")
                self.logger.log_debug(f"Using OpenAI TTS with voice: {voice}")
            
            # Generate speech
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=compressed_message,
                speed=1.0,
            )
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                # Write the audio content to file
                for chunk in response.iter_bytes():
                    temp_file.write(chunk)
            
            # Play audio
            data, samplerate = sf.read(temp_filename)
            sd.play(data, samplerate)
            sd.wait()
            
            # Clean up
            os.unlink(temp_filename)
            
            if self.logger:
                self.logger.log_tts_event("OpenAI", True, voice=voice, text=compressed_message)
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.log_tts_event("OpenAI", False, voice=voice, error=str(e))
            return False
    
    def speak_with_system(self, message, voice=None):
        """
        Use system TTS (macOS say, Linux espeak, Windows SAPI).
        
        Args:
            message (str): Text to speak
            voice (str, optional): System voice selection
        """
        system = platform.system()
        
        if not voice:
            voice = self.config.get("voice_settings", {}).get("default_voice", "Samantha")
        
        try:
            if system == "Darwin":  # macOS
                cmd = ["say", "-v", voice]
                # Add speech rate if configured
                rate = self.config.get("voice_settings", {}).get("speech_rate")
                if rate:
                    cmd.extend(["-r", str(rate)])
                cmd.append(message)
                subprocess.run(cmd, check=True)
            elif system == "Linux":
                subprocess.run(["espeak", message], check=True)
            elif system == "Windows":
                ps_command = f'Add-Type -AssemblyName System.speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak("{message}")'
                subprocess.run(["powershell", "-Command", ps_command], check=True)
            
            if self.logger:
                self.logger.log_tts_event("System", True, voice=voice, text=message)
                
        except subprocess.CalledProcessError as e:
            if self.logger:
                self.logger.log_tts_event("System", False, voice=voice, error=str(e))
            raise
    
    def speak(self, message, voice=None):
        """
        Main speech output method with automatic provider selection.
        
        Args:
            message (str): Message to speak
            voice (str, optional): Override voice selection
        """
        # Log the original message before formatting
        if self.logger:
            self.logger.log_debug(f"TTS Input (before formatting): '{message}'")
        
        # Format message
        message = self.format_message_for_speech(message)
        
        # Log the formatted message
        if self.logger:
            self.logger.log_debug(f"TTS Input (after formatting): '{message}'")
        
        # Get TTS provider from config
        tts_provider = self.config.get("voice_settings", {}).get("tts_provider", "system")
        
        # Try OpenAI TTS first if configured
        if tts_provider == "openai" and OPENAI_AVAILABLE:
            openai_voice = voice or self.config.get("voice_settings", {}).get("openai_voice", "nova")
            if self.speak_with_openai(message, openai_voice):
                return
            # Fall back to system TTS if OpenAI fails
            if self.logger:
                self.logger.log_info("Falling back to system TTS")
        
        # Use system TTS
        self.speak_with_system(message, voice)