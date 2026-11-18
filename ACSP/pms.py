"""One 45-day QC PMS per unit; former task records are a read-only archive."""
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path
import sqlite3

from .database import get_connection, get_db_path, calculate_equipment_status

TASKS = ('PMS',)
CYCLE_DAYS = 45


def backup_before_upgrade():
    path = Path(get_db_path())
    if not path.exists():
        return
    with closing(get_connection()) as source:
        tables = {r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'equipment' not in tables:
            return
        columns = {r[1] for r in source.execute('PRAGMA table_info(maintenance_history)')}
        if {'workers', 'notes', 'version'} <= columns and 'qc_pms_history' in tables:
            return
        folder = path.parent / 'backups'
        folder.mkdir(exist_ok=True)
        target = folder / f'{path.stem}_before_unified_pms_v5_{datetime.now():%Y%m%d_%H%M%S_%f}.db'
        with closing(sqlite3.connect(str(target))) as destination:
            source.backup(destination)


def init_pms():
    with closing(get_connection()) as conn, conn:
        # Serialize upgrades from multiple NAS clients; preserve all old IDs/data.
        conn.execute('BEGIN IMMEDIATE')
        columns = {r[1] for r in conn.execute('PRAGMA table_info(maintenance_history)')}
        for name, definition in [('workers', "TEXT NOT NULL DEFAULT ''"),
                                 ('notes', "TEXT NOT NULL DEFAULT ''"),
                                 ('version', 'INTEGER NOT NULL DEFAULT 1')]:
            if name not in columns:
                conn.execute(f'ALTER TABLE maintenance_history ADD COLUMN {name} {definition}')
        conn.execute('''CREATE TABLE IF NOT EXISTS qc_pms_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL REFERENCES equipment(id),
            task TEXT NOT NULL CHECK(task IN ('Front','Back','Gantry','H.B')),
            maintenance_date TEXT NOT NULL, workers TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(equipment_id, task, maintenance_date))''')


def validate_date(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
        return parsed
    except (TypeError, ValueError):
        raise ValueError('날짜는 YYYY-MM-DD 형식의 실제 날짜로 입력하세요.') from None


def equipment_ids():
    with closing(get_connection()) as conn:
        return [r[0] for r in conn.execute("SELECT id FROM equipment WHERE type='QC' ORDER BY id")]


def save_record(equipment_id, task='PMS', maintenance_date=None, workers=None, notes=None, record_id=None, version=None):
    if isinstance(equipment_id, bool) or not isinstance(equipment_id, (int, str)) or not str(equipment_id).isdigit():
        raise ValueError('등록된 QC 호기를 선택하세요.')
    equipment_id = int(equipment_id)
    if not 0 < equipment_id < 2147483647:
        raise ValueError('등록된 QC 호기를 선택하세요.')
    if task not in TASKS:
        raise ValueError('QC PMS는 호기별 통합 PMS로 변경되었습니다. 화면을 새로고침하세요.')
    if validate_date(maintenance_date) > date.today():
        raise ValueError('시행 실적에는 미래 날짜를 입력할 수 없습니다.')
    if workers is not None and (not isinstance(workers, str) or len(workers) > 200):
        raise ValueError('작업자 정보는 200자 이내의 문자열이어야 합니다.')
    if notes is not None and (not isinstance(notes, str) or len(notes) > 2000):
        raise ValueError('비고는 2,000자 이내로 입력하세요.')
    with closing(get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT type FROM equipment WHERE id=?', (equipment_id,)).fetchone()
        if not row or row[0] != 'QC':
            raise ValueError('등록된 QC 호기를 선택하세요.')
        old_equipment = equipment_id
        if record_id is not None:
            old = conn.execute('''SELECT h.equipment_id FROM maintenance_history h
                JOIN equipment e ON e.id=h.equipment_id
                WHERE h.id=? AND h.version=? AND e.type='QC' ''', (record_id, version)).fetchone()
            if not old:
                raise ValueError('다른 PC에서 변경했거나 삭제한 이력입니다. 새로고침 후 다시 수정하세요.')
            old_equipment = old[0]
        duplicate = conn.execute('''SELECT id FROM maintenance_history
            WHERE equipment_id=? AND maintenance_date=? AND id != ?''',
            (equipment_id, maintenance_date, record_id if record_id is not None else -1)).fetchone()
        if duplicate:
            raise ValueError('같은 호기·시행일의 PMS 실적이 이미 있습니다. 기존 이력을 확인하세요.')
        # New forms omit metadata. Keep existing metadata when correcting a date.
        values = (equipment_id, maintenance_date,
                  workers.strip() if workers is not None else None,
                  notes.strip() if notes is not None else None)
        if record_id is None:
            record_id = conn.execute('''INSERT INTO maintenance_history
                (equipment_id, maintenance_date, workers, notes)
                VALUES (?,?,COALESCE(?,''),COALESCE(?,''))''', values).lastrowid
        else:
            conn.execute('''UPDATE maintenance_history SET equipment_id=?, maintenance_date=?,
                workers=COALESCE(?,workers), notes=COALESCE(?,notes), version=version+1
                WHERE id=?''', values + (record_id,))
        for eq in {old_equipment, equipment_id}:
            calculate_equipment_status(conn, eq)
        return record_id


def delete_record(record_id, version):
    with closing(get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        old = conn.execute('''SELECT h.equipment_id FROM maintenance_history h
            JOIN equipment e ON e.id=h.equipment_id
            WHERE h.id=? AND h.version=? AND e.type='QC' ''', (record_id, version)).fetchone()
        if not old:
            raise ValueError('다른 PC에서 변경했거나 삭제한 이력입니다. 새로고침하세요.')
        conn.execute('DELETE FROM maintenance_history WHERE id=?', (record_id,))
        calculate_equipment_status(conn, old[0])


def list_records(equipment_id=None, task=None, start=None, end=None, include_legacy=True):
    """Unified records by default; the explicit archive filter is read-only."""
    for value in (start, end):
        if value:
            validate_date(value)
    if start and end and start > end:
        raise ValueError('조회 시작일은 종료일보다 늦을 수 없습니다.')
    if task not in (None, '', 'PMS', '분류별 보관 이력'):
        raise ValueError('올바른 조회 구분을 선택하세요.')
    if task == '분류별 보관 이력':
        query = '''SELECT h.*, 1 AS legacy FROM qc_pms_history h
                   JOIN equipment e ON e.id=h.equipment_id WHERE e.type='QC' '''
    else:
        query = '''SELECT h.id, h.equipment_id, 'PMS' AS task, h.maintenance_date,
                   h.workers, h.notes, h.version, h.created_at, h.created_at AS updated_at,
                   0 AS legacy FROM maintenance_history h
                   JOIN equipment e ON e.id=h.equipment_id WHERE e.type='QC' '''
    params = []
    for column, value, op in [('equipment_id', equipment_id, '='),
                              ('maintenance_date', start, '>='), ('maintenance_date', end, '<=')]:
        if value not in (None, ''):
            query += f' AND h.{column} {op} ?'
            params.append(value)
    query += ' ORDER BY h.maintenance_date DESC, h.equipment_id, h.id DESC'
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(query, params)]


def _statuses(equipment, history, today):
    latest = {}
    for eq, value, kind in equipment:
        if kind == 'QC':
            latest[eq] = None
            try:
                if validate_date(value) <= today:
                    latest[eq] = dict(maintenance_date=value, workers='')
            except ValueError:
                pass
    for row in history:
        eq, value = row['equipment_id'], row['maintenance_date']
        if eq not in latest:
            continue
        try:
            if validate_date(value) > today:
                continue
        except ValueError:
            continue
        if latest[eq] is None or value >= latest[eq]['maintenance_date']:
            latest[eq] = row
    result = []
    for eq, row in sorted(latest.items()):
        value = row['maintenance_date'] if row else None
        elapsed = (today - validate_date(value)).days if value else None
        remaining = CYCLE_DAYS - elapsed if elapsed is not None else None
        state = ('미등록' if remaining is None else '지연' if remaining < 0
                 else '임박' if remaining < 10 else '정상')
        result.append(dict(equipment_id=eq, task='PMS', maintenance_date=value,
                           workers=row.get('workers', '') if row else '',
                           next_date=(validate_date(value) + timedelta(days=CYCLE_DAYS)).isoformat() if value else None,
                           days_passed=elapsed, remaining=remaining, status=state))
    return result


def task_status(as_of=None):
    today = validate_date(as_of) if as_of else date.today()
    with closing(get_connection()) as conn:
        conn.execute('BEGIN')
        equipment = conn.execute("SELECT id, last_maintenance_date, type FROM equipment WHERE type='QC'").fetchall()
        conn.row_factory = sqlite3.Row
        history = [dict(r) for r in conn.execute('''SELECT h.equipment_id, h.maintenance_date, h.workers
            FROM maintenance_history h JOIN equipment e ON e.id=h.equipment_id
            WHERE e.type='QC' ORDER BY h.maintenance_date, h.id''')]
    return _statuses(equipment, history, today)


def _units(jobs):
    return [dict(id=j['equipment_id'], days_passed=j['days_passed'] or 0,
                 is_overdue=j['status'] == '지연', source='unit' if j['maintenance_date'] else 'unknown',
                 unknown=int(j['maintenance_date'] is None)) for j in jobs]


def unit_status(as_of=None):
    return _units(task_status(as_of))


def unit_status_from_rows(equipment, legacy_history, task_history, as_of):
    """Task archive rows intentionally do not count as full-unit completion."""
    history = [dict(equipment_id=eq, maintenance_date=value) for eq, value in legacy_history]
    return _units(_statuses(equipment, history, validate_date(as_of)))


def calendar_rows(start=None, end=None):
    return [(r['id'], r['equipment_id'], r['maintenance_date'], 'PMS', r['workers'], r['version'])
            for r in list_records(start=start, end=end)]
