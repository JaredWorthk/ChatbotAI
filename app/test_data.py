# test_data.py
import json

try:
    with open('data/railway_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"📊 Loaded: {data['metadata']['total_entries']} knowledge entries")
        print(f"🌍 Languages: {data['metadata']['languages']}")
        print(f"📋 Categories: {data['metadata']['categories']}")
        print("✅ JSON file loaded successfully!")
except FileNotFoundError:
    print("❌ File railway_data.json not found!")
except Exception as e:
    print(f"❌ Error: {e}")