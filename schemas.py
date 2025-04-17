from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel

class SearchType(str, Enum):
    WORD = "word"
    EXPLANATION = "explanation"
    REGEX = "regex"
    MIXED = "mixed"

class SearchRequest(BaseModel):
    query: str
    search_type: SearchType = SearchType.MIXED
    exact_match: bool = False
    limit: int = 50
    offset: int = 0

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int
    query: str
    search_type: str