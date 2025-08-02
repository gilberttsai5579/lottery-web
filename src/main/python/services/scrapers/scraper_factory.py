"""
Scraper factory for creating appropriate scrapers based on URL
"""
from typing import Optional, Type
from urllib.parse import urlparse

from .base_scraper import BaseScraper, ScrapingError
from .threads_scraper import ThreadsScraper
from .instagram_scraper import InstagramScraper


class ScraperFactory:
    """
    Factory class for creating appropriate scrapers based on URL
    """
    
    _scrapers = {
        'threads': ThreadsScraper,
        'instagram': InstagramScraper,
    }
    
    @classmethod
    def create_scraper(cls, url: str, **kwargs) -> BaseScraper:
        """
        Create appropriate scraper based on URL
        
        Args:
            url: URL to scrape
            **kwargs: Additional arguments for scraper initialization
            
        Returns:
            Appropriate scraper instance
            
        Raises:
            ScrapingError: If no suitable scraper found
        """
        platform = cls.detect_platform(url)
        
        if platform not in cls._scrapers:
            raise ScrapingError(f"No scraper available for platform: {platform}")
        
        scraper_class = cls._scrapers[platform]
        return scraper_class(**kwargs)
    
    @classmethod
    def detect_platform(cls, url: str) -> str:
        """
        Detect platform from URL
        
        Args:
            url: URL to analyze
            
        Returns:
            Platform name string
            
        Raises:
            ScrapingError: If platform cannot be detected
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            if 'threads.com' in domain or 'threads.net' in domain:
                return 'threads'
            elif 'instagram.com' in domain:
                return 'instagram'
            else:
                raise ScrapingError(f"Unsupported domain: {domain}")
                
        except Exception as e:
            raise ScrapingError(f"Failed to detect platform from URL: {e}")
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """
        Get list of supported platforms
        
        Returns:
            List of platform names
        """
        return list(cls._scrapers.keys())
    
    @classmethod
    def is_supported_url(cls, url: str) -> bool:
        """
        Check if URL is supported by any scraper
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is supported
        """
        try:
            platform = cls.detect_platform(url)
            scraper_class = cls._scrapers.get(platform)
            if scraper_class:
                # Create temporary instance to validate URL
                temp_scraper = scraper_class()
                return temp_scraper.validate_url(url)
            return False
        except:
            return False
    
    @classmethod
    def register_scraper(cls, platform: str, scraper_class: Type[BaseScraper]):
        """
        Register a new scraper for a platform
        
        Args:
            platform: Platform name
            scraper_class: Scraper class
        """
        cls._scrapers[platform] = scraper_class