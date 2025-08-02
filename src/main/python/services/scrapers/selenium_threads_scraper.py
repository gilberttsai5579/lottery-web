"""
Selenium-based Threads scraper for handling dynamic content
"""
import re
import time
from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import urlparse

from ...models import Comment
from .selenium_base_scraper import SeleniumBaseScraper, ScrapingError
from ...auth import AuthManager
from ...config.auth_config import auth_config


class SeleniumThreadsScraper(SeleniumBaseScraper):
    """
    Selenium-powered scraper for Threads posts with authentication support
    """
    
    THREADS_DOMAINS = ['threads.com', 'www.threads.com', 'threads.net', 'www.threads.net']
    
    def __init__(self, *args, **kwargs):
        """Initialize Selenium Threads scraper with authentication support"""
        super().__init__(*args, **kwargs)
        
        # Initialize authentication manager
        self.auth_manager = AuthManager(auth_config)
        self.logger.info("Initialized Selenium Threads scraper with authentication support")
    
    # Common selectors for Threads elements (will be dynamically discovered)
    COMMENT_SELECTORS = [
        # Data test IDs
        '[data-testid*="comment"]',
        '[data-testid*="reply"]',
        '[data-testid*="thread"]',
        
        # ARIA roles
        '[role="article"]',
        '[role="listitem"]',
        
        # Common class patterns (these change frequently)
        '[class*="comment"]',
        '[class*="reply"]',
        '[class*="thread"]',
        
        # Text-based detection
        'div[class*="x"]:has-text("@")',  # Elements containing mentions
        
        # Structure-based detection
        'div:has(img) + div:has(div)',  # Avatar + content structure
    ]
    
    USERNAME_SELECTORS = [
        'a[href*="/@"]',
        '[data-testid*="username"]',
        '[class*="username"]',
        'span:contains("@")',
    ]
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is a Threads post URL
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
        """
        try:
            path_parts = urlparse(url).path.split('/')
            post_index = path_parts.index('post')
            if post_index + 1 < len(path_parts):
                return path_parts[post_index + 1]
            raise ValueError("Post ID not found in URL")
        except (ValueError, IndexError) as e:
            raise ScrapingError(f"Invalid Threads URL format: {e}")
    
    def scrape_comments(self, url: str) -> List[Comment]:
        """
        Scrape comments from Threads post using Selenium with authentication
        """
        if not self.validate_url(url):
            raise ScrapingError("Invalid Threads URL")
        
        self.logger.info(f"Scraping Threads post with Selenium: {url}")
        
        try:
            # Navigate to the URL
            page_source = self._make_request(url)
            
            # Check if authentication is required and handle it
            if self._check_login_required():
                self.logger.info("Authentication required, attempting to authenticate...")
                
                if self.auth_manager.authenticate_for_url(self.driver, url):
                    self.logger.info("Authentication successful, retrying page load...")
                    # Retry loading the page after authentication
                    self.driver.refresh()
                    time.sleep(3)
                    
                    # Check again if login is still required
                    if self._check_login_required():
                        raise ScrapingError("Authentication failed - still requires login")
                else:
                    raise ScrapingError("Authentication was not completed")
            
            # Wait for comment section to load
            self._wait_for_comments_section()
            
            # Scroll to load more comments
            self.scroll_to_load_content(max_scrolls=3, scroll_pause=2.0)
            
            # Extract comments using multiple strategies
            comments = []
            
            # Strategy 1: Use Selenium to find dynamic elements
            selenium_comments = self._extract_with_selenium()
            if selenium_comments:
                comments.extend(selenium_comments)
                self.logger.info(f"Selenium extraction found {len(selenium_comments)} comments")
            
            # Strategy 2: Parse current page source with BeautifulSoup
            if not comments:
                soup = self.get_soup()
                soup_comments = self._extract_with_beautifulsoup(soup, url)
                comments.extend(soup_comments)
                self.logger.info(f"BeautifulSoup extraction found {len(soup_comments)} comments")
            
            # Strategy 3: JavaScript-based extraction
            if not comments:
                js_comments = self._extract_with_javascript(url)
                comments.extend(js_comments)
                self.logger.info(f"JavaScript extraction found {len(js_comments)} comments")
            
            # Remove duplicates
            unique_comments = self._deduplicate_comments(comments)
            
            self.logger.info(f"Total unique comments extracted: {len(unique_comments)}")
            return unique_comments
            
        except Exception as e:
            self.logger.error(f"Failed to scrape Threads comments: {e}")
            raise ScrapingError(f"Failed to scrape Threads comments: {e}")
    
    def _check_login_required(self) -> bool:
        """
        Check if the page requires login
        """
        try:
            # Look for login indicators
            login_indicators = [
                "Log in",
                "Sign up",
                "登入",
                "註冊",
                "login",
                "sign-up"
            ]
            
            page_text = self.driver.page_source.lower()
            login_detected = any(indicator.lower() in page_text for indicator in login_indicators)
            
            # Also check URL for login redirect
            current_url = self.driver.current_url
            if 'login' in current_url.lower() or 'auth' in current_url.lower():
                login_detected = True
            
            if login_detected:
                self.logger.warning("Login page detected")
                
            return login_detected
            
        except Exception as e:
            self.logger.debug(f"Error checking login status: {e}")
            return False
    
    def _wait_for_comments_section(self) -> bool:
        """
        Wait for comments section to appear
        """
        self.logger.info("Waiting for comments section to load...")
        
        # Wait for various possible comment containers
        possible_selectors = [
            (By.CSS_SELECTOR, '[role="main"]'),
            (By.CSS_SELECTOR, '[data-testid*="thread"]'),
            (By.CSS_SELECTOR, 'main'),
            (By.CSS_SELECTOR, 'article'),
            (By.TAG_NAME, 'main'),
        ]
        
        for selector in possible_selectors:
            if self.wait_for_element(selector, timeout=10):
                self.logger.info(f"Found content area with selector: {selector}")
                time.sleep(2)  # Allow time for dynamic content to load
                return True
        
        self.logger.warning("No specific comments section found, proceeding with general content")
        return False
    
    def _extract_with_selenium(self) -> List[Comment]:
        """
        Extract comments using Selenium WebElement traversal
        """
        comments = []
        
        # Try different strategies to find comment elements
        for selector in self.COMMENT_SELECTORS:
            try:
                elements = self.get_elements(selector)
                self.logger.debug(f"Selector '{selector}' found {len(elements)} elements")
                
                for element in elements:
                    comment = self._parse_selenium_element(element)
                    if comment:
                        comments.append(comment)
                        
                if comments:
                    self.logger.info(f"Successfully extracted comments with selector: {selector}")
                    break
                    
            except Exception as e:
                self.logger.debug(f"Selector '{selector}' failed: {e}")
                continue
        
        # Try to find comments by looking for mention patterns
        if not comments:
            comments.extend(self._find_comments_by_mentions())
        
        return comments
    
    def _parse_selenium_element(self, element) -> Optional[Comment]:
        """
        Parse a Selenium WebElement to extract comment data
        """
        try:
            # Get text content
            text_content = element.text.strip()
            if not text_content or len(text_content) < 2:
                return None
            
            # Try to find username
            username = self._extract_username_from_element(element)
            if not username:
                # Try to extract from text content
                username_match = re.search(r'@(\w+)', text_content)
                if username_match:
                    username = username_match.group(1)
                else:
                    username = "unknown_user"
            
            # Try to find avatar
            avatar_url = self._extract_avatar_from_element(element)
            
            # Create comment
            comment = Comment(
                id=f"selenium_threads_{hash(text_content + username)}",
                username=username.lstrip('@'),
                content=text_content,
                avatar_url=avatar_url,
                platform="threads",
                post_url=self.driver.current_url
            )
            
            comment.extract_mentions()
            return comment
            
        except Exception as e:
            self.logger.debug(f"Failed to parse Selenium element: {e}")
            return None
    
    def _extract_username_from_element(self, element) -> Optional[str]:
        """
        Extract username from Selenium element
        """
        try:
            # Try to find username links
            username_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/@"]')
            if username_links:
                href = username_links[0].get_attribute('href')
                if href:
                    match = re.search(r'/@([^/?]+)', href)
                    if match:
                        return match.group(1)
            
            # Try other username selectors
            for selector in self.USERNAME_SELECTORS:
                try:
                    username_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    if username_elements:
                        username_text = username_elements[0].text.strip()
                        if username_text:
                            return username_text.lstrip('@')
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to extract username: {e}")
            return None
    
    def _extract_avatar_from_element(self, element) -> Optional[str]:
        """
        Extract avatar URL from Selenium element
        """
        try:
            img_elements = element.find_elements(By.TAG_NAME, 'img')
            for img in img_elements:
                src = img.get_attribute('src')
                if src and ('profile' in src.lower() or 'avatar' in src.lower()):
                    return src
            
            # Return first image if no profile image found
            if img_elements:
                return img_elements[0].get_attribute('src')
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to extract avatar: {e}")
            return None
    
    def _find_comments_by_mentions(self) -> List[Comment]:
        """
        Find comments by looking for @ mentions
        """
        comments = []
        
        try:
            # Use JavaScript to find elements containing @ symbols
            js_script = """
            var elements = document.querySelectorAll('*');
            var mentionElements = [];
            for (var i = 0; i < elements.length; i++) {
                if (elements[i].textContent && elements[i].textContent.includes('@')) {
                    mentionElements.push(elements[i]);
                }
            }
            return mentionElements.slice(0, 50); // Limit to first 50
            """
            
            mention_elements = self.execute_script(js_script)
            if not mention_elements:
                return comments
            
            for element in mention_elements[:20]:  # Process first 20
                try:
                    text_content = element.text.strip()
                    if text_content and '@' in text_content and len(text_content) > 5:
                        # Extract potential username
                        username_match = re.search(r'@(\w+)', text_content)
                        username = username_match.group(1) if username_match else "unknown_user"
                        
                        comment = Comment(
                            id=f"selenium_mention_{hash(text_content + username)}",
                            username=username,
                            content=text_content,
                            platform="threads",
                            post_url=self.driver.current_url
                        )
                        comment.extract_mentions()
                        comments.append(comment)
                except:
                    continue
            
        except Exception as e:
            self.logger.debug(f"Failed to find comments by mentions: {e}")
        
        return comments
    
    def _extract_with_beautifulsoup(self, soup, url: str) -> List[Comment]:
        """
        Extract comments using BeautifulSoup on current page source
        """
        comments = []
        
        # Use the existing BeautifulSoup extraction methods from the original scraper
        # This provides a fallback when Selenium element traversal fails
        
        # Look for text patterns that might indicate comments
        text_content = soup.get_text()
        
        # Pattern for @username mentions followed by text
        mention_pattern = r'@(\\w+)\\s+([^@]+?)(?=@|\\n|$)'
        matches = re.findall(mention_pattern, text_content, re.MULTILINE)
        
        for i, (username, content) in enumerate(matches):
            if len(content.strip()) > 10:  # Filter out very short content
                comment = Comment(
                    id=f"selenium_soup_{i}",
                    username=username,
                    content=content.strip(),
                    platform="threads",
                    post_url=url
                )
                comment.extract_mentions()
                comments.append(comment)
        
        return comments
    
    def _extract_with_javascript(self, url: str) -> List[Comment]:
        """
        Extract comments using JavaScript execution
        """
        comments = []
        
        try:
            # JavaScript to extract comment-like structures
            js_script = """
            var comments = [];
            var allElements = document.querySelectorAll('div, article, section');
            
            for (var i = 0; i < allElements.length; i++) {
                var element = allElements[i];
                var text = element.textContent || '';
                
                // Look for elements that might be comments
                if (text.length > 10 && text.length < 1000 && text.includes('@')) {
                    var usernameMatch = text.match(/@(\\w+)/);
                    if (usernameMatch) {
                        comments.push({
                            username: usernameMatch[1],
                            content: text.trim(),
                            hasAvatar: element.querySelector('img') !== null
                        });
                    }
                }
            }
            
            return comments.slice(0, 20); // Limit results
            """
            
            js_comments = self.execute_script(js_script)
            
            if js_comments:
                for i, js_comment in enumerate(js_comments):
                    comment = Comment(
                        id=f"selenium_js_{i}",
                        username=js_comment.get('username', 'unknown_user'),
                        content=js_comment.get('content', ''),
                        platform="threads",
                        post_url=url
                    )
                    comment.extract_mentions()
                    comments.append(comment)
            
        except Exception as e:
            self.logger.debug(f"JavaScript extraction failed: {e}")
        
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
    
    def cleanup(self):
        """
        Clean up resources including authentication state
        """
        # Cleanup authentication if needed
        if hasattr(self, 'auth_manager') and self.auth_manager:
            try:
                if self.auth_manager.is_authenticated:
                    self.logger.info("Cleaning up authentication state")
                    # Note: We don't logout here to preserve cookies for future use
                    # Only clear the in-memory state
                    self.auth_manager.is_authenticated = False
            except Exception as e:
                self.logger.warning(f"Error during auth cleanup: {e}")
        
        # Call parent cleanup
        super().cleanup()