import sqlite3
import os
import sys
from datetime import datetime

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ACSP.database import get_connection, calculate_equipment_status

# Legacy Path
# Note: Using raw string for Windows path
LEGACY_DB_PATH = r'\\172.16.3.237\Technical\주장비 PMS 관리 List\PMS_Manager_v2.0\pms.db'

def import_data():
    print(f"Checking access to: {LEGACY_DB_PATH}")
    if not os.path.exists(LEGACY_DB_PATH):
        print("Error: Cannot find legacy DB file. Check network connection or path.")
        return

    print("Connecting to legacy DB...")
    imported_count = 0
    skipped_count = 0
    
    try:
        # Connect to Source
        src_conn = sqlite3.connect(LEGACY_DB_PATH)
        src_cursor = src_conn.cursor()
        
        # Connect to Dest
        dest_conn = get_connection()
        dest_cursor = dest_conn.cursor()
        
        # 1. Fetch History
        print("Fetching maintenance history...")
        try:
            src_cursor.execute("SELECT equipment_id, maintenance_date FROM maintenance_history")
            rows = src_cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(f"Error reading source table: {e}")
            return
            
        print(f"Found {len(rows)} records. Importing...")
        
        affected_ids = set()
        
        for eq_id, date_str in rows:
            # Check if exists
            dest_cursor.execute(
                "SELECT id FROM maintenance_history WHERE equipment_id = ? AND maintenance_date = ?",
                (eq_id, date_str)
            )
            if dest_cursor.fetchone():
                skipped_count += 1
                continue
            
            # Insert
            dest_cursor.execute(
                "INSERT INTO maintenance_history (equipment_id, maintenance_date) VALUES (?, ?)",
                (eq_id, date_str)
            )
            imported_count += 1
            affected_ids.add(eq_id)
            
        dest_conn.commit()
        
        # 2. Recalculate Status
        print("Recalculating equipment status...")
        for eq_id in affected_ids:
            calculate_equipment_status(dest_conn, eq_id)
            
        dest_conn.commit()
        
        print("-" * 30)
        print(f"Import Complete.")
        print(f"Imported: {imported_count}")
        print(f"Skipped (Duplicate): {skipped_count}")
        print("-" * 30)
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'src_conn' in locals():
            src_conn.close()
        if 'dest_conn' in locals():
            dest_conn.close()

if __name__ == "__main__":
    import_data()
