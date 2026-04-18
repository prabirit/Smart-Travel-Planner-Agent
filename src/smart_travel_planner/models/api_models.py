"""API response models for Smart Travel Planner."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class APIResponse:
    """Base API response."""
    success: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
            "data": self.data,
        }


@dataclass
class SuccessResponse(APIResponse):
    """Successful API response."""
    success: bool = True
    
    def __post_init__(self):
        """Post-initialization setup."""
        if not self.message:
            self.message = "Operation completed successfully"


@dataclass
class ErrorResponse(APIResponse):
    """Error API response."""
    success: bool = False
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        if self.error_details:
            self.data = self.error_details
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error response to dictionary."""
        base_dict = super().to_dict()
        if self.error_code:
            base_dict["error_code"] = self.error_code
        return base_dict


@dataclass
class PaginatedResponse(APIResponse):
    """Paginated API response."""
    page: int = 1
    page_size: int = 10
    total_items: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False
    
    def __post_init__(self):
        """Calculate pagination metadata."""
        if self.page_size > 0:
            self.total_pages = (self.total_items + self.page_size - 1) // self.page_size
            self.has_next = self.page < self.total_pages
            self.has_previous = self.page > 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert paginated response to dictionary."""
        base_dict = super().to_dict()
        pagination = {
            "page": self.page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }
        base_dict["pagination"] = pagination
        return base_dict
