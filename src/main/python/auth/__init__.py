"""
Authentication module for web scraping
Provides authentication management for social media platforms
"""

from .auth_manager import AuthManager
from .cookie_storage import CookieStorage

__all__ = ['AuthManager', 'CookieStorage']