"""
Authentication configuration for social media platforms
"""
import os
from typing import Dict, Any, Optional
from enum import Enum


class AuthMode(Enum):
    """Authentication modes"""
    DISABLED = "disabled"       # No authentication
    MANUAL = "manual"          # Manual interactive login
    AUTO = "auto"              # Automatic using saved cookies
    PROMPT = "prompt"          # Ask user when needed


class AuthConfig:
    """
    Configuration class for authentication settings
    """
    
    def __init__(self):
        """Initialize authentication configuration"""
        self.load_from_env()
    
    def load_from_env(self):
        """Load configuration from environment variables"""
        # Authentication mode
        self.auth_mode = AuthMode(
            os.getenv('THREADS_AUTH_MODE', 'prompt').lower()
        )
        
        # Cookie storage settings
        self.cookie_file_path = os.getenv(
            'THREADS_COOKIE_FILE', 
            os.path.expanduser('~/.lottery_web_cookies.json')
        )
        
        # Security settings
        self.cookie_encryption_key = os.getenv(
            'THREADS_COOKIE_KEY',
            None  # Will generate if not provided
        )
        
        # Session settings
        self.session_timeout_hours = int(
            os.getenv('THREADS_SESSION_TIMEOUT', '24')
        )
        
        # Browser settings for manual login
        self.manual_login_timeout = int(
            os.getenv('THREADS_MANUAL_TIMEOUT', '300')  # 5 minutes
        )
        
        # Platform specific settings
        self.threads_login_url = "https://www.threads.com/login"
        self.threads_domains = [
            'threads.com', 
            'www.threads.com',
            'threads.net',
            'www.threads.net'
        ]
    
    def get_config_dict(self) -> Dict[str, Any]:
        """
        Get configuration as dictionary
        
        Returns:
            Dictionary containing all configuration values
        """
        return {
            'auth_mode': self.auth_mode.value,
            'cookie_file_path': self.cookie_file_path,
            'session_timeout_hours': self.session_timeout_hours,
            'manual_login_timeout': self.manual_login_timeout,
            'threads_login_url': self.threads_login_url,
            'threads_domains': self.threads_domains
        }
    
    def is_auth_enabled(self) -> bool:
        """
        Check if authentication is enabled
        
        Returns:
            True if authentication is enabled
        """
        return self.auth_mode != AuthMode.DISABLED
    
    def should_prompt_user(self) -> bool:
        """
        Check if should prompt user for authentication decisions
        
        Returns:
            True if should prompt user
        """
        return self.auth_mode == AuthMode.PROMPT
    
    def is_manual_mode(self) -> bool:
        """
        Check if manual authentication mode is enabled
        
        Returns:
            True if manual mode
        """
        return self.auth_mode == AuthMode.MANUAL
    
    def is_auto_mode(self) -> bool:
        """
        Check if automatic authentication mode is enabled
        
        Returns:
            True if auto mode
        """
        return self.auth_mode == AuthMode.AUTO
    
    def update_mode(self, mode: AuthMode):
        """
        Update authentication mode
        
        Args:
            mode: New authentication mode
        """
        self.auth_mode = mode
    
    @classmethod
    def create_example_env(cls) -> str:
        """
        Create example environment variables configuration
        
        Returns:
            String containing example .env configuration
        """
        return """
# Threads Authentication Configuration
# Available modes: disabled, manual, auto, prompt
THREADS_AUTH_MODE=prompt

# Cookie storage file path
THREADS_COOKIE_FILE=~/.lottery_web_cookies.json

# Session timeout in hours
THREADS_SESSION_TIMEOUT=24

# Manual login timeout in seconds
THREADS_MANUAL_TIMEOUT=300

# Optional: Cookie encryption key (will generate if not provided)
# THREADS_COOKIE_KEY=your_secret_key_here
        """.strip()


# Global configuration instance
auth_config = AuthConfig()