import os
from app.database.queries import DatabaseManager
"""
   Tạo database ---
   Tạo file raiway_ai.db
   
"""
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "railway_ai.db")

db = DatabaseManager(db_path)
