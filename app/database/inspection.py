#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Inspection Tools for Railway AI Chatbot
File: database/inspection.py

Tại sao cần file này:
- Xem cấu trúc database ngay trong code
- Debug và monitor database
- Analyze usage patterns
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def print_database_structure(db_path: str):
    """
    In ra cấu trúc database một cách đẹp mắt
    Perfect để debug và kiểm tra
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        print("=" * 60)
        print("🗄️  RAILWAY AI CHATBOT - DATABASE STRUCTURE")
        print("=" * 60)

        # Database info
        db_exists = Path(db_path).exists()
        db_size = Path(db_path).stat().st_size / (1024 * 1024) if db_exists else 0

        print(f"📁 Database Path: {db_path}")
        print(f"📊 Database Exists: {'✅ YES' if db_exists else '❌ NO'}")
        print(f"💾 Database Size: {db_size:.2f} MB")

        # Lấy danh sách tables
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📈 Total Tables: {len(tables)}")

        # Chi tiết từng table
        for table_name in tables:
            print(f"\n📋 TABLE: {table_name.upper()}")

            # Đếm records
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            record_count = cursor.fetchone()[0]
            print(f"   📊 Records: {record_count:,}")

            # Lấy columns
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"   📝 Columns: {len(columns)}")

            for col in columns:
                flags = []
                if col[5]:  # primary_key
                    flags.append('🔑 PK')
                if col[3]:  # not_null
                    flags.append('⚠️  NOT NULL')
                if col[4]:  # default_value
                    flags.append(f"📌 DEFAULT: {col[4]}")

                flag_str = ' '.join(flags) if flags else ''
                print(f"      └─ {col[1]:<20} {col[2]:<15} {flag_str}")

        # Indexes
        cursor = conn.execute("""
            SELECT name, tbl_name FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
        """)
        indexes = cursor.fetchall()

        if indexes:
            print(f"\n🔍 INDEXES ({len(indexes)} total):")
            for idx in indexes:
                print(f"   └─ {idx[0]} → {idx[1]}")

        # Summary
        total_records = 0
        for table_name in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_records += cursor.fetchone()[0]

        print(f"\n📈 SUMMARY:")
        print(f"   Total Records: {total_records:,}")
        print(f"   Database Size: {db_size:.2f} MB")
        print("=" * 60)

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")


def show_sample_data(db_path: str, table_name: str, limit: int = 5):
    """
    Xem sample data của một table
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
        rows = cursor.fetchall()

        if not rows:
            print(f"📭 Table '{table_name}' is empty")
            return

        # Get column names
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]

        print(f"\n📋 SAMPLE DATA: {table_name.upper()} (Top {len(rows)} records)")
        print("-" * 80)

        for i, row in enumerate(rows, 1):
            print(f"Record #{i}:")
            for col_name in columns:
                value = row[col_name]
                # Truncate long values
                display_value = str(value)
                if len(display_value) > 50:
                    display_value = display_value[:47] + "..."
                print(f"  {col_name:<20}: {display_value}")
            print()

        conn.close()

    except Exception as e:
        print(f"❌ Error showing sample data: {e}")


def run_custom_query(db_path: str, query: str) -> List[Dict[str, Any]]:
    """
    Chạy custom SQL query
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(query)

        results = []
        for row in cursor.fetchall():
            results.append(dict(row))

        conn.close()
        return results

    except Exception as e:
        print(f"❌ Error running query: {e}")
        return []


def quick_database_info(db_path: str):
    """
    Xem nhanh thông tin database
    """
    try:
        conn = sqlite3.connect(db_path)

        # Lấy tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"🗄️  Database: {db_path}")
        print(f"📋 Tables: {tables}")

        # Đếm records từng table
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   📊 {table}: {count:,} records")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")


def database_health_check(db_path: str):
    """
    Kiểm tra sức khỏe database
    """
    print("🏥 DATABASE HEALTH CHECK")
    print("-" * 40)

    try:
        conn = sqlite3.connect(db_path)

        # 1. File exists?
        exists = Path(db_path).exists()
        print(f"📁 File exists: {'✅ YES' if exists else '❌ NO'}")

        if not exists:
            print("❌ Database file not found!")
            return

        # 2. Size
        size_mb = Path(db_path).stat().st_size / (1024 * 1024)
        print(f"💾 Size: {size_mb:.2f} MB")

        # 3. Integrity check
        cursor = conn.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        print(f"🔍 Integrity: {'✅ OK' if integrity == 'ok' else '❌ ISSUES'}")

        # 4. Tables count
        cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print(f"📋 Tables: {table_count}")

        # 5. Performance test
        import time
        start = time.time()
        cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master")
        cursor.fetchone()
        query_time = (time.time() - start) * 1000
        print(f"⚡ Query speed: {query_time:.2f}ms")

        conn.close()

    except Exception as e:
        print(f"❌ Health check failed: {e}")


# === EASY-TO-USE FUNCTIONS ===

def inspect_my_database():
    """
    Function để inspect database của bạn một cách nhanh chóng
    """
    db_path = "D:/for IT/PersonalProject/PythonProject/RailwayAI/app/database/railway_ai.db"

    print("🔍 RAILWAY AI DATABASE INSPECTION")
    print("=" * 50)

    # 1. Health check
    database_health_check(db_path)

    # 2. Quick info
    print(f"\n📊 QUICK INFO:")
    quick_database_info(db_path)

    # 3. Full structure
    print(f"\n🏗️  DETAILED STRUCTURE:")
    print_database_structure(db_path)

    # 4. Sample data
    print(f"\n📄 SAMPLE DATA:")
    show_sample_data(db_path, 'user_sessions', limit=2)


def show_useful_queries():
    """
    Hiển thị các SQL queries hữu ích
    """
    print("🔧 USEFUL SQL QUERIES")
    print("-" * 30)

    queries = {
        "Xem tất cả tables": "SELECT name FROM sqlite_master WHERE type='table';",
        "Đếm records": "SELECT COUNT(*) FROM conversations;",
        "Messages hôm nay": "SELECT COUNT(*) FROM conversations WHERE date(created_at) = date('now');",
        "Top categories": "SELECT category, COUNT(*) FROM conversations GROUP BY category ORDER BY COUNT(*) DESC;",
        "Recent sessions": "SELECT session_id, last_active FROM user_sessions ORDER BY last_active DESC LIMIT 5;"
    }

    for desc, sql in queries.items():
        print(f"\n📝 {desc}:")
        print(f"   {sql}")

    print(f"\n💡 Cách dùng:")
    print(f"   results = run_custom_query('railway_ai.db', 'YOUR_SQL_HERE')")


# === MAIN EXECUTION ===

if __name__ == "__main__":
    print("🚀 Running Database Inspection...")

    # Inspect database của bạn
    inspect_my_database()

    print(f"\n" + "=" * 60 + "\n")

    # Show useful queries
    show_useful_queries()

    print(f"\n🎯 CÁCH SỬ DỤNG:")
    print(f"   python database/inspection.py")
    print(f"   hoặc import functions vào code khác")