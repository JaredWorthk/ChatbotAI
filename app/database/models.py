#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Models for Railway AI Chatbot
File: database/models.py

Tại sao cần models này:
- Tổ chức data structure rõ ràng
- ORM giúp thao tác database dễ dàng hơn
- Type safety và validation
"""


from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class UserSession:
    """
    Model cho User Session - theo dõi người dùng

    Tại sao cần:
    - Phân biệt các user khác nhau
    - Lưu preferences (ngôn ngữ, settings)
    - Rate limiting theo user
    """
    session_id: str
    created_at: str
    last_active: str
    language: str = 'vi'
    message_count: int = 0
    preferences: Dict[str, Any] = None

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}


@dataclass
class Conversation:
    """
    Model cho Conversation - lưu trữ cuộc trò chuyện

    Tại sao cần:
    - Nhớ context của conversation
    - Phân tích user behavior
    - Cải thiện responses theo thời gian
    """
    id: Optional[int] = None
    session_id: str = ""
    user_message: str = ""
    bot_response: str = ""
    category: str = "general"
    confidence_score: float = 0.0
    response_time: float = 0.0
    feedback: Optional[str] = None  # 'good', 'bad', hoặc None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class KnowledgeBase:
    """
    Model cho Knowledge Base - câu hỏi và đáp án mẫu

    Tại sao cần:
    - Lưu trữ domain knowledge về railway
    - Training data cho AI
    - Quick responses cho câu hỏi phổ biến
    """
    id: Optional[int] = None
    question: str = ""
    answer: str = ""
    category: str = "general"
    keywords: List[str] = None
    language: str = "vi"
    confidence_threshold: float = 0.6
    usage_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
