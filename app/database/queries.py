
import sqlite3, json, hashlib, shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from app.database.models import UserSession, Conversation, KnowledgeBase

class DatabaseManager:
    """
    Class quản lý tất cả database operations

    Tại sao cần class này:
    - Tập trung tất cả DB operations
    - Connection management
    - Error handling
    - Database schema management
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Tạo connection tới database với proper settings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Cho phép access columns bằng tên
        return conn

    def init_database(self):
        """
        Tạo các tables cần thiết nếu chưa tồn tại
        """
        with self.get_connection() as conn:
            # Table cho User Sessions
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    language TEXT DEFAULT 'vi',
                    message_count INTEGER DEFAULT 0,
                    preferences TEXT DEFAULT '{}'
                )
            ''')

            # Table cho Conversations
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    confidence_score REAL DEFAULT 0.0,
                    response_time REAL DEFAULT 0.0,
                    feedback TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES user_sessions (session_id)
                )
            ''')

            # Table cho Knowledge Base
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    keywords TEXT DEFAULT '[]',
                    language TEXT DEFAULT 'vi',
                    confidence_threshold REAL DEFAULT 0.6,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # Indexes để tăng performance
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_conversations_session_id 
                ON conversations(session_id)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_conversations_category 
                ON conversations(category)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_knowledge_base_category 
                ON knowledge_base(category)
            ''')

            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_knowledge_base_language 
                ON knowledge_base(language)
            ''')

            conn.commit()

    # === USER SESSION OPERATIONS ===

    def create_session(self, session_data: UserSession) -> bool:
        """Tạo user session mới"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO user_sessions 
                    (session_id, created_at, last_active, language, message_count, preferences)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    session_data.session_id,
                    session_data.created_at,
                    session_data.last_active,
                    session_data.language,
                    session_data.message_count,
                    json.dumps(session_data.preferences)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Error creating session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Lấy thông tin session"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM user_sessions WHERE session_id = ?
                ''', (session_id,))
                row = cursor.fetchone()

                if row:
                    return UserSession(
                        session_id=row['session_id'],
                        created_at=row['created_at'],
                        last_active=row['last_active'],
                        language=row['language'],
                        message_count=row['message_count'],
                        preferences=json.loads(row['preferences'])
                    )
                return None
        except Exception as e:
            print(f"❌ Error getting session: {e}")
            return None

    def update_session_activity(self, session_id: str) -> bool:
        """Update thời gian active và tăng message count"""
        try:
            with self.get_connection() as conn:
                now = datetime.now().isoformat()
                conn.execute('''
                    UPDATE user_sessions 
                    SET last_active = ?, message_count = message_count + 1
                    WHERE session_id = ?
                ''', (now, session_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Error updating session: {e}")
            return False

    # === CONVERSATION OPERATIONS ===

    def save_conversation(self, conversation: Conversation) -> Optional[int]:
        """Lưu một conversation mới"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO conversations 
                    (session_id, user_message, bot_response, category, 
                     confidence_score, response_time, feedback, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conversation.session_id,
                    conversation.user_message,
                    conversation.bot_response,
                    conversation.category,
                    conversation.confidence_score,
                    conversation.response_time,
                    conversation.feedback,
                    conversation.created_at
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ Error saving conversation: {e}")
            return None

    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Conversation]:
        """Lấy lịch sử conversation của một session"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM conversations 
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (session_id, limit))

                conversations = []
                for row in cursor.fetchall():
                    conversations.append(Conversation(
                        id=row['id'],
                        session_id=row['session_id'],
                        user_message=row['user_message'],
                        bot_response=row['bot_response'],
                        category=row['category'],
                        confidence_score=row['confidence_score'],
                        response_time=row['response_time'],
                        feedback=row['feedback'],
                        created_at=row['created_at']
                    ))

                return list(reversed(conversations))  # Đảo ngược để có thứ tự chronological
        except Exception as e:
            print(f"❌ Error getting conversation history: {e}")
            return []

    def update_conversation_feedback(self, conversation_id: int, feedback: str) -> bool:
        """Update feedback cho một conversation"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    UPDATE conversations 
                    SET feedback = ?
                    WHERE id = ?
                ''', (feedback, conversation_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Error updating feedback: {e}")
            return False

    # === KNOWLEDGE BASE OPERATIONS ===

    def add_knowledge(self, knowledge: KnowledgeBase) -> Optional[int]:
        """Thêm một entry vào knowledge base"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO knowledge_base 
                    (question, answer, category, keywords, language, 
                     confidence_threshold, usage_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    knowledge.question,
                    knowledge.answer,
                    knowledge.category,
                    json.dumps(knowledge.keywords),
                    knowledge.language,
                    knowledge.confidence_threshold,
                    knowledge.usage_count,
                    knowledge.created_at,
                    knowledge.updated_at
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ Error adding knowledge: {e}")
            return None

    def search_knowledge(self, category: str = None, language: str = 'vi') -> List[KnowledgeBase]:
        """Tìm kiếm trong knowledge base"""
        try:
            with self.get_connection() as conn:
                query = 'SELECT * FROM knowledge_base WHERE language = ?'
                params = [language]

                if category:
                    query += ' AND category = ?'
                    params.append(category)

                query += ' ORDER BY usage_count DESC'

                cursor = conn.execute(query, params)

                knowledge_list = []
                for row in cursor.fetchall():
                    knowledge_list.append(KnowledgeBase(
                        id=row['id'],
                        question=row['question'],
                        answer=row['answer'],
                        category=row['category'],
                        keywords=json.loads(row['keywords']),
                        language=row['language'],
                        confidence_threshold=row['confidence_threshold'],
                        usage_count=row['usage_count'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    ))

                return knowledge_list
        except Exception as e:
            print(f"❌ Error searching knowledge: {e}")
            return []

    def update_knowledge_usage(self, knowledge_id: int) -> bool:
        """Tăng usage count khi sử dụng một knowledge entry"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    UPDATE knowledge_base 
                    SET usage_count = usage_count + 1, 
                        updated_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), knowledge_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Error updating knowledge usage: {e}")
            return False

    # === UTILITY OPERATIONS ===

    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê tổng quan của database"""
        try:
            with self.get_connection() as conn:
                # Đếm conversations
                cursor = conn.execute('SELECT COUNT(*) as count FROM conversations')
                total_conversations = cursor.fetchone()['count']

                # Đếm sessions
                cursor = conn.execute('SELECT COUNT(*) as count FROM user_sessions')
                total_sessions = cursor.fetchone()['count']

                # Đếm knowledge entries
                cursor = conn.execute('SELECT COUNT(*) as count FROM knowledge_base')
                total_knowledge = cursor.fetchone()['count']

                # Top categories
                cursor = conn.execute('''
                    SELECT category, COUNT(*) as count 
                    FROM conversations 
                    GROUP BY category 
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                top_categories = [dict(row) for row in cursor.fetchall()]

                # Recent activity (last 24h)
                yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                cursor = conn.execute('''
                    SELECT COUNT(*) as count 
                    FROM conversations 
                    WHERE created_at >= ?
                ''', (yesterday,))
                recent_activity = cursor.fetchone()['count']

                return {
                    'total_conversations': total_conversations,
                    'total_sessions': total_sessions,
                    'total_knowledge': total_knowledge,
                    'top_categories': top_categories,
                    'recent_activity_24h': recent_activity,
                    'database_size_mb': self._get_database_size()
                }
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {}

    def _get_database_size(self) -> float:
        """Tính kích thước file database"""
        try:
            if Path(self.db_path).exists():
                size_bytes = Path(self.db_path).stat().st_size
                return round(size_bytes / (1024 * 1024), 2)  # Convert to MB
            return 0.0
        except:
            return 0.0

    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Xóa các sessions cũ để tiết kiệm không gian"""
        try:
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

            with self.get_connection() as conn:
                # Xóa conversations cũ trước
                cursor = conn.execute('''
                    DELETE FROM conversations 
                    WHERE session_id IN (
                        SELECT session_id FROM user_sessions 
                        WHERE last_active < ?
                    )
                ''', (cutoff_date,))
                deleted_conversations = cursor.rowcount

                # Xóa sessions cũ
                cursor = conn.execute('''
                    DELETE FROM user_sessions 
                    WHERE last_active < ?
                ''', (cutoff_date,))
                deleted_sessions = cursor.rowcount

                conn.commit()

                print(f"🧹 Cleaned up: {deleted_sessions} sessions, {deleted_conversations} conversations")
                return deleted_sessions
        except Exception as e:
            print(f"❌ Error cleaning up: {e}")
            return 0

    def backup_database(self, backup_path: str) -> bool:
        """Backup database tới file khác"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"💾 Database backed up to: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Error backing up database: {e}")
            return False


# === UTILITY FUNCTIONS ===

def generate_session_id() -> str:
    """
    Tạo unique session ID
    Dùng timestamp + random để đảm bảo unique
    """
    import uuid
    import time

    timestamp = str(int(time.time()))
    unique_id = str(uuid.uuid4())[:8]
    return f"session_{timestamp}_{unique_id}"


def validate_session_data(session_data: Dict[str, Any]) -> bool:
    """Validate session data trước khi lưu"""
    required_fields = ['session_id', 'created_at', 'last_active']

    for field in required_fields:
        if field not in session_data or not session_data[field]:
            return False

    # Validate language
    if session_data.get('language') not in ['vi', 'en']:
        return False

    return True


def hash_message(message: str) -> str:
    """
    Hash message để tạo unique identifier
    Dùng cho caching và duplicate detection
    """
    return hashlib.md5(message.encode('utf-8')).hexdigest()


# === TESTING FUNCTIONS ===

def test_database_operations():
    """
    Function test để verify database hoạt động đúng
    """
    print("🧪 Testing Database Operations...")

    # Test với in-memory database
    db_path = "D:/for IT/PersonalProject/PythonProject/RailwayAI/app/database/railway_ai.db"
    db = DatabaseManager(db_path)

    # Test 1: Create session
    session = UserSession(
        session_id=generate_session_id(),
        created_at=datetime.now().isoformat(),
        last_active=datetime.now().isoformat(),
        language='vi'
    )

    success = db.create_session(session)
    print(f"✅ Create session: {'PASS' if success else 'FAIL'}")

    # Test 2: Get session
    retrieved_session = db.get_session(session.session_id)
    print(f"✅ Get session: {'PASS' if retrieved_session else 'FAIL'}")

    # Test 3: Save conversation
    conversation = Conversation(
        session_id=session.session_id,
        user_message="Tàu từ Hà Nội đi TP.HCM mấy giờ?",
        bot_response="Tàu SE1 khởi hành 19:20, SE3 khởi hành 6:00",
        category="schedule",
        confidence_score=0.85
    )

    conv_id = db.save_conversation(conversation)
    print(f"✅ Save conversation: {'PASS' if conv_id else 'FAIL'}")

    # Test 4: Add knowledge
    knowledge = KnowledgeBase(
        question="Giá vé tàu Hà Nội - TP.HCM",
        answer="Giá vé tàu từ Hà Nội đi TP.HCM dao động từ 800.000đ đến 1.500.000đ tùy loại chỗ",
        category="pricing",
        keywords=["giá vé", "hà nội", "tp.hcm", "tàu"],
        language="vi"
    )

    kb_id = db.add_knowledge(knowledge)
    print(f"✅ Add knowledge: {'PASS' if kb_id else 'FAIL'}")

    # Test 5: Get statistics
    stats = db.get_statistics()
    print(f"✅ Get statistics: {'PASS' if stats else 'FAIL'}")
    print(f"📊 Stats: {stats}")

    print("🎉 All tests completed!")

if __name__ == "__main__":
    # Chạy tests nếu execute file này directly
    test_database_operations()