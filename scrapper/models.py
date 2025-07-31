from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Place:
    name: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    rating: float = 0.0
    review_count: int = 0
    description: str = ""
    image_data: bytes = b""
    image_url: str = ""  # Added this field
    reviews: List[dict] = field(default_factory=list)
    
    # Additional fields that your extractor uses
    phone_number: str = ""  # Alias for phone
    reviews_count: int = 0  # Alias for review_count
    reviews_average: float = 0.0  # Alias for rating
