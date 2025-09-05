"""
Railway AI Knowledge Base Engine
Handles search, retrieval and matching of railway-related questions and answers
"""

import json
import re
import os
from typing import List, Dict, Tuple, Optional, Any
from difflib import SequenceMatcher
import unicodedata
from collections import defaultdict
import math


class RailwayKnowledgeBase:
    """
    Advanced Knowledge Base Engine for Railway AI Chatbot
    Supports multiple search methods: keyword, fuzzy, semantic, category-based
    """

    def __init__(self, data_file_path: str = None):
        """
        Initialize the Knowledge Base

        Args:
            data_file_path: Path to railway_data.json file
        """
        self.data_file_path = "D:/for IT/PersonalProject/PythonProject/RailwayAI/app/data/railway_data.json"
        self.knowledge_data = {}
        self.questions = []
        self.categories = {}
        self.keyword_index = defaultdict(list)
        self.language_index = {"vi": [], "en": []}

        # Load and index data
        self.load_knowledge_base()
        self.build_indexes()

    # Tải lên Knowledge base
    def load_knowledge_base(self) -> bool:
        """
        Load knowledge base from JSON file

        Returns:
            bool: Success status
        """
        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as file:
                self.knowledge_data = json.load(file)
                self.questions = self.knowledge_data.get('knowledge_base', [])
                self.categories = self.knowledge_data.get('categories_description', {})
                print(f"✅ Loaded {len(self.questions)} questions from knowledge base")
                return True
        except FileNotFoundError:
            print(f"❌ Knowledge base file not found: {self.data_file_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading knowledge base: {e}")
            return False

    # Tạo index để truy xuất nhanh hơn
    def build_indexes(self):
        """
        Build search indexes for faster retrieval
        """
        self.keyword_index.clear()
        self.language_index = {"vi": [], "en": []}

        for idx, item in enumerate(self.questions):
            # Language index
            language = item.get('language', 'vi')
            self.language_index[language].append(idx)

            # Keyword index
            keywords = item.get('keywords', [])
            for keyword in keywords:
                normalized_keyword = self.normalize_text(keyword)
                self.keyword_index[normalized_keyword].append(idx)

            # Also index question and answer text
            question_words = self.extract_keywords(item.get('question', ''))
            answer_words = self.extract_keywords(item.get('answer', ''))

            for word in question_words + answer_words:
                if len(word) > 2:  # Skip very short words
                    self.keyword_index[word].append(idx)

        print(
            f"✅ Built indexes: {len(self.keyword_index)} keywords, {sum(len(v) for v in self.language_index.values())} language entries")

    # Chuẩn hóa Tiếng Việt để phù hợp hơn cho việc so sánh
    def normalize_text(self, text: str) -> str:
        """
        Normalize Vietnamese text for better matching

        Args:
            text: Input text

        Returns:
            str: Normalized text
        """
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove Vietnamese accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

        # Remove special characters and extra spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        text = ' '.join(text.split())

        return text

    # Trích xuất keywords
    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text

        Args:
            text: Input text

        Returns:
            List[str]: List of keywords
        """
        if not text:
            return []

        normalized = self.normalize_text(text)
        words = normalized.split()

        # Filter out common stop words
        stop_words = {
            'la', 'cua', 'va', 'co', 'khong', 'thi', 'se', 'duoc', 'nhu', 'theo',
            'trong', 'ngoai', 'tren', 'duoi', 'sau', 'truoc', 'giua', 'ben',
            'the', 'is', 'are', 'was', 'were', 'and', 'or', 'but', 'in', 'on', 'at'
        }

        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return keywords

    # Search for keyword
    def keyword_search(self, query: str, language: str = 'vi', limit: int = 5) -> List[Dict]:
        """
        Search using keyword matching

        Args:
            query: Search query
            language: Language preference
            limit: Maximum number of results

        Returns:
            List[Dict]: Matching results with scores
        """
        query_keywords = self.extract_keywords(query)
        if not query_keywords:
            return []

        # Score each question
        scores = defaultdict(float)

        for keyword in query_keywords:
            if keyword in self.keyword_index:
                for idx in self.keyword_index[keyword]:
                    # Prefer same language
                    item = self.questions[idx]
                    language_bonus = 1.5 if item.get('language') == language else 1.0
                    scores[idx] += language_bonus

        # Sort by score and return top results
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        results = []
        for idx, score in sorted_results:
            item = self.questions[idx].copy()
            item['search_score'] = score
            item['search_method'] = 'keyword'
            results.append(item)

        return results

    """
    Fuzzy search found top result with the highest score(similarity + (keyword_similarity * 0.8))
    Sequence :
    1. Lập danh sách chỉ mục cho các câu hỏi của các ngôn ngữ ưu tiên, chia ra thành các danh sách câu hỏi 
    theo ngôn ngữ ưu tiên, chuẩn hóa câu hỏi
    2. Tính toán điểm tương đồng cho câu hỏi của người dùng với danh sách chỉ mục các câu hỏi với ngôn ngữ 
    ưu tiên
    3. Tính toán điểm tương đồng cho cả keyword có trong câu hỏi của người dùng với keyword trong file 
    railway_data.json 
    4. Sử dụng công thức tính score và so sánh với threshold có trong railway_data.json 
    5. Sắp xếp theo score, và trả về top result
    """

    def fuzzy_search(self, query: str, language: str = 'vi', limit: int = 5, threshold: float = 0.3) -> List[Dict]:
        """
        Fuzzy matching search

        Args:
            query: Search query
            language: Language preference
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            List[Dict]: Matching results with scores
        """
        normalized_query = self.normalize_text(query)
        results = []

        # Get questions in preferred language first
        candidate_indices = self.language_index.get(language, []) + self.language_index.get(
            'vi' if language != 'vi' else 'en', [])

        for idx in candidate_indices[:50]:  # Limit candidates for performance
            item = self.questions[idx]
            question = self.normalize_text(item.get('question', ''))

            # Calculate similarity
            similarity = SequenceMatcher(None, normalized_query, question).ratio()

            # Also check keywords
            keywords = ' '.join(item.get('keywords', []))
            keyword_similarity = SequenceMatcher(None, normalized_query, self.normalize_text(keywords)).ratio()

            # Combined score
            combined_score = max(similarity, keyword_similarity * 0.8)

            if combined_score >= threshold:
                item_copy = item.copy()
                item_copy['search_score'] = combined_score
                item_copy['search_method'] = 'fuzzy'
                results.append(item_copy)

        # Sort by score and return top results
        results.sort(key=lambda x: x['search_score'], reverse=True)
        return results[:limit]

    # Tìm kiếm phân loại
    def category_search(self, query: str, language: str = 'vi', limit: int = 5) -> List[Dict]:
        """
        Search by category relevance

        Args:
            query: Search query
            language: Language preference
            limit: Maximum number of results

        Returns:
            List[Dict]: Matching results with scores
        """
        query_keywords = self.extract_keywords(query)
        if not query_keywords:
            return []

        # Category keyword mapping
        category_keywords = {
            'booking': ['dat ve', 'mua ve', 'book', 'reserve', 'online', 'app', 'website'],
            'schedule': ['lich tau', 'thoi gian', 'bao lau', 'schedule', 'time', 'duration'],
            'pricing': ['gia ve', 'cost', 'price', 'tien', 'khuyen mai', 'discount'],
            'stations': ['ga', 'station', 'dia chi', 'address', 'location'],
            'services': ['dich vu', 'wifi', 'do an', 'toilet', 'service', 'food'],
            'cancellation': ['huy ve', 'cancel', 'hoan tien', 'refund'],
            'support': ['hotline', 'support', 'help', 'lien he', 'contact']
        }

        # Find relevant categories
        category_scores = defaultdict(float)
        for keyword in query_keywords:
            for category, cat_keywords in category_keywords.items():
                for cat_keyword in cat_keywords:
                    if keyword in self.normalize_text(cat_keyword):
                        category_scores[category] += 1

        # Get questions from relevant categories
        results = []
        for category, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True):
            category_questions = [q for q in self.questions if q.get('category') == category]

            # Prefer same language
            lang_questions = [q for q in category_questions if q.get('language') == language]
            if not lang_questions:
                lang_questions = category_questions

            for item in lang_questions[:2]:  # Top 2 per category
                item_copy = item.copy()
                item_copy['search_score'] = score
                item_copy['search_method'] = 'category'
                results.append(item_copy)

        return results[:limit]

    # Main search dùng để navigate để tìm ra search methods phù hợp
    def search(self, query: str, language: str = 'vi', method: str = 'hybrid', limit: int = 5) -> List[Dict]:
        """
        Main search function with multiple methods

        Args:
            query: Search query
            language: Language preference ('vi' or 'en')
            method: Search method ('keyword', 'fuzzy', 'category', 'hybrid')
            limit: Maximum number of results

        Returns:
            List[Dict]: Search results
        """
        if not query or not query.strip():
            return []

        if method == 'keyword':
            return self.keyword_search(query, language, limit)
        elif method == 'fuzzy':
            return self.fuzzy_search(query, language, limit)
        elif method == 'category':
            return self.category_search(query, language, limit)
        elif method == 'hybrid':
            return self.hybrid_search(query, language, limit)
        else:
            return self.hybrid_search(query, language, limit)

    """
    Hybrid search combining các search methods xong tính ra score với tỉ lệ weight đã cho với mỗi loại 
    search methods và trả về danh sách các câu hỏi có top score với số lượng: limit
    Sequence :
    1. Get result từ các method
    2. Combine và deduplicate result
    3. Phân chia weight và tính score cho các chỉ mục và cho vào danh sách theo từng method, với các chỉ 
    mục được lặp lại với các method khác nhau thì score cho các chỉ mục đó sẽ tăng để score thể hiện được
    rõ ràng hơn
    4. Sắp xếp theo final score
    5. Trả về danh sách các chỉ mục với limit: số lượng
    """

    def hybrid_search(self, query: str, language: str = 'vi', limit: int = 5) -> List[Dict]:
        """
        Hybrid search combining multiple methods

        Args:
            query: Search query
            language: Language preference
            limit: Maximum number of results

        Returns:
            List[Dict]: Combined search results
        """
        # Get results from different methods
        keyword_results = self.keyword_search(query, language, limit * 2)
        fuzzy_results = self.fuzzy_search(query, language, limit * 2)
        category_results = self.category_search(query, language, limit)

        # Combine and deduplicate results
        combined_results = {}

        # Weight different search methods
        weights = {'keyword': 1.0, 'fuzzy': 0.8, 'category': 0.6}

        for results, method in [(keyword_results, 'keyword'), (fuzzy_results, 'fuzzy'), (category_results, 'category')]:
            for result in results:
                idx = result.get('id', 0)
                score = result.get('search_score', 0) * weights[method]

                if idx in combined_results:
                    # Boost score if found by multiple methods
                    combined_results[idx]['search_score'] += score * 0.5
                    combined_results[idx]['search_method'] += f', {method}'
                else:
                    result['search_score'] = score
                    result['search_method'] = method
                    combined_results[idx] = result

        # Sort by final score
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x['search_score'], reverse=True)

        return final_results[:limit]

    # Truy xuất câu hỏi by ID
    def get_by_id(self, question_id: int) -> Optional[Dict]:
        """
        Get question by ID

        Args:
            question_id: Question ID

        Returns:
            Optional[Dict]: Question data or None
        """
        for item in self.questions:
            if item.get('id') == question_id:
                return item
        return None

    # Truy xuất câu hỏi theo Category
    def get_by_category(self, category: str, language: str = 'vi', limit: int = 10) -> List[Dict]:
        """
        Get questions by category

        Args:
            category: Category name
            language: Language preference
            limit: Maximum number of results

        Returns:
            List[Dict]: Questions in category
        """
        results = []
        for item in self.questions:
            if item.get('category') == category:
                # Prefer same language
                if item.get('language') == language:
                    results.insert(0, item)
                else:
                    results.append(item)

        return results[:limit]

    # Truy xuất các câu hỏi trương đồng dựa trên category và keywords
    def get_similar_questions(self, question_id: int, limit: int = 3) -> List[Dict]:
        """
        Get similar questions based on category and keywords

        Args:
            question_id: Reference question ID
            limit: Maximum number of results

        Returns:
            List[Dict]: Similar questions
        """
        reference = self.get_by_id(question_id)
        if not reference:
            return []

        ref_category = reference.get('category')
        ref_keywords = set(reference.get('keywords', []))
        ref_language = reference.get('language', 'vi')

        similar = []
        for item in self.questions:
            if item.get('id') == question_id:
                continue

            # Calculate similarity score
            score = 0

            # Same category bonus
            if item.get('category') == ref_category:
                score += 2

            # Keyword overlap
            item_keywords = set(item.get('keywords', []))
            overlap = len(ref_keywords.intersection(item_keywords))
            score += overlap

            # Same language bonus
            if item.get('language') == ref_language:
                score += 1

            if score > 0:
                item_copy = item.copy()
                item_copy['similarity_score'] = score
                similar.append(item_copy)

        # Sort by similarity score
        similar.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similar[:limit]

    """
    Get stat information 
    Total question: Number of questions
    Categories: {'Categories name': Number of categories questions,...}, 
    Languages: {'Languages name': Number of languages questions,...},
    Total keyworlds: Number of keywords,
    Confidence threshold: [Threshold sequence of all questions from first to last],
    Average confidence threshold: Average threshold.
    """

    def get_stats(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics

        Returns:
            Dict: Statistics information
        """
        stats = {
            'total_questions': len(self.questions),
            'categories': {},
            'languages': {},
            'total_keywords': len(self.keyword_index),
            'confidence_thresholds': []
        }

        # Category stats
        for item in self.questions:
            category = item.get('category', 'unknown')
            language = item.get('language', 'unknown')
            confidence = item.get('confidence_threshold', 0)

            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            stats['languages'][language] = stats['languages'].get(language, 0) + 1
            stats['confidence_thresholds'].append(confidence)

        # Average confidence
        if stats['confidence_thresholds']:
            stats['avg_confidence'] = sum(stats['confidence_thresholds']) / len(stats['confidence_thresholds'])

        return stats

    """"
    Validate method to define knowledge base incase 
    {missing_fields,low_confidence,duplicate_questions,empty_answers}
    Sequence :
    1. Check required file
    2. Check confidence threshold
    3. Check for duplicates
    4. Check for empty answers
    5. Return dictionary: issues
    """

    def validate_knowledge_base(self) -> Dict[str, List[str]]:
        """
        Validate knowledge base for issues

        Returns:
            Dict: Validation results
        """
        issues = {
            'missing_fields': [],
            'low_confidence': [],
            'duplicate_questions': [],
            'empty_answers': []
        }

        seen_questions = {}
        required_fields = ['id', 'question', 'answer', 'category', 'keywords']

        for idx, item in enumerate(self.questions):
            # Check required fields
            for field in required_fields:
                if not item.get(field):
                    issues['missing_fields'].append(f"Question {idx}: Missing {field}")

            # Check confidence threshold
            confidence = item.get('confidence_threshold', 0)
            if confidence < 0.5:
                issues['low_confidence'].append(f"Question {item.get('id', idx)}: Low confidence {confidence}")

            # Check for duplicates
            question = self.normalize_text(item.get('question', ''))
            if question in seen_questions:
                issues['duplicate_questions'].append(
                    f"Question {item.get('id', idx)}: Duplicate of {seen_questions[question]}")
            else:
                seen_questions[question] = item.get('id', idx)

            # Check empty answers
            answer = item.get('answer', '').strip()
            if not answer or len(answer) < 10:
                issues['empty_answers'].append(f"Question {item.get('id', idx)}: Empty or very short answer")

        return issues


# Example usage and testing functions
def test_knowledge_base():
    """Test the knowledge base functionality"""
    print("🧪 Testing Railway Knowledge Base Engine")
    print("=" * 50)

    # Initialize knowledge base
    kb = RailwayKnowledgeBase()

    if not kb.questions:
        print("❌ No knowledge base data loaded")
        return

    # Test different search methods
    test_queries = [
        "Làm thế nào để đặt vé tàu?",
        "Giá vé Hà Nội TP.HCM",
        "Tàu có wifi không",
        "train ticket booking",
        "Ga Sài Gòn ở đâu"
    ]

    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 30)

        # Test hybrid search
        results = kb.search(query, method='hybrid', limit=3)

        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. ID: {result.get('id')} | Score: {result.get('search_score', 0):.2f}")
                print(f"    Q: {result.get('question', '')[:80]}...")
                print(f"    Method: {result.get('search_method', '')}")
                print(f"    Answer: {result.get('answer', '')}")
                print()
        else:
            print("   No results found")

    # Print statistics
    print("\n📊 Knowledge Base Statistics:")
    print("-" * 30)
    stats = kb.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_knowledge_base()
