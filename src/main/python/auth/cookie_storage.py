"""
Secure cookie storage and management for authentication
"""
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import base64
import hashlib
from cryptography.fernet import Fernet


class CookieStorage:
    """
    Secure cookie storage with encryption and expiration management
    """
    
    def __init__(self, file_path: str, encryption_key: Optional[str] = None):
        """
        Initialize cookie storage
        
        Args:
            file_path: Path to cookie storage file
            encryption_key: Optional encryption key for cookie security
        """
        self.file_path = Path(file_path).expanduser()
        self.logger = self._setup_logger()
        
        # Setup encryption
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            self.encryption_key = self._generate_key()
        
        self.cipher = Fernet(base64.urlsafe_b64encode(
            hashlib.sha256(self.encryption_key).digest()
        ))
        
        # Ensure directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for cookie storage"""
        logger = logging.getLogger("CookieStorage")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _generate_key(self) -> bytes:
        """Generate a default encryption key based on system info"""
        import platform
        system_info = f"{platform.node()}-{platform.system()}-lottery-web"
        return hashlib.sha256(system_info.encode()).digest()[:32]
    
    def save_cookies(
        self, 
        cookies: List[Dict[str, Any]], 
        domain: str,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Save cookies to storage with encryption
        
        Args:
            cookies: List of cookie dictionaries from Selenium
            domain: Domain the cookies belong to
            user_agent: User agent used during authentication
            
        Returns:
            True if saved successfully
        """
        try:
            # Prepare cookie data
            cookie_data = {
                'domain': domain,
                'saved_at': datetime.now().isoformat(),
                'user_agent': user_agent,
                'cookies': cookies
            }
            
            # Encrypt and save
            json_data = json.dumps(cookie_data)
            encrypted_data = self.cipher.encrypt(json_data.encode())
            
            with open(self.file_path, 'wb') as f:
                f.write(encrypted_data)
            
            self.logger.info(f"Saved {len(cookies)} cookies for domain {domain}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")
            return False
    
    def load_cookies(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Load cookies from storage
        
        Args:
            domain: Domain to load cookies for
            
        Returns:
            Dictionary containing cookies and metadata, or None if not found/expired
        """
        try:
            if not self.file_path.exists():
                self.logger.info("No cookie file found")
                return None
            
            # Read and decrypt
            with open(self.file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            cookie_data = json.loads(decrypted_data.decode())
            
            # Check domain match
            if cookie_data.get('domain') != domain:
                self.logger.warning(f"Domain mismatch: stored {cookie_data.get('domain')}, requested {domain}")
                return None
            
            # Check expiration
            saved_at = datetime.fromisoformat(cookie_data['saved_at'])
            if self._is_expired(saved_at):
                self.logger.info("Stored cookies have expired")
                self.clear_cookies()
                return None
            
            self.logger.info(f"Loaded {len(cookie_data['cookies'])} cookies for domain {domain}")
            return cookie_data
            
        except Exception as e:
            self.logger.error(f"Failed to load cookies: {e}")
            return None
    
    def _is_expired(self, saved_at: datetime, max_age_hours: int = 24) -> bool:
        """
        Check if cookies are expired
        
        Args:
            saved_at: When cookies were saved
            max_age_hours: Maximum age in hours
            
        Returns:
            True if expired
        """
        return datetime.now() - saved_at > timedelta(hours=max_age_hours)
    
    def clear_cookies(self) -> bool:
        """
        Clear stored cookies
        
        Returns:
            True if cleared successfully
        """
        try:
            if self.file_path.exists():
                self.file_path.unlink()
                self.logger.info("Cleared stored cookies")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear cookies: {e}")
            return False
    
    def has_valid_cookies(self, domain: str) -> bool:
        """
        Check if valid cookies exist for domain
        
        Args:
            domain: Domain to check
            
        Returns:
            True if valid cookies exist
        """
        cookie_data = self.load_cookies(domain)
        return cookie_data is not None
    
    def get_cookie_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about stored cookies without loading them
        
        Returns:
            Dictionary with cookie metadata or None
        """
        try:
            if not self.file_path.exists():
                return None
            
            with open(self.file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            cookie_data = json.loads(decrypted_data.decode())
            
            saved_at = datetime.fromisoformat(cookie_data['saved_at'])
            
            return {
                'domain': cookie_data.get('domain'),
                'saved_at': saved_at,
                'cookie_count': len(cookie_data.get('cookies', [])),
                'expired': self._is_expired(saved_at),
                'user_agent': cookie_data.get('user_agent')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cookie info: {e}")
            return None
    
    def update_expiry(self, max_age_hours: int = 24):
        """
        Update the expiry check time
        
        Args:
            max_age_hours: New maximum age in hours
        """
        self.max_age_hours = max_age_hours
    
    def backup_cookies(self, backup_path: Optional[str] = None) -> bool:
        """
        Create a backup of current cookies
        
        Args:
            backup_path: Optional backup file path
            
        Returns:
            True if backup created successfully
        """
        try:
            if not self.file_path.exists():
                self.logger.warning("No cookies to backup")
                return False
            
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = str(self.file_path.parent / f"cookies_backup_{timestamp}.json")
            
            import shutil
            shutil.copy2(self.file_path, backup_path)
            
            self.logger.info(f"Cookies backed up to {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup cookies: {e}")
            return False