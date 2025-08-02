"""
Selenium-based base scraper for handling modern web applications
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from ...models import Comment
from .base_scraper import BaseScraper, ScrapingError


class SeleniumBaseScraper(BaseScraper):
    """
    Base class for Selenium-powered web scrapers
    """
    
    def __init__(
        self, 
        timeout: int = 30, 
        delay: float = 2.0, 
        retry_attempts: int = 3,
        headless: bool = True,
        window_size: tuple = (1920, 1080)
    ):
        """
        Initialize Selenium base scraper
        
        Args:
            timeout: Request timeout in seconds
            delay: Delay between requests in seconds
            retry_attempts: Number of retry attempts
            headless: Run browser in headless mode
            window_size: Browser window size (width, height)
        """
        # Initialize base class without session (we'll use WebDriver instead)
        self.timeout = timeout
        self.delay = delay
        self.retry_attempts = retry_attempts
        self.headless = headless
        self.window_size = window_size
        
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.logger = self._setup_logger()
        
        # Initialize driver
        self._setup_driver()
    
    def _setup_driver(self):
        """
        Set up Chrome WebDriver with optimized options
        """
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            # Performance and compatibility options
            chrome_options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Faster loading
            
            # User agent for better compatibility
            chrome_options.add_argument(
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Language settings
            chrome_options.add_argument('--lang=zh-TW')
            chrome_options.add_experimental_option('prefs', {
                'intl.accept_languages': 'zh-TW,zh,en'
            })
            
            # Try to find and use ChromeDriver
            service = None
            chromedriver_path = None
            
            # Method 1: Try webdriver-manager
            try:
                import os
                from pathlib import Path
                
                # Use webdriver-manager to download if needed
                wdm_path = ChromeDriverManager().install()
                
                # Find actual chromedriver executable
                if wdm_path:
                    base_dir = Path(wdm_path).parent
                    possible_files = ['chromedriver', 'chromedriver.exe']
                    
                    for filename in possible_files:
                        candidate_path = base_dir / filename
                        if candidate_path.exists() and candidate_path.is_file():
                            # Set execute permissions
                            candidate_path.chmod(0o755)
                            chromedriver_path = str(candidate_path)
                            break
                
                if chromedriver_path:
                    service = Service(chromedriver_path)
                    self.logger.info(f"Using ChromeDriver at: {chromedriver_path}")
                
            except Exception as wdm_error:
                self.logger.warning(f"ChromeDriverManager failed: {wdm_error}")
            
            # Method 2: Try system PATH
            if not service:
                try:
                    service = Service()  # Uses system PATH
                    self.logger.info("Using system ChromeDriver from PATH")
                except Exception as path_error:
                    self.logger.warning(f"System ChromeDriver failed: {path_error}")
            
            # Method 3: Try common installation paths
            if not service:
                common_paths = [
                    '/usr/local/bin/chromedriver',
                    '/usr/bin/chromedriver',
                    '/opt/homebrew/bin/chromedriver',
                ]
                
                for path in common_paths:
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        service = Service(path)
                        self.logger.info(f"Using ChromeDriver at: {path}")
                        break
            
            if not service:
                raise Exception("No valid ChromeDriver found. Please install Chrome browser and ensure chromedriver is in PATH.")
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            self.logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            raise ScrapingError(f"WebDriver initialization failed: {e}")
    
    def _make_request(self, url: str, **kwargs) -> str:
        """
        Navigate to URL and return page source
        
        Args:
            url: URL to navigate to
            **kwargs: Additional arguments (not used in Selenium)
            
        Returns:
            Page source HTML
            
        Raises:
            ScrapingError: If navigation fails
        """
        for attempt in range(self.retry_attempts):
            try:
                self.logger.info(f"Navigating to {url} (attempt {attempt + 1})")
                
                # Navigate to the URL
                self.driver.get(url)
                
                # Wait for basic page load
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # Additional delay for JavaScript execution
                time.sleep(self.delay)
                
                return self.driver.page_source
                
            except TimeoutException as e:
                self.logger.warning(f"Page load timeout (attempt {attempt + 1}): {e}")
                if attempt == self.retry_attempts - 1:
                    raise ScrapingError(f"Page load timeout after {self.retry_attempts} attempts")
            except WebDriverException as e:
                self.logger.warning(f"WebDriver error (attempt {attempt + 1}): {e}")
                if attempt == self.retry_attempts - 1:
                    raise ScrapingError(f"WebDriver error after {self.retry_attempts} attempts: {e}")
            except Exception as e:
                self.logger.warning(f"Navigation failed (attempt {attempt + 1}): {e}")
                if attempt == self.retry_attempts - 1:
                    raise ScrapingError(f"Navigation failed after {self.retry_attempts} attempts: {e}")
                
                # Exponential backoff
                time.sleep(self.delay * (attempt + 1))
    
    def wait_for_element(
        self, 
        locator: tuple, 
        timeout: Optional[int] = None,
        condition='presence'
    ) -> bool:
        """
        Wait for element to appear on page
        
        Args:
            locator: Selenium locator tuple (By.TYPE, "selector")
            timeout: Custom timeout (uses default if None)
            condition: Type of condition to wait for
            
        Returns:
            True if element found, False otherwise
        """
        wait_timeout = timeout or self.timeout
        temp_wait = WebDriverWait(self.driver, wait_timeout)
        
        try:
            conditions = {
                'presence': EC.presence_of_element_located,
                'visible': EC.visibility_of_element_located,
                'clickable': EC.element_to_be_clickable
            }
            
            condition_func = conditions.get(condition, EC.presence_of_element_located)
            temp_wait.until(condition_func(locator))
            return True
            
        except TimeoutException:
            self.logger.debug(f"Element not found with locator {locator} within {wait_timeout}s")
            return False
    
    def scroll_to_load_content(self, max_scrolls: int = 5, scroll_pause: float = 2.0):
        """
        Scroll page to load dynamic content
        
        Args:
            max_scrolls: Maximum number of scroll attempts
            scroll_pause: Pause between scrolls
        """
        self.logger.info(f"Scrolling to load dynamic content (max {max_scrolls} scrolls)")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scrolls = 0
        
        while scrolls < max_scrolls:
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(scroll_pause)
            
            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                self.logger.info(f"No new content after scroll {scrolls + 1}, stopping")
                break
                
            last_height = new_height
            scrolls += 1
            
        self.logger.info(f"Completed {scrolls} scrolls")
    
    def execute_script(self, script: str) -> Any:
        """
        Execute JavaScript in the browser
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result of script execution
        """
        try:
            return self.driver.execute_script(script)
        except Exception as e:
            self.logger.warning(f"Script execution failed: {e}")
            return None
    
    def get_elements(self, selector: str, by: By = By.CSS_SELECTOR) -> List:
        """
        Find elements using Selenium
        
        Args:
            selector: Element selector
            by: Selenium By method
            
        Returns:
            List of WebElement objects
        """
        try:
            return self.driver.find_elements(by, selector)
        except Exception as e:
            self.logger.debug(f"Failed to find elements with selector '{selector}': {e}")
            return []
    
    def get_soup(self) -> BeautifulSoup:
        """
        Get BeautifulSoup object from current page
        
        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(self.driver.page_source, 'html.parser')
    
    def cleanup(self):
        """
        Clean up resources and close browser
        """
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
                self.wait = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()