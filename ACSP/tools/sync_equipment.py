import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from ACSP.database import get_connection

LEGACY_DB_PATH = r'\\172.16.3.237\Technical\주장비 PMS 관리 List\PMS_Manager_v2.0\pms.db'

def sync_equipment():
    print(f"Syncing equipment data from: {LEGACY_DB_PATH}")
    
    if not os.path.exists(LEGACY_DB_PATH):
        print("Error: Cannot access legacy DB file.")
        return
    
    try:
        # Connect to Source
        src_conn = sqlite3.connect(LEGACY_DB_PATH)
        src_cursor = src_conn.cursor()
        
        # Connect to Dest
        dest_conn = get_connection()
        dest_cursor = dest_conn.cursor()
        
        # Fetch all equipment from legacy
        src_cursor.execute("SELECT id, last_maintenance_date, next_maintenance_date FROM equipment")
        rows = src_cursor.fetchall()
        
        updated_count = 0
        
        for eq_id, last_date, next_date in rows:
            dest_cursor.execute('''
                UPDATE equipment 
                SET last_maintenance_date = ?, 
                    next_maintenance_date = ?
                WHERE id = ?
            ''', (last_date, next_date, eq_id))
            
            if dest_cursor.rowcount > 0:
                updated_count += 1
        
        dest_conn.commit()
        
        print("-" * 30)
        print(f"Sync Complete.")
        print(f"Updated: {updated_count} equipment records")
        print("-" * 30)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'src_conn' in locals():
            src_conn.close()
        if 'dest_conn' in locals():
            dest_conn.close()

if __name__ == "__main__":
    sync_equipment()
