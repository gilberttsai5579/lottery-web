"""
Configuration file for lottery web application
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # Flask configuration
    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    # Upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Output directory
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
    
    # Scraper configuration
    SCRAPER_TIMEOUT = 30  # seconds
    SCRAPER_RETRY_ATTEMPTS = 3
    SCRAPER_DELAY = 2  # seconds between requests
    
    # Selenium configuration
    SELENIUM_HEADLESS = True
    SELENIUM_WINDOW_SIZE = "1920,1080"
    
    # Excel export configuration
    EXCEL_MAX_ROWS = 1000000
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        # Create output directory if it doesn't exist
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration"""
    # Override configurations for production
    pass


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}