"""Persistent work campaigns and per-equipment completion / target selection."""
from contextlib import closing
from datetime import date, datetime
import json
from pathlib import Path
import sqlite3

from .database import get_connection, get_db_path
from .pms import validate_date


def backup_before_upgrade():
    path = Path(get_db_path())
    if not path.exists():
        return
    with closing(get_connection()) as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'qc_pms_history' not in names or 'work_campaigns' in names:
            return
        folder = path.parent / 'backups'
        folder.mkdir(exist_ok=True)
        backup = folder / f'{path.stem}_before_work_v4_{datetime.now():%Y%m%d_%H%M%S_%f}.db'
        with closing(sqlite3.connect(str(backup))) as target:
            conn.backup(target)


def init_work_tracking():
    with get_connection() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS work_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                round_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, round_name)
            );
            CREATE TABLE IF NOT EXISTS work_equipment (
                campaign_id INTEGER NOT NULL REFERENCES work_campaigns(id),
                equipment_id INTEGER NOT NULL REFERENCES equipment(id),
                excluded INTEGER NOT NULL DEFAULT 0 CHECK(excluded IN (0,1)),
                completion_date TEXT,
                workers TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(campaign_id,equipment_id)
            );
            CREATE TABLE IF NOT EXISTS work_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL REFERENCES work_campaigns(id),
                equipment_id INTEGER NOT NULL REFERENCES equipment(id),
                action TEXT NOT NULL,
                before_json TEXT NOT NULL,
                after_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_work_changes
                ON work_changes(campaign_id,equipment_id,id);
        ''')


def clean_text(value, label, maximum, required=False):
    if not isinstance(value, str):
        raise ValueError(f'{label}을(를) 문자로 입력하세요.')
    value = value.strip()
    if len(value) > maximum or (required and not value):
        raise ValueError(f'{label}은(는) {"1~" if required else ""}{maximum}자 이내로 입력하세요.')
    return value


def create_campaign(name, round_name=''):
    name = clean_text(name, '작업명', 120, required=True)
    round_name = clean_text(round_name, '작업 차수 / 기간', 80)
    try:
        with get_connection() as conn:
            cursor = conn.execute('INSERT INTO work_campaigns(name,round_name) VALUES (?,?)', (name, round_name))
            campaign_id = cursor.lastrowid
            conn.execute('''INSERT INTO work_equipment(campaign_id,equipment_id)
                SELECT ?, id FROM equipment WHERE type IN ('QC','ARMGC')''', (campaign_id,))
            return campaign_id
    except sqlite3.IntegrityError:
        raise ValueError('같은 작업명과 차수가 이미 있습니다. 기존 작업을 선택하거나 차수를 변경하세요.') from None


def list_campaigns():
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute('SELECT * FROM work_campaigns ORDER BY id DESC')]


def summary(rows):
    included = [r for r in rows if not r['excluded']]
    done = sum(bool(r['completion_date']) for r in included)
    target = len(included)
    return dict(total=len(rows), target=target, completed=done,
                pending=target-done, excluded=len(rows)-target,
                percent=round(done / target * 100, 1) if target else None)


def dashboard(campaign_id):
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        campaign = conn.execute('SELECT * FROM work_campaigns WHERE id=?', (campaign_id,)).fetchone()
        if not campaign:
            raise ValueError('작업을 먼저 등록하거나 선택하세요.')
        rows = [dict(r) for r in conn.execute('''SELECT w.*, e.type AS equipment_type
            FROM work_equipment w JOIN equipment e ON e.id=w.equipment_id
            WHERE w.campaign_id=? ORDER BY e.id''', (campaign_id,))]
    for row in rows:
        row['status'] = '제외' if row['excluded'] else '완료' if row['completion_date'] else '미완료'
    fleets = {kind: summary([r for r in rows if r['equipment_type'] == kind]) for kind in ('QC','ARMGC')}
    return dict(campaign=dict(campaign), equipment=rows, summary=summary(rows), fleets=fleets)


def update_equipment(campaign_id, equipment_id, version, action, completion_date=None, workers='', notes=''):
    """Compare-and-swap avoids stale clicks and edits overwriting another window."""
    if action not in ('complete', 'clear', 'exclude', 'include'):
        raise ValueError('지원하지 않는 작업입니다.')
    if action == 'complete':
        if validate_date(completion_date) > date.today():
            raise ValueError('완료일에는 미래 날짜를 입력할 수 없습니다.')
        workers = clean_text(workers, '작업자', 200, required=True)
        notes = clean_text(notes, '비고', 2000)
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('''SELECT * FROM work_equipment
            WHERE campaign_id=? AND equipment_id=?''', (campaign_id,equipment_id)).fetchone()
        if not row or row['version'] != version:
            raise ValueError('다른 창에서 변경된 실적입니다. 새로고침 후 다시 선택하세요.')
        before = dict(row)
        if action in ('complete', 'clear') and row['excluded']:
            raise ValueError('제외된 호기는 대상에 포함한 후 실적을 입력하세요.')
        if action in ('exclude', 'include'):
            # Preserve completion details; including again restores the prior completion state.
            conn.execute('''UPDATE work_equipment SET excluded=?, version=version+1,
                updated_at=CURRENT_TIMESTAMP WHERE campaign_id=? AND equipment_id=?''',
                         (int(action == 'exclude'),campaign_id,equipment_id))
        else:
            conn.execute('''UPDATE work_equipment SET completion_date=?, workers=?, notes=?,
                version=version+1, updated_at=CURRENT_TIMESTAMP
                WHERE campaign_id=? AND equipment_id=?''',
                         (completion_date if action == 'complete' else None,
                          workers if action == 'complete' else '', notes if action == 'complete' else '',
                          campaign_id,equipment_id))
        after = dict(conn.execute('SELECT * FROM work_equipment WHERE campaign_id=? AND equipment_id=?',
                                  (campaign_id,equipment_id)).fetchone())
        conn.execute('''INSERT INTO work_changes(campaign_id,equipment_id,action,before_json,after_json)
            VALUES (?,?,?,?,?)''', (campaign_id,equipment_id,action,
                                   json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False)))
    return after


def changes(campaign_id, equipment_id=None):
    query = 'SELECT * FROM work_changes WHERE campaign_id=?'
    values = [campaign_id]
    if equipment_id is not None:
        query += ' AND equipment_id=?'
        values.append(equipment_id)
    with closing(get_connection()) as conn:
        conn.row_factory = sqlite3.Row
        result = [dict(r) for r in conn.execute(query+' ORDER BY id DESC',values)]
    for row in result:
        row['before'] = json.loads(row.pop('before_json'))
        row['after'] = json.loads(row.pop('after_json'))
    return result
