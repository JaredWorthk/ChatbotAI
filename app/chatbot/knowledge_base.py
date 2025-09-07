"""
Railway AI Knowledge Base Engine
Handles search, retrieval and matching of railway-related questions and answers
"""

import json
import re
import os
import time
from typing import List, Dict, Tuple, Optional, Any
from difflib import SequenceMatcher
import unicodedata
from collections import defaultdict
import math

# Try to import fuzzywuzzy for better fuzzy search
try:
    from fuzzywuzzy import fuzz

    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    print("💡 Tip: Install fuzzywuzzy for better fuzzy search: pip install fuzzywuzzy")


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
        # Relative path - more portable than absolute
        default_path = os.path.join("data", "railway_data.json")
        self.data_file_path = "D:/for IT/PersonalProject/PythonProject/RailwayAI/app/data/railway_data.json" or default_path
        self.knowledge_data = {}
        self.questions = []
        self.categories = set()

        # Optimized indexes for O(1) lookups
        self.keyword_index = defaultdict(list)  # keyword -> [question_indices]
        self.id_index = {}  # id -> question_dict (O(1) lookup)
        self.category_index = defaultdict(list)  # category -> [question_dicts] (O(1) lookup)
        self.language_index = defaultdict(list)  # language -> [question_indices]

        # TF-IDF related
        self.keyword_document_frequency = defaultdict(int)  # keyword -> document count
        self.total_documents = 0

        # Dynamic category keywords (auto-generated from data)
        self.category_keywords = defaultdict(set)  # category -> {keywords}

        # Load and index data
        self.load_knowledge_base()
        self.build_indexes()

    # Tải lên knowledge base
    def load_knowledge_base(self) -> bool:
        """Load knowledge data from JSON file safely"""
        if not os.path.exists(self.data_file_path):
            print(f"[Warning] Data file not found: {self.data_file_path}")
            return False

        try:
            with open(self.data_file_path, "r", encoding="utf-8") as f:
                self.knowledge_data = json.load(f)
                # Correct key for railway_data.json structure
                self.questions = self.knowledge_data.get("knowledge_base", [])
                self.categories = set(item.get("category") for item in self.questions if item.get("category"))
                print(f"✅ Loaded {len(self.questions)} questions successfully")
                return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Error] Failed to load data: {e}")
            self.knowledge_data = {}
            self.questions = []
            self.categories = set()
            return False

    # Tạo index để truy xuất nhanh hơn
    def build_indexes(self):
        """Build optimized search indexes for faster retrieval with TF-IDF calculation"""
        # Clear existing indexes
        self.keyword_index.clear()
        self.id_index.clear()
        self.category_index.clear()
        self.category_keywords.clear()
        self.language_index.clear()
        self.keyword_document_frequency.clear()

        self.total_documents = len(self.questions)
        if self.total_documents == 0:
            print("[Warning] No questions to index")
            return

        for idx, item in enumerate(self.questions):
            # ID index for O(1) lookup
            item_id = item.get('id')
            if item_id is not None:
                self.id_index[item_id] = item

            # Language index - dynamic languages
            language = item.get('language', 'vi')
            self.language_index[language].append(idx)

            # Category index for O(1) lookup
            category = item.get('category')
            if category:
                self.category_index[category].append(item)

            # Extract ALL keywords from this document
            all_keywords = set()

            # 1. Keywords from metadata
            keywords = item.get('keywords', [])
            for keyword in keywords:
                normalized_keyword = self.normalize_text(keyword)
                if normalized_keyword:
                    all_keywords.add(normalized_keyword)

            # 2. Keywords from question text
            question_words = self.extract_keywords(item.get('question', ''))
            all_keywords.update(question_words)

            # 3. Keywords from answer text
            answer_words = self.extract_keywords(item.get('answer', ''))
            all_keywords.update(answer_words)

            # Build keyword index
            for keyword in all_keywords:
                if len(keyword) > 2:  # Skip very short words
                    self.keyword_index[keyword].append(idx)

            # Update document frequency for TF-IDF
            for keyword in all_keywords:
                self.keyword_document_frequency[keyword] += 1

            # Build dynamic category keywords
            if category:
                self.category_keywords[category].update(all_keywords)

        print(f"✅ Built optimized indexes:")
        print(f"   - {len(self.keyword_index)} keywords indexed")
        print(f"   - {len(self.id_index)} IDs indexed")
        print(f"   - {len(self.category_index)} categories indexed")
        print(f"   - {len(self.language_index)} languages supported: {list(self.language_index.keys())}")
        print(f"   - Language distribution: {dict((lang, len(indices)) for lang, indices in self.language_index.items())}")
        print(f"   - Auto-generated category keywords: {list(self.category_keywords.keys())}")

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
        Extract keywords from text with stop word filtering

        Args:
            text: Input text

        Returns:
            List[str]: List of keywords
        """
        if not text:
            return []

        normalized = self.normalize_text(text)
        words = normalized.split()

        # Enhanced stop words for Vietnamese and English
        stop_words = {
            # Vietnamese stop words
            'la', 'cua', 'va', 'co', 'khong', 'thi', 'se', 'duoc', 'nhu', 'theo',
            'trong', 'ngoai', 'tren', 'duoi', 'sau', 'truoc', 'giua', 'ben',
            'voi', 'cho', 'den', 'tu', 'khi', 'ma', 'neu', 'vi', 'boi', 'qua',
            # English stop words
            'the', 'is', 'are', 'was', 'were', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through'
        }

        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return keywords

    # Get tf-idf score(vector score)
    def get_tf_idf_score(self, keyword: str) -> float:
        """
        Calculate TF-IDF score for a keyword

        Args:
            keyword: The keyword to calculate score for

        Returns:
            float: TF-IDF score (higher = more important/rare)
        """
        if keyword not in self.keyword_document_frequency or self.total_documents == 0:
            return 0.0

        # IDF = log(total_docs / docs_containing_term)
        # Add 1 to avoid division by zero
        idf = math.log(self.total_documents / (1 + self.keyword_document_frequency[keyword]))
        return max(0.1, idf)  # Minimum score to avoid zero weights

    # Search for keyword
    def keyword_search(self, query: str, language: str = 'vi', limit: int = 5) -> List[Dict]:
        """
        Enhanced keyword search with TF-IDF scoring

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

        # Score each question with TF-IDF weighting
        scores = defaultdict(float)

        for keyword in query_keywords:
            if keyword in self.keyword_index:
                # Get TF-IDF weight for this keyword
                keyword_weight = self.get_tf_idf_score(keyword)

                for idx in self.keyword_index[keyword]:
                    # Prefer same language
                    item = self.questions[idx]
                    language_bonus = 1.5 if item.get('language') == language else 1.0

                    # Apply TF-IDF weighting
                    weighted_score = keyword_weight * language_bonus
                    scores[idx] += weighted_score

        # Sort by score and return top results
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        results = []
        for idx, score in sorted_results:
            item = self.questions[idx].copy()
            item['search_score'] = score
            item['search_method'] = 'keyword_tfidf'
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
        Enhanced fuzzy matching search with fuzzywuzzy or SequenceMatcher fallback

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

        # Get questions in preferred language first, then fallback
        candidate_indices = (self.language_index.get(language, []) +
                             self.language_index.get('vi' if language != 'vi' else 'en', []))

        # Limit candidates for performance but be smarter about selection
        max_candidates = min(100, len(candidate_indices))
        candidate_indices = candidate_indices[:max_candidates]

        for idx in candidate_indices:
            item = self.questions[idx]
            question = self.normalize_text(item.get('question', ''))

            # Calculate similarity using fuzzywuzzy if available
            if FUZZYWUZZY_AVAILABLE:
                similarity = fuzz.ratio(normalized_query, question) / 100.0
                # Also check keywords with fuzzywuzzy
                keywords = ' '.join(item.get('keywords', []))
                keyword_similarity = fuzz.partial_ratio(normalized_query, self.normalize_text(keywords)) / 100.0
            else:
                # Fallback to SequenceMatcher
                similarity = SequenceMatcher(None, normalized_query, question).ratio()
                keywords = ' '.join(item.get('keywords', []))
                keyword_similarity = SequenceMatcher(None, normalized_query, self.normalize_text(keywords)).ratio()

            # Combined score with weighted keyword importance
            combined_score = max(similarity, keyword_similarity * 0.8)

            # Boost score for exact keyword matches
            query_words = set(normalized_query.split())
            question_words = set(question.split())
            exact_matches = len(query_words.intersection(question_words))
            if exact_matches > 0:
                combined_score += exact_matches * 0.1

            if combined_score >= threshold:
                item_copy = item.copy()
                item_copy['search_score'] = combined_score
                item_copy['search_method'] = 'fuzzy_enhanced'
                results.append(item_copy)

        # Sort by score and return top results
        results.sort(key=lambda x: x['search_score'], reverse=True)
        return results[:limit]

    # Tìm kiếm phân loại
    def category_search(self, query: str, language: str = 'vi', limit: int = 5) -> List[Dict]:
        """
        Dynamic category search using auto-generated category keywords

        Args:
            query: Search query
            language: Language preference
            limit: Maximum number of results

        Returns:
            List[Dict]: Matching results with scores
        """
        query_keywords = set(self.extract_keywords(query))
        if not query_keywords:
            return []

        # Calculate category relevance using dynamic keywords
        category_scores = defaultdict(float)

        for category, cat_keywords in self.category_keywords.items():
            # Calculate overlap between query keywords and category keywords
            overlap = len(query_keywords.intersection(cat_keywords))
            if overlap > 0:
                # Score based on overlap percentage and TF-IDF
                overlap_ratio = overlap / len(query_keywords)

                # Add TF-IDF weighting for matched keywords
                tfidf_bonus = 0
                for keyword in query_keywords.intersection(cat_keywords):
                    tfidf_bonus += self.get_tf_idf_score(keyword)

                category_scores[category] = overlap_ratio + (tfidf_bonus * 0.1)

        # Get questions from relevant categories using O(1) lookup
        results = []
        for category, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True):
            category_questions = self.category_index.get(category, [])

            # Prefer same language
            lang_questions = [q for q in category_questions if q.get('language') == language]
            if not lang_questions:
                lang_questions = category_questions

            # Take top 2 per category to ensure diversity
            for item in lang_questions[:2]:
                item_copy = item.copy()
                item_copy['search_score'] = score
                item_copy['search_method'] = 'category_dynamic'
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
        Hybrid search combining multiple methods with intelligent weighting

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
        weights = {'keyword_tfidf': 1.0, 'fuzzy_enhanced': 0.8, 'category_dynamic': 0.6}

        for results, base_method in [(keyword_results, 'keyword'), (fuzzy_results, 'fuzzy'),
                                     (category_results, 'category')]:
            for result in results:
                idx = result.get('id', 0)
                method = result.get('search_method', base_method)
                score = result.get('search_score', 0) * weights.get(method, 0.5)

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
        Get question by ID using O(1) lookup

        Args:
            question_id: Question ID

        Returns:
            Optional[Dict]: Question data or None
        """
        return self.id_index.get(question_id)

    # Truy xuất câu hỏi by Categories
    def get_by_category(self, category: str, language: str = 'vi', limit: int = 10) -> List[Dict]:
        """
        Get questions by category using O(1) lookup

        Args:
            category: Category name
            language: Language preference
            limit: Maximum number of results

        Returns:
            List[Dict]: Questions in category
        """
        category_questions = self.category_index.get(category, [])

        # Prefer same language
        results = []
        same_lang = []
        other_lang = []

        for item in category_questions:
            if item.get('language') == language:
                same_lang.append(item)
            else:
                other_lang.append(item)

        # Combine with same language first
        results = same_lang + other_lang
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
        Get comprehensive knowledge base statistics

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

        # Category and language stats
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
        Validate knowledge base for potential issues

        Returns:
            Dict: Validation results with detailed issues
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


# Utility functions for testing and benchmarking
def install_dependencies():
    """Install recommended dependencies for optimal performance"""
    try:
        import subprocess
        import sys

        print("📦 Installing recommended dependencies...")

        # Try to install fuzzywuzzy for better fuzzy search
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "fuzzywuzzy", "python-Levenshtein"])
            print("✅ Installed fuzzywuzzy with C extensions for fast fuzzy matching")
        except Exception as e:
            print(f"⚠️ Could not install fuzzywuzzy: {e}")
            print("   Fuzzy search will use slower SequenceMatcher fallback")

    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")


def performance_benchmark(kb: RailwayKnowledgeBase):
    """Benchmark different search methods"""
    print("⚡ Performance Benchmark")
    print("=" * 40)

    if not kb.questions:
        print("❌ No knowledge base loaded for benchmark")
        return

    test_queries = [
        "đặt vé tàu online",
        "giá vé Hà Nội TP.HCM",
        "lịch tàu Sài Gòn",
        "hủy vé hoàn tiền",
        "ga tàu địa chỉ"
    ]

    methods = ['keyword', 'fuzzy', 'category', 'hybrid']

    for method in methods:
        start_time = time.time()
        total_results = 0

        for query in test_queries:
            results = kb.search(query, method=method, limit=5)
            total_results += len(results)

        end_time = time.time()
        avg_time = (end_time - start_time) / len(test_queries) * 1000

        print(f"{method:12}: {avg_time:6.2f}ms/query | {total_results} total results")

    # Test optimized lookups
    start_time = time.time()
    for i in range(1, min(46, len(kb.questions) + 1)):
        kb.get_by_id(i)
    end_time = time.time()
    id_lookup_time = (end_time - start_time) / min(45, len(kb.questions)) * 1000
    print(f"{'ID lookup':12}: {id_lookup_time:6.2f}ms/query (O(1) optimized)")


def test_knowledge_base():
    """Comprehensive test of the knowledge base functionality"""
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

        # Test hybrid search with enhanced scoring
        results = kb.search(query, method='hybrid', limit=3)

        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. ID: {result.get('id')} | Score: {result.get('search_score', 0):.3f}")
                print(f"   Q: {result.get('question', '')[:80]}...")
                print(f"   Method: {result.get('search_method', '')}")
                print()
        else:
            print("   No results found")

    # Test optimized lookups
    print("\n🚀 Testing Optimized Lookups:")
    print("-" * 30)

    # Test ID lookup
    test_item = kb.get_by_id(1)
    if test_item:
        print(f"✅ ID lookup (O(1)): {test_item.get('question', '')[:60]}...")

    # Test category lookup
    booking_questions = kb.get_by_category('booking', limit=3)
    print(f"✅ Category lookup (O(1)): Found {len(booking_questions)} booking questions")

    # Print statistics
    print("\n📊 Knowledge Base Statistics:")
    print("-" * 30)
    stats = kb.get_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        elif isinstance(value, list):
            print(f"{key}: {len(value)} items")
        else:
            print(f"{key}: {value}")

    # Validation
    print("\n🔍 Knowledge Base Validation:")
    print("-" * 30)
    issues = kb.validate_knowledge_base()
    total_issues = sum(len(issue_list) for issue_list in issues.values())

    if total_issues == 0:
        print("✅ No issues found - knowledge base is healthy!")
    else:
        for issue_type, issue_list in issues.items():
            if issue_list:
                print(f"⚠️ {issue_type}: {len(issue_list)} issues")
                for issue in issue_list[:3]:  # Show first 3 issues
                    print(f"   - {issue}")
                if len(issue_list) > 3:
                    print(f"   ... and {len(issue_list) - 3} more")

    # Run performance benchmark
    print("\n" + "=" * 50)
    performance_benchmark(kb)

    return kb


if __name__ == "__main__":
    # Uncomment to install dependencies
    if not FUZZYWUZZY_AVAILABLE:
        print("💡 For optimal performance, consider installing fuzzywuzzy:")
        print("   pip install fuzzywuzzy python-Levenshtein")
        print()

    test_knowledge_base()
