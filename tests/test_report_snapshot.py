import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ACSP import database, pms


class ReportSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, ACSP_DB_PATH=str(Path(self.temp.name) / 'report.db'))
        env.start()
        self.addCleanup(env.stop)
        database.init_database()

    def test_one_connection_three_reads_and_no_stale_cache(self):
        original = database.get_connection
        statements = []
        def connect():
            conn = original()
            conn.set_trace_callback(statements.append)
            return conn
        with patch.object(database, 'get_connection', side_effect=connect) as connections, \
             patch.object(pms, 'get_connection', side_effect=AssertionError('Unexpected extra PMS connection')):
            stats = database.get_daily_report_stats()
        self.assertEqual(connections.call_count, 1)
        self.assertEqual(sum(sql.lstrip().upper().startswith('SELECT') for sql in statements), 3)
        self.assertEqual(statements[0], 'BEGIN')
        self.assertEqual(statements[-1], 'COMMIT')
        self.assertEqual(stats['qc_overdue'], 0)
        with original() as conn:
            conn.execute('UPDATE equipment SET last_maintenance_date=? WHERE id=101',
                         ((date.today()-timedelta(days=60)).isoformat(),))
        self.assertEqual(database.get_daily_report_stats()['qc_overdue'], 1)

    def test_current_and_month_end_qc_match_standalone_rules(self):
        with database.get_connection() as conn:
            for eq, days in [(101, 95), (102, 80), (103, 45)]:
                value = (date.today()-timedelta(days=days)).isoformat()
                conn.execute('UPDATE equipment SET last_maintenance_date=? WHERE id=?', (value, eq))
                conn.execute('INSERT INTO maintenance_history(equipment_id, maintenance_date) VALUES (?,?)', (eq, value))
        pms.save_record(101, 'PMS', date.today().isoformat(), 'Test')
        pms.save_record(101, 'PMS', (date.today()-timedelta(days=46)).isoformat(), 'Test')
        stats = database.get_daily_report_stats()
        self.assertEqual(stats['qc_data'], pms.unit_status())
        self.assertEqual(stats['qc_overdue'], 1)
        self.assertEqual(stats['calendar_assignments'][date.today().day]['QC'], ['101'])
        for month, rate in stats['history_qc'].items():
            if month == date.today().month:
                self.assertEqual(rate, round(stats['qc_rate']))
            else:
                import calendar
                as_of = date(date.today().year, month, calendar.monthrange(date.today().year, month)[1])
                self.assertEqual(rate, round(sum(r['is_overdue'] for r in pms.unit_status(as_of.isoformat())) / 12 * 100))

    def test_armgc_history_and_calendar_duplicate_dates(self):
        with database.get_connection() as conn:
            conn.execute("INSERT INTO maintenance_history(equipment_id,maintenance_date) VALUES (211,'2026-01-01')")
            for _ in range(2):
                conn.execute("INSERT INTO maintenance_history(equipment_id,maintenance_date) VALUES (211,'2026-10-10')")
            conn.execute("UPDATE equipment SET last_maintenance_date='2026-10-10' WHERE id=211")
        class October(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 20)
        with patch.object(database, 'datetime', October):
            stats = database.get_daily_report_stats()
        self.assertEqual(stats['calendar_assignments'][10]['ARMGC'], ['211'])
        self.assertEqual(stats['armgc_pms_count'], 1)
        self.assertEqual(stats['history_armgc'][1], 0)
        self.assertEqual(stats['history_armgc'][2], round(100/38))


if __name__ == '__main__':
    unittest.main()
