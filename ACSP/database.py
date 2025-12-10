import sqlite3
from datetime import datetime, timedelta

DB_NAME = 'acsp.db'

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_database():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Create equipment table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY,
                last_maintenance_date TEXT,
                next_maintenance_date TEXT
            )
        ''')
        
        # Create maintenance history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER,
                maintenance_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipment_id) REFERENCES equipment (id)
            )
        ''')
        
        
        # Populate initial equipment list if missing
        _populate_initial_equipment(cursor)
        
        conn.commit()

def _populate_initial_equipment(cursor):
    equipment_list = []
    # 211-216, 221-226, 231-236, 241-246, 251-256, 261-266
    for start in [211, 221, 231, 241, 251, 261]:
        equipment_list.extend(range(start, start + 6))
    # 271-272
    equipment_list.extend(range(271, 273))
    
    # Check existing
    cursor.execute('SELECT id FROM equipment')
    existing_ids = {row[0] for row in cursor.fetchall()}
    
    today = datetime.now().strftime('%Y-%m-%d')
    next_due = (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d')
    
    for eq_id in equipment_list:
        if eq_id not in existing_ids:
            cursor.execute('''
                INSERT INTO equipment (id, last_maintenance_date, next_maintenance_date)
                VALUES (?, ?, ?)
            ''', (eq_id, today, next_due))

def calculate_equipment_status(conn, equipment_id):
    """
    Recalculates the last and next maintenance dates for an equipment 
    based on its most recent history entry.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT maintenance_date FROM maintenance_history 
        WHERE equipment_id = ? 
        ORDER BY maintenance_date DESC 
        LIMIT 1
    ''', (equipment_id,))
    row = cursor.fetchone()
    
    if row:
        last_date_str = row[0]
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
        next_date = last_date + timedelta(days=45)
        
        cursor.execute('''
            UPDATE equipment 
            SET last_maintenance_date = ?, 
                next_maintenance_date = ?
            WHERE id = ?
        ''', (last_date_str, next_date.strftime('%Y-%m-%d'), equipment_id))
    # If no history exists, we might normally clear it, but for this app 
    # we assume initial data is sufficient or manual intervention.

def add_maintenance_history(equipment_id, date_str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO maintenance_history (equipment_id, maintenance_date)
            VALUES (?, ?)
        ''', (equipment_id, date_str))
        calculate_equipment_status(conn, equipment_id)
        conn.commit()

def update_maintenance_history(old_id, new_id, date_str):
    with get_connection() as conn:
        cursor = conn.cursor()
        # Find the specific record (assuming simple one-per-day-per-unit constraint or just taking one)
        # To be safe, we use rowid or just update where matching.
        # But here we are editing "a" record on a specific date in the list.
        # Simple approach: Update where eq_id and date match.
        
        # 1. Update the record
        cursor.execute('''
            UPDATE maintenance_history 
            SET equipment_id = ? 
            WHERE equipment_id = ? AND maintenance_date = ?
        ''', (new_id, old_id, date_str))
        
        # 2. Recalculate for both old (it lost a record) and new (it gained one)
        calculate_equipment_status(conn, old_id)
        calculate_equipment_status(conn, new_id)
        conn.commit()

def delete_maintenance_history(equipment_id, date_str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM maintenance_history 
            WHERE equipment_id = ? AND maintenance_date = ?
        ''', (equipment_id, date_str))
        calculate_equipment_status(conn, equipment_id)
        conn.commit()
