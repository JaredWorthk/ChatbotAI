#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration settings for Railway AI Chatbot
File này chứa tất cả các cài đặt của project
"""
import os
from dotenv import load_dotenv

# Load file .env (nếu có) để đọc environment variables
load_dotenv()


class Config:
    """
    Class chứa tất cả configuration cho Railway Chatbot
    Tại sao cần class này:
    - Tập trung tất cả settings ở một nơi
    - Dễ thay đổi và maintain
    - Có thể có nhiều config khác nhau (dev, production)
    """

    # === FLASK WEB APP SETTINGS ===
    SECRET_KEY = os.getenv('SECRET_KEY', 'railway-ai-secret-key-2024')
    # SECRET_KEY: Dùng để encrypt session data, cookies
    # Giải thích: Flask cần secret key để bảo mật user sessions

    DEBUG = True  # Development mode - hiển thị errors chi tiết
    # DEBUG = True: Khi có lỗi sẽ show detailed error page
    # DEBUG = False: Production mode, chỉ show generic error

    HOST = '127.0.0.1'  # Localhost - chỉ access từ máy local
    PORT = 5000  # Port 5000 - Flask default port

    # === DATABASE SETTINGS ===
    DATABASE_PATH = 'railway_chatbot.db'  # Tên file SQLite database
    # Giải thích: SQLite tạo file .db để lưu trữ data

    # === AI SETTINGS ===
    # 🆓 FREE VERSION - Không cần OpenAI API
    USE_OPENAI = False  # Set True nếu muốn dùng OpenAI (có phí)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')  # Optional

    # Local AI Settings (FREE)
    LOCAL_MODEL_NAME = 'all-MiniLM-L6-v2'  # Sentence transformer model (free)
    AI_MODEL = 'gpt-3.5-turbo'  # Chỉ dùng nếu USE_OPENAI = True
    MAX_TOKENS = 200
    TEMPERATURE = 0.7

    # === CHATBOT BEHAVIOR SETTINGS ===
    SIMILARITY_THRESHOLD = 0.55  # Ngưỡng để match câu hỏi trong knowledge base
    # Giải thích: Nếu similarity score > 0.5 thì dùng answer từ knowledge base
    # Nếu < 0.5 thì dùng AI để generate response mới

    MAX_CONVERSATION_HISTORY = 10  # Nhớ tối đa 10 tin nhắn gần nhất
    # Giải thích: Để chatbot có context, nhưng không quá nhiều để tránh chậm

    # === LANGUAGE SETTINGS ===
    SUPPORTED_LANGUAGES = ['vi', 'en']  # Các ngôn ngữ được hỗ trợ
    DEFAULT_LANGUAGE = 'vi'  # Ngôn ngữ mặc định

    # === RAILWAY BUSINESS LOGIC ===
    DEFAULT_CATEGORIES = [
        'booking',  # Đặt vé tàu
        'schedule',  # Lịch trình, thời gian tàu
        'cancellation',  # Hủy vé, hoàn tiền
        'pricing',  # Giá vé, khuyến mãi
        'stations',  # Thông tin ga tàu
        'services',  # Dịch vụ trên tàu
        'support'  # Hỗ trợ khách hàng
    ]

    # === APP LIMITS (Để tránh spam và abuse) ===
    MAX_MESSAGE_LENGTH = 500  # Tin nhắn tối đa 500 ký tự
    RATE_LIMIT_PER_MINUTE = 60  # Tối đa 60 tin nhắn/phút/user


# === FUNCTIONS ===
def get_config():
    """
    Function để lấy config object
    Tại sao cần function này: Có thể thêm logic để chọn config khác nhau
    """
    return Config


def print_config():
    """
    Function để debug - in ra tất cả settings hiện tại
    """
    config = get_config()

    print("=== Railway AI Chatbot Configuration ===")
    print(f"🌐 Host: {config.HOST}:{config.PORT}")
    print(f"🗄️  Database: {config.DATABASE_PATH}")
    print(f"🤖 AI Model: {config.AI_MODEL}")
    print(f"🌍 Languages: {config.SUPPORTED_LANGUAGES}")
    print(f"📂 Categories: {len(config.DEFAULT_CATEGORIES)} categories")
    print(f"🔑 OpenAI Key: {'✅ Set' if config.OPENAI_API_KEY else '❌ Not set'}")
    print(f"🐛 Debug Mode: {'✅ ON' if config.DEBUG else '❌ OFF'}")


if __name__ == "__main__":
    # Nếu chạy file này directly, sẽ print config
    print_config()