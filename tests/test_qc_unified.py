"""Upgrade and end-to-end consistency checks for the unified QC rollback."""
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from ACSP import database, pms, work_tracking


class UnifiedQCTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, ACSP_DB_PATH=str(Path(self.temp.name) / 'old.db'))
        env.start()
        self.addCleanup(env.stop)
        database.init_database()
        self.today = date.today().isoformat()

    def test_upgrade_preserves_original_history_archive_and_work_dashboard(self):
        campaign = work_tracking.create_campaign('Preserved work')
        before_work = work_tracking.dashboard(campaign)
        old_date = (date.today()-timedelta(days=60)).isoformat()
        with database.get_connection() as conn:
            # Exact pre-v5 history layout, including a pre-existing record ID.
            conn.execute('DROP TABLE maintenance_history')
            conn.execute('''CREATE TABLE maintenance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, equipment_id INTEGER,
                maintenance_date TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(equipment_id) REFERENCES equipment(id))''')
            conn.execute('INSERT INTO maintenance_history(id,equipment_id,maintenance_date) VALUES (42,101,?)', (old_date,))
            conn.execute('UPDATE equipment SET last_maintenance_date=? WHERE id=101', (old_date,))
            for task in ('Front', 'Back', 'Gantry', 'H.B'):
                conn.execute('''INSERT INTO qc_pms_history(equipment_id,task,maintenance_date,workers,notes)
                    VALUES (101,?,?,'Archive worker','Keep me')''', (task, self.today))
            original_archive = conn.execute('SELECT * FROM qc_pms_history').fetchall()
        database.init_database()
        database.init_database()
        backups = list((Path(self.temp.name)/'backups').glob('*before_unified_pms_v5*.db'))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(str(backups[0]))) as backup:
            self.assertNotIn('workers', [r[1] for r in backup.execute('PRAGMA table_info(maintenance_history)')])
            self.assertEqual(backup.execute('SELECT * FROM qc_pms_history').fetchall(), original_archive)
        with database.get_connection() as conn:
            self.assertEqual(conn.execute('SELECT * FROM qc_pms_history').fetchall(), original_archive)
        records = pms.list_records()
        self.assertEqual([(r['id'], r['task'], r['maintenance_date']) for r in records], [(42, 'PMS', old_date)])
        self.assertEqual(len(pms.task_status()), 12)
        self.assertEqual(pms.task_status()[0]['days_passed'], 60)
        self.assertEqual(len(pms.list_records(task='분류별 보관 이력')), 4)
        self.assertTrue(all(r['legacy'] for r in pms.list_records(task='분류별 보관 이력')))
        self.assertEqual(work_tracking.dashboard(campaign), before_work)
        self.assertEqual(database.get_daily_report_stats()['qc_overdue'], 1)
        self.assertEqual(pms.calendar_rows(self.today, self.today), [])
        pms.save_record(101, maintenance_date=old_date, workers='Added worker', record_id=42, version=1)
        self.assertEqual(pms.list_records()[0]['workers'], 'Added worker')

    def test_unit_edit_move_and_final_delete_recalculate_all_surfaces(self):
        older = (date.today()-timedelta(days=46)).isoformat()
        pms.save_record(101, maintenance_date=older, workers='A')
        recent = pms.save_record(101, maintenance_date=self.today, workers='B')
        self.assertEqual(database.get_daily_report_stats()['qc_overdue'], 0)
        pms.save_record(102, maintenance_date=self.today, workers='C', record_id=recent, version=1)
        self.assertEqual(pms.task_status()[0]['status'], '지연')
        self.assertEqual(database.get_daily_report_stats()['qc_overdue'], 1)
        pms.delete_record(recent, 2)
        self.assertEqual(pms.task_status()[1]['status'], '미등록')
        self.assertEqual(database.get_daily_report_stats()['qc_unknown'], 1)
        self.assertNotIn('102', [str(r[1]) for r in pms.calendar_rows()])

    def test_old_four_task_clients_are_rejected_without_writes(self):
        for task in ('Front', 'Back', 'Gantry', 'H.B'):
            with self.assertRaisesRegex(ValueError, '통합 PMS'):
                pms.save_record(101, task, self.today, 'Old browser')
        self.assertEqual(pms.list_records(), [])
        self.assertEqual(pms.list_records(task='분류별 보관 이력'), [])

    def test_date_only_entry_and_edit_preserve_existing_metadata(self):
        record_id = pms.save_record(101, maintenance_date=self.today)
        row = pms.list_records()[0]
        self.assertEqual((row['workers'], row['notes']), ('', ''))
        with database.get_connection() as conn:
            conn.execute('UPDATE maintenance_history SET workers=?,notes=? WHERE id=?',
                         ('기존 작업자', '기존 비고', record_id))
        yesterday = (date.today()-timedelta(days=1)).isoformat()
        pms.save_record(101, maintenance_date=yesterday, record_id=record_id, version=1)
        row = pms.list_records()[0]
        self.assertEqual((row['maintenance_date'], row['workers'], row['notes'], row['version']),
                         (yesterday, '기존 작업자', '기존 비고', 2))


if __name__ == '__main__':
    unittest.main()
