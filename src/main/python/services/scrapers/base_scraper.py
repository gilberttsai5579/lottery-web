"""
Base scraper class for web scraping functionality
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from ...models import Comment


class ScrapingError(Exception):
    """Custom exception for scraping errors"""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for web scrapers
    """
    
    def __init__(self, timeout: int = 30, delay: float = 2.0, retry_attempts: int = 3):
        """
        Initialize base scraper
        
        Args:
            timeout: Request timeout in seconds
            delay: Delay between requests in seconds
            retry_attempts: Number of retry attempts for failed requests
        """
        self.timeout = timeout
        self.delay = delay
        self.retry_attempts = retry_attempts
        self.session = self._create_session()
        self.logger = self._setup_logger()
    
    def _create_session(self) -> requests.Session:
        """
        Create and configure requests session
        """
        session = requests.Session()
        session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return session
    
    def _setup_logger(self) -> logging.Logger:
        """
        Setup logger for scraper
        """
        logger = logging.getLogger(f"{self.__class__.__name__}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with retry logic
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            ScrapingError: If all retry attempts fail
        """
        for attempt in range(self.retry_attempts):
            try:
                self.logger.info(f"Making request to {url} (attempt {attempt + 1})")
                
                response = self.session.get(
                    url, 
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                
                # Delay between requests
                if self.delay > 0:
                    time.sleep(self.delay)
                
                return response
                
            except requests.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.retry_attempts - 1:
                    raise ScrapingError(f"Failed to fetch {url} after {self.retry_attempts} attempts: {e}")
                time.sleep(self.delay * (attempt + 1))  # Exponential backoff
    
    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """
        Parse HTML content using BeautifulSoup
        
        Args:
            html_content: HTML content string
            
        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html_content, 'html.parser')
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is supported by this scraper
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid for this scraper
        """
        pass
    
    @abstractmethod
    def extract_post_id(self, url: str) -> str:
        """
        Extract post ID from URL
        
        Args:
            url: Post URL
            
        Returns:
            Post ID string
        """
        pass
    
    @abstractmethod
    def scrape_comments(self, url: str) -> List[Comment]:
        """
        Scrape comments from post URL
        
        Args:
            url: Post URL to scrape
            
        Returns:
            List of Comment objects
            
        Raises:
            ScrapingError: If scraping fails
        """
        pass
    
    def get_platform_name(self) -> str:
        """
        Get platform name for this scraper
        
        Returns:
            Platform name string
        """
        return self.__class__.__name__.replace('Scraper', '').lower()
    
    def scrape_with_metadata(self, url: str) -> Dict[str, Any]:
        """
        Scrape comments with additional metadata
        
        Args:
            url: Post URL to scrape
            
        Returns:
            Dictionary containing comments and metadata
        """
        try:
            start_time = time.time()
            comments = self.scrape_comments(url)
            end_time = time.time()
            
            return {
                'success': True,
                'url': url,
                'platform': self.get_platform_name(),
                'post_id': self.extract_post_id(url),
                'comments': comments,
                'total_comments': len(comments),
                'unique_users': len(set(c.username for c in comments)),
                'scraping_duration': round(end_time - start_time, 2),
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Scraping failed for {url}: {e}")
            return {
                'success': False,
                'url': url,
                'platform': self.get_platform_name(),
                'error': str(e),
                'comments': [],
                'total_comments': 0,
                'unique_users': 0,
                'timestamp': time.time()
            }
    
    def close(self):
        """
        Clean up resources
        """
        if hasattr(self, 'session'):
            self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()