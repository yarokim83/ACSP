import sqlite3
import os

LEGACY_DB_PATH = r'\\172.16.3.237\Technical\주장비 PMS 관리 List\PMS_Manager_v2.0\pms.db'

def inspect_db():
    if not os.path.exists(LEGACY_DB_PATH):
        print(f"File not found: {LEGACY_DB_PATH}")
        return

    try:
        conn = sqlite3.connect(LEGACY_DB_PATH)
        cursor = conn.cursor()
        
        # 1. List Tables
        print("=== Tables ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for t in tables:
            print(f"- {t[0]}")
            
        # 2. Inspect 'maintenance_history' schema
        target_table = 'maintenance_history'
        if (target_table,) in tables:
            print(f"\n=== Schema: {target_table} ===")
            cursor.execute(f"PRAGMA table_info({target_table})")
            columns = cursor.fetchall()
            for col in columns:
                print(col) # (cid, name, type, notnull, dflt_value, pk)
                
            # 3. Sample Data
            print(f"\n=== Sample Data: {target_table} (First 5) ===")
            cursor.execute(f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
        else:
            print(f"\nTable '{target_table}' not found!")
            
        # 4. Inspect 'equipment' schema as well just in case
        target_table = 'equipment'
        if (target_table,) in tables:
            print(f"\n=== Schema: {target_table} ===")
            cursor.execute(f"PRAGMA table_info({target_table})")
            columns = cursor.fetchall()
            for col in columns:
                print(col)
            
            print(f"\n=== Sample Data: {target_table} (First 5) ===")
            cursor.execute(f"SELECT * FROM {target_table} LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                print(row)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    inspect_db()
