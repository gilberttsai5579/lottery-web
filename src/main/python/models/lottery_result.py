"""
Lottery result data model for lottery web application
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid

from .comment import Comment


class LotteryMode(Enum):
    """Lottery mode enumeration"""
    KEYWORD_FILTER = "1"  # Mode 1: Keyword filtering
    ALL_COMMENTERS = "2"  # Mode 2: All commenters
    MENTION_COUNT = "3"   # Mode 3: Mention count requirement


@dataclass
class LotteryResult:
    """
    Represents the result of a lottery draw
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Lottery parameters
    post_url: str = ""
    platform: str = ""  # "threads" or "instagram"
    mode: LotteryMode = LotteryMode.ALL_COMMENTERS
    winner_count: int = 1
    
    # Mode-specific parameters
    keyword: str = ""  # For mode 1
    mention_count_required: int = 1  # For mode 3
    
    # Results
    winners: List[Comment] = field(default_factory=list)
    all_participants: List[Comment] = field(default_factory=list)
    eligible_participants: List[Comment] = field(default_factory=list)
    
    # Statistics
    total_comments: int = 0
    total_participants: int = 0
    eligible_count: int = 0
    
    @property
    def mode_name(self) -> str:
        """Get human-readable mode name"""
        mode_names = {
            LotteryMode.KEYWORD_FILTER: "關鍵字篩選",
            LotteryMode.ALL_COMMENTERS: "所有留言者",
            LotteryMode.MENTION_COUNT: "標註指定帳號"
        }
        return mode_names.get(self.mode, "未知模式")
    
    def add_participant(self, comment: Comment):
        """Add a participant comment"""
        # Avoid duplicates based on username
        if not any(p.username == comment.username for p in self.all_participants):
            self.all_participants.append(comment)
    
    def filter_eligible_participants(self):
        """
        Filter participants based on lottery mode
        """
        self.eligible_participants = []
        
        for comment in self.all_participants:
            if self._is_eligible(comment):
                self.eligible_participants.append(comment)
        
        self.eligible_count = len(self.eligible_participants)
    
    def _is_eligible(self, comment: Comment) -> bool:
        """
        Check if a comment is eligible based on lottery mode
        """
        if self.mode == LotteryMode.KEYWORD_FILTER:
            # Mode 1: Must contain keyword
            return comment.contains_keyword(self.keyword)
        
        elif self.mode == LotteryMode.ALL_COMMENTERS:
            # Mode 2: All commenters are eligible
            return True
        
        elif self.mode == LotteryMode.MENTION_COUNT:
            # Mode 3: Must mention required number of accounts
            comment.extract_mentions()  # Ensure mentions are extracted
            return comment.mention_count() >= self.mention_count_required
        
        return False
    
    def conduct_lottery(self, seed: Optional[int] = None):
        """
        Conduct the lottery and select winners
        """
        import random
        
        if seed is not None:
            random.seed(seed)
        
        # Filter eligible participants
        self.filter_eligible_participants()
        
        # Select winners
        available_winners = min(self.winner_count, len(self.eligible_participants))
        if available_winners > 0:
            self.winners = random.sample(self.eligible_participants, available_winners)
        else:
            self.winners = []
        
        # Update statistics
        self.total_comments = len(self.all_participants)
        self.total_participants = len(set(p.username for p in self.all_participants))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert lottery result to dictionary for JSON serialization
        """
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'post_url': self.post_url,
            'platform': self.platform,
            'mode': self.mode.value,
            'mode_name': self.mode_name,
            'winner_count': self.winner_count,
            'keyword': self.keyword,
            'mention_count_required': self.mention_count_required,
            'winners': [winner.to_dict() for winner in self.winners],
            'total_comments': self.total_comments,
            'total_participants': self.total_participants,
            'eligible_count': self.eligible_count,
            'success': len(self.winners) > 0
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LotteryResult':
        """
        Create LotteryResult instance from dictionary
        """
        result = cls(
            id=data.get('id', str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.now(),
            post_url=data.get('post_url', ''),
            platform=data.get('platform', ''),
            mode=LotteryMode(data.get('mode', '2')),
            winner_count=data.get('winner_count', 1),
            keyword=data.get('keyword', ''),
            mention_count_required=data.get('mention_count_required', 1),
            total_comments=data.get('total_comments', 0),
            total_participants=data.get('total_participants', 0),
            eligible_count=data.get('eligible_count', 0)
        )
        
        # Restore winners
        if 'winners' in data:
            result.winners = [Comment.from_dict(winner) for winner in data['winners']]
        
        return result