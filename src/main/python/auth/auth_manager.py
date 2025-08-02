"""
Authentication manager for handling login and session management
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .cookie_storage import CookieStorage
from ..config.auth_config import AuthConfig, AuthMode


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass


class AuthManager:
    """
    Manages authentication for social media platforms
    """
    
    def __init__(self, config: Optional[AuthConfig] = None):
        """
        Initialize authentication manager
        
        Args:
            config: Authentication configuration (uses default if None)
        """
        from ..config.auth_config import auth_config
        self.config = config or auth_config
        
        self.logger = self._setup_logger()
        self.cookie_storage = CookieStorage(
            file_path=self.config.cookie_file_path,
            encryption_key=self.config.cookie_encryption_key
        )
        
        # Authentication state
        self.is_authenticated = False
        self.current_domain = None
        self.last_auth_check = None
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for auth manager"""
        logger = logging.getLogger("AuthManager")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def authenticate_for_url(self, driver, url: str) -> bool:
        """
        Authenticate for accessing a specific URL
        
        Args:
            driver: Selenium WebDriver instance
            url: URL to authenticate for
            
        Returns:
            True if authentication successful or not needed
        """
        # Check if authentication is disabled
        if not self.config.is_auth_enabled():
            self.logger.info("Authentication is disabled")
            return True
        
        # Determine domain
        domain = self._extract_domain(url)
        if not domain:
            self.logger.warning(f"Could not extract domain from URL: {url}")
            return True
        
        # Check if we need to authenticate for this domain
        if not self._needs_authentication(domain):
            self.logger.info(f"No authentication needed for domain: {domain}")
            return True
        
        self.current_domain = domain
        
        # Try different authentication methods based on configuration
        if self.config.is_auto_mode():
            return self._auto_authenticate(driver, domain)
        elif self.config.is_manual_mode():
            return self._manual_authenticate(driver, domain)
        elif self.config.should_prompt_user():
            return self._prompt_and_authenticate(driver, domain)
        else:
            self.logger.info("Authentication mode not configured")
            return True
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None
    
    def _needs_authentication(self, domain: str) -> bool:
        """
        Check if domain requires authentication
        
        Args:
            domain: Domain to check
            
        Returns:
            True if authentication is required
        """
        # Currently only supporting Threads
        return any(threads_domain in domain for threads_domain in self.config.threads_domains)
    
    def _auto_authenticate(self, driver, domain: str) -> bool:
        """
        Automatic authentication using saved cookies
        
        Args:
            driver: Selenium WebDriver instance
            domain: Domain to authenticate for
            
        Returns:
            True if authentication successful
        """
        self.logger.info(f"Attempting automatic authentication for {domain}")
        
        # Try to load saved cookies
        cookie_data = self.cookie_storage.load_cookies(domain)
        if not cookie_data:
            self.logger.warning("No saved cookies found, authentication may be needed")
            return False
        
        try:
            # Navigate to domain first
            base_url = f"https://{domain}"
            driver.get(base_url)
            time.sleep(2)
            
            # Add cookies to browser
            for cookie in cookie_data['cookies']:
                try:
                    # Clean cookie data for Selenium
                    clean_cookie = self._clean_cookie_for_selenium(cookie)
                    driver.add_cookie(clean_cookie)
                except Exception as e:
                    self.logger.debug(f"Failed to add cookie {cookie.get('name', 'unknown')}: {e}")
            
            # Refresh page to apply cookies
            driver.refresh()
            time.sleep(3)
            
            # Verify authentication
            if self._verify_authentication(driver, domain):
                self.is_authenticated = True
                self.logger.info("Automatic authentication successful")
                return True
            else:
                self.logger.warning("Automatic authentication failed - cookies may be expired")
                self.cookie_storage.clear_cookies()
                return False
                
        except Exception as e:
            self.logger.error(f"Auto authentication error: {e}")
            return False
    
    def _manual_authenticate(self, driver, domain: str) -> bool:
        """
        Manual interactive authentication
        
        Args:
            driver: Selenium WebDriver instance
            domain: Domain to authenticate for
            
        Returns:
            True if authentication successful
        """
        self.logger.info(f"Starting manual authentication for {domain}")
        
        try:
            # Navigate to login page
            login_url = self._get_login_url(domain)
            driver.get(login_url)
            time.sleep(3)
            
            # Show instructions to user
            print(f"\\n{'='*60}")
            print("🔐 手動登入 Threads")
            print(f"{'='*60}")
            print("1. 請在開啟的瀏覽器視窗中完成登入")
            print("2. 如遇到驗證碼或安全檢查，請依指示完成")
            print("3. 登入成功後，請按 Enter 鍵繼續...")
            print(f"{'='*60}")
            
            # Wait for user to complete login
            input("✋ 請完成登入後按 Enter 繼續...")
            
            # Verify authentication
            if self._verify_authentication(driver, domain):
                # Save cookies for future use
                cookies = driver.get_cookies()
                user_agent = driver.execute_script("return navigator.userAgent;")
                
                if self.cookie_storage.save_cookies(cookies, domain, user_agent):
                    self.logger.info("Authentication cookies saved for future use")
                
                self.is_authenticated = True
                print("✅ 登入成功！")
                return True
            else:
                print("❌ 登入驗證失敗，請重試")
                return False
                
        except Exception as e:
            self.logger.error(f"Manual authentication error: {e}")
            print(f"❌ 登入過程發生錯誤: {e}")
            return False
    
    def _prompt_and_authenticate(self, driver, domain: str) -> bool:
        """
        Prompt user and authenticate based on their choice
        
        Args:
            driver: Selenium WebDriver instance
            domain: Domain to authenticate for
            
        Returns:
            True if authentication successful or skipped
        """
        # First try auto authentication
        if self.cookie_storage.has_valid_cookies(domain):
            self.logger.info("Found saved cookies, trying automatic authentication...")
            if self._auto_authenticate(driver, domain):
                return True
        
        # Prompt user for choice
        print(f"\\n🔐 需要登入 {domain} 才能存取內容")
        print("請選擇認證方式：")
        print("1. 手動登入（在瀏覽器中完成登入）")
        print("2. 跳過認證（可能無法存取某些內容）")
        
        while True:
            choice = input("請輸入選擇 (1 或 2): ").strip()
            if choice == "1":
                return self._manual_authenticate(driver, domain)
            elif choice == "2":
                print("⚠️  跳過認證，某些內容可能無法存取")
                return True
            else:
                print("無效選擇，請輸入 1 或 2")
    
    def _get_login_url(self, domain: str) -> str:
        """Get login URL for domain"""
        if any(threads_domain in domain for threads_domain in self.config.threads_domains):
            return self.config.threads_login_url
        return f"https://{domain}/login"
    
    def _verify_authentication(self, driver, domain: str) -> bool:
        """
        Verify if authentication was successful
        
        Args:
            driver: Selenium WebDriver instance
            domain: Domain to verify
            
        Returns:
            True if authenticated
        """
        try:
            # Check current URL
            current_url = driver.current_url.lower()
            
            # If we're still on login page, authentication likely failed
            if 'login' in current_url or 'auth' in current_url:
                return False
            
            # Look for login indicators in page content
            page_source = driver.page_source.lower()
            login_indicators = [
                'log in', 'sign in', '登入', '登录',
                'create account', '註冊', '注册'
            ]
            
            # If login indicators are prominent, we might not be authenticated
            login_indicator_count = sum(1 for indicator in login_indicators if indicator in page_source)
            
            # If there are many login indicators, likely not authenticated
            if login_indicator_count > 2:
                return False
            
            # Try to find elements that indicate successful authentication
            auth_indicators = [
                'profile', 'timeline', 'feed', 'home',
                '個人資料', '動態', '首頁'
            ]
            
            auth_indicator_count = sum(1 for indicator in auth_indicators if indicator in page_source)
            
            # Positive indicators suggest we're authenticated
            self.logger.debug(f"Auth indicators: {auth_indicator_count}, Login indicators: {login_indicator_count}")
            return auth_indicator_count > 0
            
        except Exception as e:
            self.logger.error(f"Error verifying authentication: {e}")
            return False
    
    def _clean_cookie_for_selenium(self, cookie: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean cookie data for Selenium compatibility
        
        Args:
            cookie: Raw cookie dictionary
            
        Returns:
            Cleaned cookie dictionary
        """
        clean_cookie = {
            'name': cookie['name'],
            'value': cookie['value'],
            'domain': cookie.get('domain', ''),
            'path': cookie.get('path', '/'),
            'secure': cookie.get('secure', False),
            'httpOnly': cookie.get('httpOnly', False)
        }
        
        # Remove None values and problematic keys
        return {k: v for k, v in clean_cookie.items() if v is not None}
    
    def logout(self, driver) -> bool:
        """
        Logout and clear authentication state
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if logout successful
        """
        try:
            # Clear cookies from browser
            driver.delete_all_cookies()
            
            # Clear stored cookies
            self.cookie_storage.clear_cookies()
            
            # Reset authentication state
            self.is_authenticated = False
            self.current_domain = None
            self.last_auth_check = None
            
            self.logger.info("Logout completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return False
    
    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get current authentication status
        
        Returns:
            Dictionary with authentication status information
        """
        cookie_info = self.cookie_storage.get_cookie_info()
        
        return {
            'is_authenticated': self.is_authenticated,
            'current_domain': self.current_domain,
            'auth_mode': self.config.auth_mode.value,
            'has_saved_cookies': cookie_info is not None,
            'cookie_info': cookie_info
        }