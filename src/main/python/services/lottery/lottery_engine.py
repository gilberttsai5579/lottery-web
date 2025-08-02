"""
Lottery engine for conducting lotteries with different modes
"""
import logging
import random
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...models import Comment, LotteryResult, LotteryMode
from ..scrapers import ScraperFactory, ScrapingError


class LotteryEngine:
    """
    Main lottery engine for conducting lotteries
    """
    
    def __init__(self):
        """Initialize lottery engine"""
        self.logger = self._setup_logger()
        self.results_cache: Dict[str, LotteryResult] = {}
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for lottery engine"""
        logger = logging.getLogger("LotteryEngine")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def conduct_lottery(
        self,
        url: str,
        mode: str,
        winner_count: int,
        keyword: str = "",
        mention_count_required: int = 1,
        seed: Optional[int] = None
    ) -> LotteryResult:
        """
        Conduct a lottery with specified parameters
        
        Args:
            url: Post URL to scrape
            mode: Lottery mode ("1", "2", or "3")
            winner_count: Number of winners to select
            keyword: Keyword for mode 1 filtering
            mention_count_required: Required mention count for mode 3
            seed: Random seed for reproducible results
            
        Returns:
            LotteryResult object
            
        Raises:
            ScrapingError: If scraping fails
            ValueError: If parameters are invalid
        """
        self.logger.info(f"Starting lottery for {url}, mode {mode}")
        
        # Validate parameters
        self._validate_parameters(url, mode, winner_count, keyword, mention_count_required)
        
        # Create lottery result object
        lottery_mode = LotteryMode(mode)
        result = LotteryResult(
            post_url=url,
            mode=lottery_mode,
            winner_count=winner_count,
            keyword=keyword,
            mention_count_required=mention_count_required
        )
        
        try:
            # Scrape comments
            self.logger.info("Scraping comments...")
            comments = self._scrape_comments(url)
            result.platform = ScraperFactory.detect_platform(url)
            
            # Check if we got any comments
            if not comments:
                self.logger.warning(f"No comments found for URL: {url}")
                raise ValueError(
                    "無法從該貼文中找到任何留言。可能的原因：\n"
                    "• 該貼文沒有留言\n"
                    "• 貼文被設為私人或限制訪問\n"
                    "• 網路連線問題\n"
                    "請確認貼文是公開的且有留言存在，然後重試"
                )
            
            # Add all comments as participants
            for comment in comments:
                result.add_participant(comment)
            
            # Conduct the lottery
            self.logger.info(f"Conducting lottery with {len(comments)} comments")
            result.conduct_lottery(seed=seed)
            
            # Check if we have any eligible participants
            if result.eligible_count == 0:
                mode_descriptions = {
                    "1": f"包含關鍵字「{keyword}」",
                    "2": "符合抽獎條件",
                    "3": f"標註至少 {mention_count_required} 個帳號"
                }
                mode_desc = mode_descriptions.get(mode, "符合條件")
                
                raise ValueError(
                    f"沒有找到{mode_desc}的留言。\n"
                    f"總留言數：{len(comments)} 條\n"
                    f"符合條件：0 條\n\n"
                    "建議：\n"
                    "• 檢查篩選條件是否過於嚴格\n"
                    "• 嘗試使用不同的關鍵字或模式\n"
                    "• 確認貼文中確實有符合條件的留言"
                )
            
            # Cache result
            self.results_cache[result.id] = result
            
            self.logger.info(
                f"Lottery completed: {len(result.winners)} winners from "
                f"{result.eligible_count} eligible participants"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Lottery failed: {e}")
            # Return failed result
            result.winners = []
            result.total_comments = 0
            result.total_participants = 0
            result.eligible_count = 0
            return result
    
    def _validate_parameters(
        self,
        url: str,
        mode: str,
        winner_count: int,
        keyword: str,
        mention_count_required: int
    ):
        """Validate lottery parameters"""
        if not url:
            raise ValueError("URL is required")
        
        if not ScraperFactory.is_supported_url(url):
            raise ValueError("Unsupported URL format")
        
        if mode not in ["1", "2", "3"]:
            raise ValueError("Mode must be 1, 2, or 3")
        
        if winner_count < 1:
            raise ValueError("Winner count must be at least 1")
        
        if mode == "1" and not keyword.strip():
            raise ValueError("Keyword is required for mode 1")
        
        if mode == "3" and mention_count_required < 1:
            raise ValueError("Mention count must be at least 1 for mode 3")
    
    def _scrape_comments(self, url: str) -> List[Comment]:
        """
        Scrape comments from the given URL
        
        Args:
            url: URL to scrape
            
        Returns:
            List of Comment objects
            
        Raises:
            ScrapingError: If scraping fails
        """
        try:
            # Try Selenium scraper first for better success rate
            scraper = None
            try:
                self.logger.info("Attempting to use Selenium scraper for better compatibility...")
                scraper = ScraperFactory.create_scraper(url, use_selenium=True)
                with scraper:
                    comments = scraper.scrape_comments(url)
            except Exception as selenium_error:
                self.logger.warning(f"Selenium scraper failed: {selenium_error}")
                self.logger.info("Falling back to traditional scraper...")
                
                # Fallback to traditional scraper
                scraper = ScraperFactory.create_scraper(url, use_selenium=False)
                with scraper:
                    comments = scraper.scrape_comments(url)
            
            # Filter out empty or invalid comments
            valid_comments = []
            for comment in comments:
                if self._is_valid_comment(comment):
                    valid_comments.append(comment)
            
            return valid_comments
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape comments: {e}")
    
    def _is_valid_comment(self, comment: Comment) -> bool:
        """
        Check if comment is valid for lottery
        
        Args:
            comment: Comment to validate
            
        Returns:
            True if comment is valid
        """
        # Basic validation
        if not comment.username or not comment.content:
            return False
        
        # Filter out very short comments
        if len(comment.content.strip()) < 2:
            return False
        
        # Filter out system/bot accounts (basic check)
        if comment.username.lower() in ['instagram', 'threads', 'meta', 'facebook']:
            return False
        
        return True
    
    def get_result(self, result_id: str) -> Optional[LotteryResult]:
        """
        Get cached lottery result by ID
        
        Args:
            result_id: Result ID
            
        Returns:
            LotteryResult if found, None otherwise
        """
        return self.results_cache.get(result_id)
    
    def get_all_results(self) -> List[LotteryResult]:
        """
        Get all cached lottery results
        
        Returns:
            List of LotteryResult objects
        """
        return list(self.results_cache.values())
    
    def clear_cache(self):
        """Clear results cache"""
        self.results_cache.clear()
        self.logger.info("Results cache cleared")
    
    def preview_participants(
        self,
        url: str,
        mode: str,
        keyword: str = "",
        mention_count_required: int = 1
    ) -> Dict[str, Any]:
        """
        Preview participants without conducting lottery
        
        Args:
            url: Post URL to scrape
            mode: Lottery mode ("1", "2", or "3")
            keyword: Keyword for mode 1 filtering
            mention_count_required: Required mention count for mode 3
            
        Returns:
            Dictionary with participant information
        """
        try:
            # Scrape comments
            comments = self._scrape_comments(url)
            
            # Create temporary result to filter participants
            lottery_mode = LotteryMode(mode)
            temp_result = LotteryResult(
                post_url=url,
                mode=lottery_mode,
                keyword=keyword,
                mention_count_required=mention_count_required
            )
            
            for comment in comments:
                temp_result.add_participant(comment)
            
            temp_result.filter_eligible_participants()
            
            return {
                'success': True,
                'total_comments': len(comments),
                'total_participants': temp_result.total_participants,
                'eligible_count': temp_result.eligible_count,
                'eligible_participants': [
                    {
                        'username': c.username,
                        'content': c.content[:100] + '...' if len(c.content) > 100 else c.content,
                        'mention_count': c.mention_count()
                    }
                    for c in temp_result.eligible_participants[:10]  # Show first 10
                ]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'total_comments': 0,
                'total_participants': 0,
                'eligible_count': 0,
                'eligible_participants': []
            }


class QuickLottery:
    """
    Simplified interface for quick lottery operations
    """
    
    @staticmethod
    def keyword_lottery(url: str, keyword: str, winner_count: int = 1) -> LotteryResult:
        """
        Quick keyword-based lottery
        
        Args:
            url: Post URL
            keyword: Keyword to filter by
            winner_count: Number of winners
            
        Returns:
            LotteryResult object
        """
        engine = LotteryEngine()
        return engine.conduct_lottery(
            url=url,
            mode="1",
            winner_count=winner_count,
            keyword=keyword
        )
    
    @staticmethod
    def all_commenters_lottery(url: str, winner_count: int = 1) -> LotteryResult:
        """
        Quick all-commenters lottery
        
        Args:
            url: Post URL
            winner_count: Number of winners
            
        Returns:
            LotteryResult object
        """
        engine = LotteryEngine()
        return engine.conduct_lottery(
            url=url,
            mode="2",
            winner_count=winner_count
        )
    
    @staticmethod
    def mention_lottery(url: str, mention_count: int, winner_count: int = 1) -> LotteryResult:
        """
        Quick mention-based lottery
        
        Args:
            url: Post URL
            mention_count: Required number of mentions
            winner_count: Number of winners
            
        Returns:
            LotteryResult object
        """
        engine = LotteryEngine()
        return engine.conduct_lottery(
            url=url,
            mode="3",
            winner_count=winner_count,
            mention_count_required=mention_count
        )