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
                next_maintenance_date TEXT,
                type TEXT DEFAULT 'ARMGC'
            )
        ''')
        
        # Check if 'type' column exists (for migration)
        cursor.execute("PRAGMA table_info(equipment)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'type' not in columns:
            cursor.execute("ALTER TABLE equipment ADD COLUMN type TEXT DEFAULT 'ARMGC'")
        
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
        
        # Check if rm_list table exists before creating it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rm_list'")
        rm_table_exists = cursor.fetchone() is not None
        
        # Create rm_list table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rm_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                failure_date TEXT,
                failure_details TEXT,
                rm_request_date TEXT,
                remark TEXT
            )
        ''')
        
        # Create email_recipients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT NOT NULL,
                type TEXT DEFAULT 'TO'
            )
        ''')
        
        # Populate initial RM list only when the table is first created
        if not rm_table_exists:
            cursor.execute('''
                INSERT INTO rm_list (failure_date, failure_details, rm_request_date, remark)
                VALUES ('2026-06-16', 'QC 104호 Hoist Wire Rope 단선기준 초과', '2026-06-17', 'Wire Rope 단선으로 인한 낙하사고 위험')
            ''')
            cursor.execute('''
                INSERT INTO rm_list (failure_date, failure_details, rm_request_date, remark)
                VALUES ('2026-06-16', 'ARMGC 256호 Trolley Wheel 진동 소음발생', '2026-06-17', 'Trolley Wheel 이탈로 인한 낙하사고 위험')
            ''')
        
        # Populate initial equipment list if missing
        _populate_initial_equipment(cursor)
        
        conn.commit()

def _populate_initial_equipment(cursor):
    # ARMGC: 211-272
    armgc_list = []
    # 211-216, 221-226, 231-236, 241-246, 251-256, 261-266
    for start in [211, 221, 231, 241, 251, 261]:
        armgc_list.extend(range(start, start + 6))
    # 271-272
    armgc_list.extend(range(271, 273))
    
    # QC: 101-112
    qc_list = list(range(101, 113))
    
    today = datetime.now().strftime('%Y-%m-%d')
    next_due = (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d')
    
    # Check existing
    cursor.execute('SELECT id, type FROM equipment')
    existing_data = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Insert/Update ARMGC
    for eq_id in armgc_list:
        if eq_id not in existing_data:
            cursor.execute('''
                INSERT INTO equipment (id, last_maintenance_date, next_maintenance_date, type)
                VALUES (?, ?, ?, 'ARMGC')
            ''', (eq_id, today, next_due))
        elif existing_data[eq_id] != 'ARMGC':
             cursor.execute("UPDATE equipment SET type = 'ARMGC' WHERE id = ?", (eq_id,))

    # Insert/Update QC
    for eq_id in qc_list:
        if eq_id not in existing_data:
            cursor.execute('''
                INSERT INTO equipment (id, last_maintenance_date, next_maintenance_date, type)
                VALUES (?, ?, ?, 'QC')
            ''', (eq_id, today, next_due))
        elif existing_data[eq_id] != 'QC':
             cursor.execute("UPDATE equipment SET type = 'QC' WHERE id = ?", (eq_id,))

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

# -------------------------------------------------------------------------
# Email Recipients Management
# -------------------------------------------------------------------------
def get_email_recipients():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, email, type FROM email_recipients ORDER BY id ASC')
        rows = cursor.fetchall()
    
    recipients = {'TO': [], 'CC': []}
    for row in rows:
        r_id, r_name, r_email, r_type = row
        t_key = 'CC' if r_type.upper() == 'CC' else 'TO'
        recipients[t_key].append({'id': r_id, 'name': r_name, 'email': r_email, 'type': t_key})
    return recipients

def add_email_recipient(name, email, type_val='TO'):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO email_recipients (name, email, type)
            VALUES (?, ?, ?)
        ''', (name.strip(), email.strip(), type_val.upper()))
        conn.commit()

def delete_email_recipient(recipient_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM email_recipients WHERE id = ?', (recipient_id,))
        conn.commit()

# -------------------------------------------------------------------------
# Report Stats Collector
# -------------------------------------------------------------------------
def get_daily_report_stats():
    today = datetime.now()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch RM items
        cursor.execute('SELECT failure_date, failure_details, rm_request_date, remark FROM rm_list ORDER BY rm_request_date DESC')
        rm_rows = cursor.fetchall()
        rm_list = []
        for r in rm_rows:
            f_date, details, req_date, remark = r
            try:
                elapsed = (today - datetime.strptime(req_date, '%Y-%m-%d')).days
                elapsed_str = f"+{elapsed}" if elapsed >= 0 else str(elapsed)
            except Exception:
                elapsed_str = "-"
            rm_list.append({
                'failure_date': f_date,
                'details': details,
                'rm_request_date': req_date,
                'elapsed_days': elapsed_str,
                'remark': remark
            })
            
        # 2. Fetch equipment for QC and ARMGC overdue calculation
        cursor.execute('SELECT id, last_maintenance_date, type FROM equipment ORDER BY id')
        eq_rows = cursor.fetchall()
        
        qc_data = []
        armgc_data = []
        
        for r in eq_rows:
            eq_id, last_date_str, eq_type = r[0], r[1], r[2] if len(r) > 2 else 'ARMGC'
            try:
                days_passed = (today - datetime.strptime(last_date_str, '%Y-%m-%d')).days
            except Exception:
                days_passed = 0
                
            item = {'id': eq_id, 'days_passed': days_passed, 'is_overdue': days_passed > 45}
            if eq_type == 'QC':
                qc_data.append(item)
            else:
                armgc_data.append(item)
                
        # 3. Monthly PMS assignments for current month
        month_prefix = today.strftime('%Y-%m')
        cursor.execute('SELECT equipment_id, maintenance_date FROM maintenance_history WHERE maintenance_date LIKE ?', (f"{month_prefix}%",))
        history_rows = cursor.fetchall()
        
        calendar_assignments = {} # day_num -> list of crane_ids
        for h in history_rows:
            eq_id, m_date = h
            try:
                day_num = int(m_date.split('-')[2])
                if day_num not in calendar_assignments:
                    calendar_assignments[day_num] = []
                calendar_assignments[day_num].append(str(eq_id))
            except Exception:
                pass

    qc_total = len(qc_data)
    qc_overdue = len([d for d in qc_data if d['is_overdue']])
    qc_rate = (qc_overdue / qc_total * 100) if qc_total > 0 else 0
    
    armgc_total = len(armgc_data)
    armgc_overdue = len([d for d in armgc_data if d['is_overdue']])
    armgc_rate = (armgc_overdue / armgc_total * 100) if armgc_total > 0 else 0

    return {
        'today_str': today.strftime('%Y-%m-%d'),
        'today_korean': today.strftime('%Y년 %m월 %d일'),
        'year': today.year,
        'month': today.month,
        'rm_list': rm_list,
        'qc_data': qc_data,
        'qc_total': qc_total,
        'qc_overdue': qc_overdue,
        'qc_rate': qc_rate,
        'armgc_data': armgc_data,
        'armgc_total': armgc_total,
        'armgc_overdue': armgc_overdue,
        'armgc_rate': armgc_rate,
        'calendar_assignments': calendar_assignments
    }
