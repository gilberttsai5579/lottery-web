"""
Instagram scraper implementation
"""
import re
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from datetime import datetime

from .base_scraper import BaseScraper, ScrapingError
from ...models import Comment


class InstagramScraper(BaseScraper):
    """
    Scraper for Instagram posts
    """
    
    INSTAGRAM_DOMAINS = ['instagram.com', 'www.instagram.com']
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is an Instagram post URL
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid Instagram URL
        """
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc.lower() in self.INSTAGRAM_DOMAINS and
                ('/p/' in parsed.path or '/reel/' in parsed.path)
            )
        except Exception:
            return False
    
    def extract_post_id(self, url: str) -> str:
        """
        Extract post ID from Instagram URL
        
        Args:
            url: Instagram post URL
            
        Returns:
            Post ID string
        """
        try:
            # Instagram URL formats:
            # https://www.instagram.com/p/POST_ID/
            # https://www.instagram.com/reel/POST_ID/
            path_parts = urlparse(url).path.split('/')
            
            for i, part in enumerate(path_parts):
                if part in ['p', 'reel'] and i + 1 < len(path_parts):
                    return path_parts[i + 1]
            
            raise ValueError("Post ID not found in URL")
            
        except (ValueError, IndexError) as e:
            raise ScrapingError(f"Invalid Instagram URL format: {e}")
    
    def scrape_comments(self, url: str) -> List[Comment]:
        """
        Scrape comments from Instagram post
        
        Args:
            url: Instagram post URL
            
        Returns:
            List of Comment objects
        """
        if not self.validate_url(url):
            raise ScrapingError("Invalid Instagram URL")
        
        self.logger.info(f"Scraping Instagram post: {url}")
        
        try:
            # Add Instagram-specific headers
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://www.instagram.com/',
            }
            
            # Make request to get the page
            response = self._make_request(url, headers=headers)
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
            
            self.logger.info(f"Extracted {len(comments)} comments from Instagram")
            return comments
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Instagram comments: {e}")
    
    def _extract_from_json_data(self, soup, url: str) -> List[Comment]:
        """
        Extract comments from JSON data in script tags
        """
        comments = []
        
        # Look for specific Instagram JSON patterns
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            if not script.string:
                continue
                
            try:
                # Look for Instagram's window._sharedData
                if 'window._sharedData' in script.string:
                    json_match = re.search(r'window\._sharedData\s*=\s*({.+?});', script.string)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        comments.extend(self._parse_shared_data(data, url))
                
                # Look for additional data patterns
                elif 'additionalDataLoaded' in script.string:
                    json_match = re.search(r'({.+})', script.string)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        comments.extend(self._parse_json_for_comments(data, url))
                        
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return comments
    
    def _parse_shared_data(self, data: Dict, url: str) -> List[Comment]:
        """
        Parse Instagram's _sharedData for comments
        """
        comments = []
        
        try:
            # Navigate through Instagram's data structure
            entry_data = data.get('entry_data', {})
            post_page = entry_data.get('PostPage', [{}])[0]
            graphql = post_page.get('graphql', {})
            shortcode_media = graphql.get('shortcode_media', {})
            
            # Extract comments from edge_media_to_parent_comment
            comment_edges = shortcode_media.get('edge_media_to_parent_comment', {}).get('edges', [])
            
            for edge in comment_edges:
                comment_node = edge.get('node', {})
                comment = self._create_comment_from_instagram_node(comment_node, url)
                if comment:
                    comments.append(comment)
                
                # Also get replies
                reply_edges = comment_node.get('edge_threaded_comments', {}).get('edges', [])
                for reply_edge in reply_edges:
                    reply_node = reply_edge.get('node', {})
                    reply_comment = self._create_comment_from_instagram_node(reply_node, url)
                    if reply_comment:
                        comments.append(reply_comment)
            
        except Exception as e:
            self.logger.debug(f"Error parsing shared data: {e}")
        
        return comments
    
    def _create_comment_from_instagram_node(self, node: Dict, url: str) -> Optional[Comment]:
        """
        Create Comment object from Instagram comment node
        """
        try:
            text = node.get('text', '')
            if not text:
                return None
            
            owner = node.get('owner', {})
            username = owner.get('username', '')
            if not username:
                return None
            
            profile_pic_url = owner.get('profile_pic_url')
            
            # Parse timestamp
            timestamp = None
            created_at = node.get('created_at')
            if created_at:
                timestamp = datetime.fromtimestamp(created_at)
            
            comment = Comment(
                id=node.get('id', f"ig_{hash(text + username)}"),
                username=username,
                content=text,
                avatar_url=profile_pic_url,
                timestamp=timestamp,
                platform="instagram",
                post_url=url,
                likes_count=node.get('edge_liked_by', {}).get('count', 0)
            )
            
            comment.extract_mentions()
            return comment
            
        except Exception as e:
            self.logger.debug(f"Failed to create comment from Instagram node: {e}")
            return None
    
    def _parse_json_for_comments(self, data: Any, url: str) -> List[Comment]:
        """
        Recursively parse JSON data for comment structures
        """
        comments = []
        
        if isinstance(data, dict):
            # Look for comment-like objects
            if self._is_instagram_comment_object(data):
                comment = self._create_comment_from_json(data, url)
                if comment:
                    comments.append(comment)
            
            # Recursively search in nested objects
            for key, value in data.items():
                if key in ['comments', 'edge_media_to_comment', 'edge_media_to_parent_comment']:
                    comments.extend(self._parse_json_for_comments(value, url))
        
        elif isinstance(data, list):
            # Search in array items
            for item in data:
                comments.extend(self._parse_json_for_comments(item, url))
        
        return comments
    
    def _is_instagram_comment_object(self, obj: Dict) -> bool:
        """
        Check if object looks like an Instagram comment
        """
        if not isinstance(obj, dict):
            return False
        
        # Instagram-specific comment indicators
        has_text = 'text' in obj
        has_owner = 'owner' in obj or 'user' in obj
        has_id = 'id' in obj
        
        return has_text and (has_owner or has_id)
    
    def _create_comment_from_json(self, data: Dict, url: str) -> Optional[Comment]:
        """
        Create Comment object from generic JSON data
        """
        try:
            text = data.get('text', '')
            if not text:
                return None
            
            # Extract user info
            owner = data.get('owner') or data.get('user') or {}
            username = owner.get('username') or data.get('username', '')
            if not username:
                return None
            
            avatar_url = owner.get('profile_pic_url') or owner.get('profile_picture')
            
            comment = Comment(
                id=data.get('id', f"ig_json_{hash(text + username)}"),
                username=username,
                content=text,
                avatar_url=avatar_url,
                platform="instagram",
                post_url=url
            )
            
            comment.extract_mentions()
            return comment
            
        except Exception as e:
            self.logger.debug(f"Failed to create comment from JSON: {e}")
            return None
    
    def _extract_from_html_structure(self, soup, url: str) -> List[Comment]:
        """
        Extract comments from HTML structure
        """
        comments = []
        
        # Look for Instagram-specific HTML patterns
        comment_selectors = [
            'article [role="button"]',
            '.comment',
            '[data-testid="comment"]',
            'span[dir="auto"]',  # Instagram often uses this for text content
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
            # Get text content
            text_content = element.get_text(strip=True)
            if not text_content or len(text_content) < 2:
                return None
            
            # Skip if it looks like a timestamp or metadata
            if re.match(r'^\d+[smhd]$', text_content) or text_content in ['Like', 'Reply', 'View replies']:
                return None
            
            # Try to find associated username
            username = "unknown_user"
            
            # Look for username in nearby elements
            parent = element.find_parent()
            if parent:
                username_element = parent.find('a', href=re.compile(r'/[\w.]+/?$'))
                if username_element:
                    username = username_element.get_text(strip=True).lstrip('@')
            
            comment = Comment(
                id=f"ig_html_{hash(text_content + username)}",
                username=username,
                content=text_content,
                platform="instagram",
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
        
        # Get all text and look for patterns
        text_content = soup.get_text()
        
        # Pattern for username followed by comment text
        # Instagram usernames can contain dots and underscores
        username_pattern = r'([a-zA-Z0-9_.]+)\s+([^@\n]{10,}?)(?=\s+[a-zA-Z0-9_.]+\s+|$)'
        matches = re.findall(username_pattern, text_content, re.MULTILINE)
        
        for i, (username, content) in enumerate(matches):
            # Filter out obvious non-comments
            if any(word in content.lower() for word in ['follow', 'followers', 'following', 'posts']):
                continue
            
            if len(content.strip()) > 5:  # Minimum content length
                comment = Comment(
                    id=f"ig_pattern_{i}",
                    username=username,
                    content=content.strip(),
                    platform="instagram",
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