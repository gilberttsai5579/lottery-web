"""
Web scrapers package for Threads and Instagram
"""

from .base_scraper import BaseScraper, ScrapingError
from .threads_scraper import ThreadsScraper
from .instagram_scraper import InstagramScraper
from .scraper_factory import ScraperFactory

__all__ = [
    'BaseScraper', 
    'ScrapingError',
    'ThreadsScraper', 
    'InstagramScraper', 
    'ScraperFactory'
]