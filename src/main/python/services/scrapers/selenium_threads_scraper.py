"""
Selenium-based Threads scraper for handling dynamic content
"""
import re
import time
from typing import List, Optional
from datetime import datetime, timedelta
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
    
    # Improved selectors for Threads comment elements
    COMMENT_SELECTORS = [
        # High priority: Specific data test IDs for comments
        '[data-testid*="comment"]',
        '[data-testid*="reply"]',
        '[data-testid*="thread-item"]',
        '[data-testid="post"]',
        
        # ARIA roles that commonly contain comments
        '[role="article"]',
        '[role="listitem"]',
        '[role="group"]',
        
        # Structural patterns: Comment containers with user info
        'div:has(img[alt*="profile"]) + div',  # Avatar + content structure
        'div:has(img[alt*="avatar"]) + div',
        'div:has(a[href*="/@"]):has(span)',  # Username link + content
        
        # Look for elements containing usernames and text
        'div:has(a[href*="/@"]):not(:has(video)):not(:has(img[src*="media"]))',
        
        # Comment thread patterns
        'div[class*="x"]:has(a[href*="/@"]):has(span)',
        'div[class*="thread"]:has(a[href*="/@"])',
        
        # Fallback: General content with user mentions
        'div:contains("@"):has(a[href*="/@"])',
    ]
    
    USERNAME_SELECTORS = [
        # High priority: Direct username links
        'a[href*="/@"]',
        
        # Data attributes
        '[data-testid*="username"]',
        '[data-testid*="user"]',
        
        # Class patterns
        '[class*="username"]',
        '[class*="user"]',
        
        # Text content patterns
        'span:contains("@")',
        'div:contains("@")',
        
        # Structural patterns
        'img[alt*="profile"] + span',
        'img[alt*="avatar"] + span',
        'img + div > span:first-child',
    ]
    
    # Timestamp selectors for extracting post/comment time
    TIMESTAMP_SELECTORS = [
        # High priority: Semantic time elements
        'time',
        '[datetime]',
        
        # Data attributes
        '[data-testid*="time"]',
        '[data-testid*="timestamp"]',
        '[data-testid*="date"]',
        
        # Class patterns
        '[class*="time"]',
        '[class*="timestamp"]',
        '[class*="date"]',
        
        # ARIA labels
        '[aria-label*="時間"]',
        '[aria-label*="time"]',
        '[aria-label*="ago"]',
        '[aria-label*="前"]',
        
        # Title attributes (hover text)
        'span[title*=":"]',  # Often contains full timestamp
        'a[title*=":"]',
        
        # Relative time text patterns (English)
        'span[textContent*="h"]',
        'span[textContent*="m"]', 
        'span[textContent*="d"]',
        'span[textContent*="w"]',
        
        # Relative time text patterns (Chinese)
        'span[textContent*="小時"]',
        'span[textContent*="分鐘"]',
        'span[textContent*="天"]',
        'span[textContent*="週"]',
        'span[textContent*="秒"]',
        
        # Generic patterns for small text near username
        'a[href*="/@"] + span',
        'a[href*="/@"] ~ span:last-child',
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
            
            # Scroll to load more comments with improved strategy
            self._smart_scroll_for_comments()
            
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
        Wait for comments section to appear with improved stability
        """
        self.logger.info("Waiting for comments section to load...")
        
        # Wait for various possible comment containers with longer timeout
        possible_selectors = [
            (By.CSS_SELECTOR, '[role="main"]'),
            (By.CSS_SELECTOR, '[data-testid*="thread"]'),
            (By.CSS_SELECTOR, '[data-testid*="post"]'),
            (By.CSS_SELECTOR, 'main'),
            (By.CSS_SELECTOR, 'article'),
            (By.TAG_NAME, 'main'),
        ]
        
        # Try multiple times with different selectors
        for selector in possible_selectors:
            if self.wait_for_element(selector, timeout=15):
                self.logger.info(f"Found content area with selector: {selector}")
                
                # Wait for content to fully load
                time.sleep(3)
                
                # Additional check: wait for comments to appear
                if self._wait_for_comment_elements():
                    return True
        
        self.logger.warning("No specific comments section found, proceeding with general content")
        return False
    
    def _wait_for_comment_elements(self) -> bool:
        """
        Wait specifically for comment elements to appear
        """
        try:
            # Wait for elements that typically contain comments
            comment_indicators = [
                'a[href*="/@"]',  # Username links
                '[data-testid*="comment"]',
                '[role="article"]',
                'time, [datetime]',  # Timestamp elements
            ]
            
            for indicator in comment_indicators:
                try:
                    elements = self.get_elements(indicator)
                    if elements and len(elements) > 0:
                        self.logger.info(f"Found {len(elements)} comment indicators with: {indicator}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error waiting for comment elements: {e}")
            return False
    
    def _smart_scroll_for_comments(self):
        """
        Smart scrolling strategy to load comments progressively
        """
        try:
            self.logger.info("Starting smart scroll to load comments...")
            
            # Get initial comment count
            initial_count = len(self.get_elements('a[href*="/@"]'))
            self.logger.info(f"Initial comment indicators found: {initial_count}")
            
            scroll_attempts = 0
            max_scrolls = 5
            no_new_content_count = 0
            
            while scroll_attempts < max_scrolls and no_new_content_count < 2:
                # Scroll down
                self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Check for loading indicators
                loading_elements = self.get_elements('[aria-label*="loading"], [data-testid*="loading"], .loading')
                if loading_elements:
                    self.logger.info("Loading indicator found, waiting...")
                    time.sleep(3)
                
                # Count new comment indicators
                new_count = len(self.get_elements('a[href*="/@"]'))
                
                if new_count > initial_count:
                    self.logger.info(f"Found {new_count - initial_count} new comment indicators")
                    initial_count = new_count
                    no_new_content_count = 0
                else:
                    no_new_content_count += 1
                    self.logger.debug(f"No new content found (attempt {no_new_content_count})")
                
                scroll_attempts += 1
                
                # Progressive wait - longer waits for later scrolls
                wait_time = 2 + scroll_attempts * 0.5
                time.sleep(wait_time)
            
            self.logger.info(f"Scroll complete. Final comment indicators: {initial_count}")
            
        except Exception as e:
            self.logger.warning(f"Error during smart scroll: {e}")
            # Fallback to basic scroll
            self.scroll_to_load_content(max_scrolls=3, scroll_pause=2.0)
    
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
            
            # Check if this is a text comment (not just images)
            if not self._is_text_comment(element, text_content):
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
            
            # Clean the content to remove non-text elements
            cleaned_content = self._clean_comment_content(text_content)
            if not cleaned_content or len(cleaned_content.strip()) < 2:
                return None
            
            # Try to find avatar
            avatar_url = self._extract_avatar_from_element(element)
            
            # Try to extract timestamp
            timestamp = self._extract_timestamp_from_element(element)
            
            # Create comment
            comment = Comment(
                id=f"selenium_threads_{hash(cleaned_content + username)}",
                username=username.lstrip('@'),
                content=cleaned_content,
                avatar_url=avatar_url,
                timestamp=timestamp,
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
    
    def _extract_timestamp_from_element(self, element) -> Optional[datetime]:
        """
        Extract timestamp from Selenium element
        """
        try:
            # Try different timestamp selectors
            for selector in self.TIMESTAMP_SELECTORS:
                try:
                    timestamp_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    for ts_elem in timestamp_elements:
                        # Try datetime attribute first
                        datetime_attr = ts_elem.get_attribute('datetime')
                        if datetime_attr:
                            return self._parse_datetime_string(datetime_attr)
                        
                        # Try title attribute (often contains full timestamp)
                        title_attr = ts_elem.get_attribute('title')
                        if title_attr:
                            parsed_time = self._parse_datetime_string(title_attr)
                            if parsed_time:
                                return parsed_time
                        
                        # Try text content for relative time
                        text_content = ts_elem.text.strip()
                        if text_content:
                            parsed_time = self._parse_relative_time(text_content)
                            if parsed_time:
                                return parsed_time
                                
                except Exception as e:
                    self.logger.debug(f"Timestamp selector '{selector}' failed: {e}")
                    continue
            
            # Fallback: search for time patterns in element text
            element_text = element.text
            if element_text:
                return self._extract_time_from_text(element_text)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to extract timestamp: {e}")
            return None
    
    def _parse_datetime_string(self, datetime_str: str) -> Optional[datetime]:
        """
        Parse various datetime string formats
        """
        if not datetime_str:
            return None
            
        try:
            # ISO format
            if 'T' in datetime_str:
                return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            
            # Try common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%m/%d/%Y %H:%M',
                '%m/%d/%Y',
                '%d/%m/%Y %H:%M',
                '%d/%m/%Y',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Failed to parse datetime string '{datetime_str}': {e}")
            
        return None
    
    def _parse_relative_time(self, time_text: str) -> Optional[datetime]:
        """
        Parse relative time expressions like '2h', '1d', '3w' etc.
        """
        if not time_text:
            return None
            
        try:
            now = datetime.now()
            time_text = time_text.lower().strip()
            
            # Extract number and unit
            import re
            
            # English patterns
            patterns = [
                (r'(\\d+)\\s*s(?:ec(?:ond)?s?)?', 'seconds'),
                (r'(\\d+)\\s*m(?:in(?:ute)?s?)?', 'minutes'),
                (r'(\\d+)\\s*h(?:r|our)?s?', 'hours'),
                (r'(\\d+)\\s*d(?:ay)?s?', 'days'),
                (r'(\\d+)\\s*w(?:eek)?s?', 'weeks'),
                (r'(\\d+)\\s*mo(?:nth)?s?', 'months'),
                (r'(\\d+)\\s*y(?:ear)?s?', 'years'),
            ]
            
            # Chinese patterns
            chinese_patterns = [
                (r'(\\d+)\\s*秒', 'seconds'),
                (r'(\\d+)\\s*分(?:鐘)?', 'minutes'),
                (r'(\\d+)\\s*小時', 'hours'),
                (r'(\\d+)\\s*天', 'days'),
                (r'(\\d+)\\s*週', 'weeks'),
                (r'(\\d+)\\s*月', 'months'),
                (r'(\\d+)\\s*年', 'years'),
            ]
            
            all_patterns = patterns + chinese_patterns
            
            for pattern, unit in all_patterns:
                match = re.search(pattern, time_text)
                if match:
                    value = int(match.group(1))
                    
                    if unit == 'seconds':
                        return now - timedelta(seconds=value)
                    elif unit == 'minutes':
                        return now - timedelta(minutes=value)
                    elif unit == 'hours':
                        return now - timedelta(hours=value)
                    elif unit == 'days':
                        return now - timedelta(days=value)
                    elif unit == 'weeks':
                        return now - timedelta(weeks=value)
                    elif unit == 'months':
                        return now - timedelta(days=value * 30)  # Approximation
                    elif unit == 'years':
                        return now - timedelta(days=value * 365)  # Approximation
                        
        except Exception as e:
            self.logger.debug(f"Failed to parse relative time '{time_text}': {e}")
            
        return None
    
    def _extract_time_from_text(self, text: str) -> Optional[datetime]:
        """
        Extract timestamp from general text content
        """
        if not text:
            return None
            
        try:
            # Look for relative time patterns in the entire text
            lines = text.split('\\n')
            for line in lines:
                parsed_time = self._parse_relative_time(line.strip())
                if parsed_time:
                    return parsed_time
                    
        except Exception as e:
            self.logger.debug(f"Failed to extract time from text: {e}")
            
        return None
    
    def _is_text_comment(self, element, text_content: str) -> bool:
        """
        Check if this element represents a text comment (not just images)
        """
        try:
            # If there's substantial text content, it's likely a text comment
            if len(text_content.strip()) > 10:
                return True
            
            # Check if the element contains media without meaningful text
            media_elements = element.find_elements(By.CSS_SELECTOR, 'img, video, svg')
            text_elements = element.find_elements(By.CSS_SELECTOR, 'span, p, div')
            
            # If there are media elements but very little text, skip
            if media_elements and len(text_content.strip()) < 5:
                return False
            
            # Check for image-only patterns
            if (len(media_elements) > 0 and 
                len([elem for elem in text_elements if elem.text.strip()]) == 0):
                return False
            
            # Must contain some actual text (not just emojis or symbols)
            text_chars = re.sub(r'[^\w\s]', '', text_content)
            if len(text_chars.strip()) < 2:
                return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error checking if text comment: {e}")
            # Default to True to avoid false negatives
            return True
    
    def _clean_comment_content(self, content: str) -> str:
        """
        Clean comment content by removing unwanted elements
        """
        if not content:
            return ""
        
        try:
            # Remove extra whitespace and newlines
            cleaned = re.sub(r'\\s+', ' ', content.strip())
            
            # Remove common UI elements that appear in scraped text
            ui_patterns = [
                r'\\b(liked|like|reply|share|more|關於|回覆|分享|更多)\\b',
                r'\\b\\d+\\s*(likes?|replies?|個讚|則回覆)\\b',
                r'\\b(view|查看)\\s*(profile|個人檔案)\\b',
                r'\\b(follow|追蹤|following|已追蹤)\\b',
            ]
            
            for pattern in ui_patterns:
                cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
            # Remove extra spaces created by pattern removal
            cleaned = re.sub(r'\\s+', ' ', cleaned.strip())
            
            return cleaned
            
        except Exception as e:
            self.logger.debug(f"Error cleaning comment content: {e}")
            return content
    
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