"""
Threads scraper implementation
"""
import re
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from .base_scraper import BaseScraper, ScrapingError
from ...models import Comment


class ThreadsScraper(BaseScraper):
    """
    Scraper for Threads posts
    """
    
    THREADS_DOMAINS = ['threads.com', 'www.threads.com', 'threads.net', 'www.threads.net']
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is a Threads post URL
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid Threads URL
        """
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc.lower() in self.THREADS_DOMAINS and
                '/post/' in parsed.path
            )
        except Exception:
            return False
    
    def extract_post_id(self, url: str) -> str:
        """
        Extract post ID from Threads URL
        
        Args:
            url: Threads post URL
            
        Returns:
            Post ID string
        """
        try:
            # Threads URL format: https://www.threads.com/@username/post/POST_ID
            path_parts = urlparse(url).path.split('/')
            post_index = path_parts.index('post')
            if post_index + 1 < len(path_parts):
                return path_parts[post_index + 1]
            raise ValueError("Post ID not found in URL")
        except (ValueError, IndexError) as e:
            raise ScrapingError(f"Invalid Threads URL format: {e}")
    
    def scrape_comments(self, url: str) -> List[Comment]:
        """
        Scrape comments from Threads post
        
        Args:
            url: Threads post URL
            
        Returns:
            List of Comment objects
        """
        if not self.validate_url(url):
            raise ScrapingError("Invalid Threads URL")
        
        self.logger.info(f"Scraping Threads post: {url}")
        
        try:
            # Make request to get the page
            response = self._make_request(url)
            soup = self._parse_html(response.text)
            
            # Extract comments using multiple strategies
            comments = []
            
            # Strategy 1: Look for JSON data in script tags
            json_comments = self._extract_from_json_data(soup, url)
            if json_comments:
                comments.extend(json_comments)
            
            # Strategy 2: Parse HTML structure
            if not comments:
                html_comments = self._extract_from_html_structure(soup, url)
                comments.extend(html_comments)
            
            # Strategy 3: Fallback - look for basic patterns
            if not comments:
                pattern_comments = self._extract_from_patterns(soup, url)
                comments.extend(pattern_comments)
            
            self.logger.info(f"Extracted {len(comments)} comments from Threads")
            return comments
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Threads comments: {e}")
    
    def _extract_from_json_data(self, soup, url: str) -> List[Comment]:
        """
        Extract comments from JSON data in script tags
        """
        comments = []
        script_tags = soup.find_all('script', type='application/json')
        
        for script in script_tags:
            try:
                data = json.loads(script.string)
                # Look for comment-like structures in the JSON
                comments.extend(self._parse_json_for_comments(data, url))
            except (json.JSONDecodeError, TypeError):
                continue
        
        return comments
    
    def _parse_json_for_comments(self, data: Any, url: str, path: str = "") -> List[Comment]:
        """
        Recursively parse JSON data for comment structures
        """
        comments = []
        
        if isinstance(data, dict):
            # Look for comment-like objects
            if self._is_comment_object(data):
                comment = self._create_comment_from_json(data, url)
                if comment:
                    comments.append(comment)
            
            # Recursively search in nested objects
            for key, value in data.items():
                comments.extend(self._parse_json_for_comments(value, url, f"{path}.{key}"))
        
        elif isinstance(data, list):
            # Search in array items
            for i, item in enumerate(data):
                comments.extend(self._parse_json_for_comments(item, url, f"{path}[{i}]"))
        
        return comments
    
    def _is_comment_object(self, obj: Dict) -> bool:
        """
        Check if object looks like a comment
        """
        if not isinstance(obj, dict):
            return False
        
        # Look for common comment properties
        comment_indicators = ['text', 'content', 'message', 'body']
        user_indicators = ['user', 'author', 'username', 'owner']
        
        has_text = any(key in obj for key in comment_indicators)
        has_user = any(key in obj for key in user_indicators)
        
        return has_text and has_user
    
    def _create_comment_from_json(self, data: Dict, url: str) -> Optional[Comment]:
        """
        Create Comment object from JSON data
        """
        try:
            # Extract text content
            text = (
                data.get('text') or 
                data.get('content') or 
                data.get('message') or 
                data.get('body') or 
                ""
            )
            
            # Extract user info
            user_data = data.get('user') or data.get('author') or data.get('owner') or {}
            if isinstance(user_data, str):
                username = user_data
                avatar_url = None
            else:
                username = (
                    user_data.get('username') or 
                    user_data.get('name') or 
                    data.get('username') or 
                    ""
                )
                avatar_url = (
                    user_data.get('profile_picture_url') or 
                    user_data.get('avatar') or 
                    user_data.get('profile_pic_url')
                )
            
            if not text or not username:
                return None
            
            # Create comment
            comment = Comment(
                id=data.get('id', f"threads_{hash(text + username)}"),
                username=username.lstrip('@'),
                content=text,
                avatar_url=avatar_url,
                platform="threads",
                post_url=url,
                likes_count=data.get('like_count', 0),
                replies_count=data.get('reply_count', 0)
            )
            
            # Extract mentions
            comment.extract_mentions()
            
            return comment
            
        except Exception as e:
            self.logger.warning(f"Failed to create comment from JSON: {e}")
            return None
    
    def _extract_from_html_structure(self, soup, url: str) -> List[Comment]:
        """
        Extract comments from HTML structure
        """
        comments = []
        
        # Look for common HTML patterns for comments
        comment_selectors = [
            '[data-testid*="comment"]',
            '[class*="comment"]',
            '[class*="reply"]',
            '.x1i10hfl',  # Common Threads class pattern
            '[role="article"]'
        ]
        
        for selector in comment_selectors:
            elements = soup.select(selector)
            for element in elements:
                comment = self._parse_html_comment(element, url)
                if comment:
                    comments.append(comment)
        
        return self._deduplicate_comments(comments)
    
    def _parse_html_comment(self, element, url: str) -> Optional[Comment]:
        """
        Parse individual HTML comment element
        """
        try:
            # Try to extract text content
            text_element = element.find(text=True, recursive=True)
            if not text_element:
                return None
            
            # Get all text content
            text_content = ' '.join(element.stripped_strings)
            if not text_content or len(text_content) < 2:
                return None
            
            # Try to find username (often in links or specific attributes)
            username_element = (
                element.find('a', href=re.compile(r'/@\w+')) or
                element.find(attrs={'data-testid': re.compile(r'user|author')}) or
                element.find(class_=re.compile(r'user|author|name'))
            )
            
            username = "unknown_user"
            if username_element:
                username = username_element.get_text(strip=True).lstrip('@')
            
            # Try to find avatar
            avatar_element = element.find('img')
            avatar_url = avatar_element.get('src') if avatar_element else None
            
            comment = Comment(
                id=f"threads_html_{hash(text_content + username)}",
                username=username,
                content=text_content,
                avatar_url=avatar_url,
                platform="threads",
                post_url=url
            )
            
            comment.extract_mentions()
            return comment
            
        except Exception as e:
            self.logger.debug(f"Failed to parse HTML comment: {e}")
            return None
    
    def _extract_from_patterns(self, soup, url: str) -> List[Comment]:
        """
        Extract comments using text patterns (fallback method)
        """
        comments = []
        
        # Look for text patterns that might indicate comments
        text_content = soup.get_text()
        
        # Pattern for @username mentions followed by text
        mention_pattern = r'@(\w+)\s+([^@]+?)(?=@|\n|$)'
        matches = re.findall(mention_pattern, text_content, re.MULTILINE)
        
        for i, (username, content) in enumerate(matches):
            if len(content.strip()) > 10:  # Filter out very short content
                comment = Comment(
                    id=f"threads_pattern_{i}",
                    username=username,
                    content=content.strip(),
                    platform="threads",
                    post_url=url
                )
                comment.extract_mentions()
                comments.append(comment)
        
        return comments
    
    def _deduplicate_comments(self, comments: List[Comment]) -> List[Comment]:
        """
        Remove duplicate comments based on content and username
        """
        seen = set()
        unique_comments = []
        
        for comment in comments:
            key = (comment.username.lower(), comment.content.lower().strip())
            if key not in seen:
                seen.add(key)
                unique_comments.append(comment)
        
        return unique_comments