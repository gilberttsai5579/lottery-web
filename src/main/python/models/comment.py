"""
Comment data model for lottery web application
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Comment:
    """
    Represents a comment from Threads or Instagram post
    """
    id: str
    username: str
    content: str
    avatar_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    platform: str = ""  # "threads" or "instagram"
    post_url: str = ""
    
    # Additional metadata
    likes_count: int = 0
    replies_count: int = 0
    mentions: List[str] = None
    
    def __post_init__(self):
        """Initialize mentions list if None"""
        if self.mentions is None:
            self.mentions = []
    
    def extract_mentions(self) -> List[str]:
        """
        Extract mentioned usernames from comment content
        Returns list of usernames (without @ symbol)
        """
        import re
        mention_pattern = r'@([a-zA-Z0-9_\.]+)'
        mentions = re.findall(mention_pattern, self.content)
        # Remove duplicates and self-mentions
        unique_mentions = list(set(mentions))
        if self.username in unique_mentions:
            unique_mentions.remove(self.username)
        self.mentions = unique_mentions
        return unique_mentions
    
    def contains_keyword(self, keyword: str, case_sensitive: bool = False) -> bool:
        """
        Check if comment contains specific keyword
        """
        if not keyword:
            return True
        
        content = self.content if case_sensitive else self.content.lower()
        search_keyword = keyword if case_sensitive else keyword.lower()
        
        return search_keyword in content
    
    def mention_count(self) -> int:
        """
        Count number of mentions in the comment
        """
        if not self.mentions:
            self.extract_mentions()
        return len(self.mentions)
    
    def to_dict(self) -> dict:
        """
        Convert comment to dictionary for JSON serialization
        """
        return {
            'id': self.id,
            'username': self.username,
            'content': self.content,
            'avatar_url': self.avatar_url,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'platform': self.platform,
            'post_url': self.post_url,
            'likes_count': self.likes_count,
            'replies_count': self.replies_count,
            'mentions': self.mentions,
            'mention_count': self.mention_count()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Comment':
        """
        Create Comment instance from dictionary
        """
        # Parse timestamp if provided
        timestamp = None
        if data.get('timestamp'):
            if isinstance(data['timestamp'], str):
                timestamp = datetime.fromisoformat(data['timestamp'])
            else:
                timestamp = data['timestamp']
        
        return cls(
            id=data['id'],
            username=data['username'],
            content=data['content'],
            avatar_url=data.get('avatar_url'),
            timestamp=timestamp,
            platform=data.get('platform', ''),
            post_url=data.get('post_url', ''),
            likes_count=data.get('likes_count', 0),
            replies_count=data.get('replies_count', 0),
            mentions=data.get('mentions', [])
        )