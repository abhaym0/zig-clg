#!/usr/bin/env python3
"""
Database migration script to add private messaging columns
"""

import sqlite3

def migrate_database():
    """Add new columns for private messaging to existing database"""
    conn = sqlite3.connect("zig_clg.db")
    cursor = conn.cursor()
    
    try:
        # Add recipient column
        cursor.execute("ALTER TABLE messages ADD COLUMN recipient TEXT")
        print("✅ Added 'recipient' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️  'recipient' column already exists")
        else:
            print(f"❌ Error adding 'recipient' column: {e}")
    
    try:
        # Add is_private column
        cursor.execute("ALTER TABLE messages ADD COLUMN is_private BOOLEAN DEFAULT 0")
        print("✅ Added 'is_private' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️  'is_private' column already exists")
        else:
            print(f"❌ Error adding 'is_private' column: {e}")
    
    conn.commit()
    conn.close()
    print("🎉 Database migration completed!")

if __name__ == "__main__":
    migrate_database()
