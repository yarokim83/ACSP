import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from ACSP import database, pms


class LegacyQCStatusTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, ACSP_DB_PATH=str(Path(self.temp.name) / 'legacy.db'))
        env.start()
        self.addCleanup(env.stop)
        database.init_database()
        with database.get_connection() as conn:
            conn.execute("UPDATE equipment SET last_maintenance_date=NULL WHERE type='QC'")

    def legacy(self, equipment_id, value):
        with database.get_connection() as conn:
            conn.execute('INSERT INTO maintenance_history(equipment_id, maintenance_date) VALUES (?,?)',
                         (equipment_id, value))

    def test_legacy_history_restores_overdue_without_creating_tasks(self):
        self.legacy(101, (date.today()-timedelta(days=46)).isoformat())
        self.legacy(102, (date.today()-timedelta(days=45)).isoformat())
        stats = database.get_daily_report_stats()
        self.assertEqual(stats['qc_overdue'], 1)
        self.assertEqual(stats['qc_legacy'], 0)
        self.assertEqual(stats['qc_unknown_tasks'], 10)
        self.assertEqual(stats['qc_data'][0]['days_passed'], 46)
        self.assertEqual(stats['qc_data'][0]['source'], 'unit')
        self.assertEqual([r['status'] for r in pms.task_status()[:2]], ['지연', '임박'])
        with database.get_connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM qc_pms_history').fetchone()[0], 0)

    def test_partial_task_archive_never_resets_unit_pms(self):
        self.legacy(101, (date.today()-timedelta(days=80)).isoformat())
        with database.get_connection() as conn:
            conn.execute("INSERT INTO qc_pms_history(equipment_id,task,maintenance_date,workers) VALUES (101,'Front',?,'Test')", (date.today().isoformat(),))
        row = pms.unit_status()[0]
        self.assertEqual(row['source'], 'unit')
        self.assertEqual(row['days_passed'], 80)
        self.assertTrue(row['is_overdue'])
        self.assertEqual(row['unknown'], 0)
        self.assertEqual(pms.unit_status((date.today()-timedelta(days=1)).isoformat())[0]['source'], 'unit')

    def test_historical_snapshot_ignores_future_records_and_current_equipment_date(self):
        self.legacy(101, '2025-01-01')
        self.legacy(101, '2025-03-01')
        with database.get_connection() as conn:
            conn.execute("UPDATE equipment SET last_maintenance_date='2025-04-01' WHERE id=101")
        row = pms.unit_status('2025-02-28')[0]
        self.assertEqual(row['days_passed'], 58)
        self.assertTrue(row['is_overdue'])
        self.assertEqual(pms.unit_status('2024-12-31')[0]['source'], 'unknown')

    def test_equipment_only_date_and_invalid_dates(self):
        with database.get_connection() as conn:
            conn.execute('UPDATE equipment SET last_maintenance_date=? WHERE id=101',
                         ((date.today()-timedelta(days=60)).isoformat(),))
            conn.execute("UPDATE equipment SET last_maintenance_date='invalid' WHERE id=102")
        self.legacy(102, '2025-02-30')
        rows = pms.unit_status()
        self.assertTrue(rows[0]['is_overdue'])
        self.assertEqual(rows[0]['source'], 'unit')
        self.assertEqual(rows[1]['source'], 'unknown')


if __name__ == '__main__':
    unittest.main()
