import concurrent.futures
from contextlib import closing
from datetime import date, timedelta
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ACSP import database, pms
from ACSP.pms_server import PMSService


class PMSTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = os.environ.get('ACSP_DB_PATH')
        os.environ['ACSP_DB_PATH'] = str(Path(self.temp.name) / 'test.db')
        database.init_database()
        self.today = date.today().isoformat()
        with database.get_connection() as conn:
            conn.execute("UPDATE equipment SET last_maintenance_date=NULL WHERE type='QC'")

    def tearDown(self):
        if self.old_path is None:
            os.environ.pop('ACSP_DB_PATH', None)
        else:
            os.environ['ACSP_DB_PATH'] = self.old_path
        self.temp.cleanup()

    def add(self, task='PMS', day=None, equipment=101):
        return pms.save_record(equipment, task, day or self.today, '홍길동, 김철수', '점검 완료')

    def test_one_pms_per_unit_and_unknown(self):
        self.assertEqual(len(pms.task_status()), 12)
        self.add()
        jobs = [j for j in pms.task_status() if j['equipment_id'] == 101]
        self.assertEqual([j['status'] for j in jobs], ['정상'])
        self.assertEqual(pms.unit_status()[0]['unknown'], 0)

    def test_latest_actual_date_not_entry_order_and_recalculation(self):
        latest_id = self.add()
        self.add(day=(date.today() - timedelta(days=50)).isoformat())
        self.assertEqual(pms.task_status()[0]['maintenance_date'], self.today)
        pms.delete_record(latest_id, 1)
        self.assertEqual(pms.task_status()[0]['status'], '지연')

    def test_cycle_boundaries(self):
        for eq, age in zip(range(101, 105), [35, 36, 45, 46]):
            self.add(day=(date.today() - timedelta(days=age)).isoformat(), equipment=eq)
        jobs = pms.task_status()[:4]
        self.assertEqual([j['status'] for j in jobs], ['정상', '임박', '임박', '지연'])
        self.assertEqual([j['remaining'] for j in jobs], [10, 9, 0, -1])
        self.assertTrue(pms.unit_status()[3]['is_overdue'])
        self.assertEqual(pms.unit_status()[0]['unknown'], 0)

    def test_invalid_input(self):
        for task, day, worker, equipment in [('H/B', self.today, '김', 101), ('PMS', '2026-02-30', '김', 101),
                 ('PMS', (date.today()+timedelta(days=1)).isoformat(), '김', 101),
                 ('PMS', self.today, 123, 101), ('PMS', self.today, '김', 211),
                 ('PMS', self.today, '김', {}), ('PMS', '20260901', '김', 101)]:
            with self.subTest(task=task, day=day, equipment=equipment), self.assertRaises(ValueError):
                pms.save_record(equipment, task, day, worker)
        self.assertEqual(pms.list_records(), [])

    def test_concurrent_duplicate_only_one_commit(self):
        def write(_):
            try:
                self.add()
                return True
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(write, range(6)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(pms.list_records()), 1)

    def test_concurrent_distinct_units_all_saved(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda eq: self.add(equipment=eq), range(101, 105)))
        self.assertEqual(len(pms.list_records()), 4)

    def test_stale_edit_and_delete_do_not_overwrite(self):
        record_id = self.add()
        pms.save_record(102, 'PMS', self.today, '수정 작업자', record_id=record_id, version=1)
        with self.assertRaises(ValueError):
            pms.save_record(103, 'PMS', self.today, '다른 PC', record_id=record_id, version=1)
        with self.assertRaises(ValueError):
            pms.delete_record(record_id, 1)
        self.assertEqual(pms.list_records()[0]['equipment_id'], 102)
        self.assertIsNone(pms.task_status()[0]['maintenance_date'])

    def test_filters_and_inclusive_date_range(self):
        self.add()
        self.add(day=(date.today()-timedelta(days=1)).isoformat())
        self.add(equipment=102)
        self.assertEqual(len(pms.list_records(equipment_id=101, start=self.today, end=self.today)), 1)
        self.assertEqual(len(pms.list_records(task='PMS')), 3)
        with self.assertRaises(ValueError):
            pms.list_records(start='2026-09-10', end='2026-09-01')

    def test_legacy_not_fabricated_and_upgrade_idempotent(self):
        with closing(database.get_connection()) as conn, conn:
            conn.execute('DROP TABLE qc_pms_history')
            conn.execute('INSERT INTO maintenance_history(equipment_id,maintenance_date) VALUES (?,?)', (101, self.today))
        database.init_database()
        database.init_database()
        self.assertEqual(len(list((Path(self.temp.name)/'backups').glob('*.db'))), 1)
        history = pms.list_records()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['task'], 'PMS')
        self.assertEqual(pms.task_status()[0]['status'], '정상')

    def test_legacy_entry_cannot_bypass_qc_tasks(self):
        with self.assertRaises(ValueError):
            database.add_maintenance_history(101, self.today)
        database.add_maintenance_history(211, self.today)
        with self.assertRaises(ValueError):
            database.update_maintenance_history(211, 101, self.today)

    def test_reports_calendar_and_historical_asof(self):
        self.add(day=(date.today()-timedelta(days=50)).isoformat())
        self.add(equipment=102)
        stats = database.get_daily_report_stats()
        self.assertEqual(stats['qc_total'], 12)
        self.assertEqual(stats['qc_overdue'], 1)
        self.assertEqual(stats['qc_unknown'], 10)
        self.assertEqual(stats['calendar_assignments'][date.today().day]['QC'], ['102'])
        earlier = (date.today()-timedelta(days=1)).isoformat()
        self.assertEqual(pms.unit_status(earlier)[0]['unknown'], 0)

    def test_network_auth_validation_shared_storage_restart(self):
        service = PMSService()
        service.start(host='127.0.0.1', port=0)
        try:
            base = f'http://127.0.0.1:{service.port}'
            with urlopen(base) as response:
                self.assertIn('QC PMS', response.read().decode())
            with self.assertRaises(HTTPError) as cm:
                urlopen(base+'/api/history')
            self.assertEqual(cm.exception.code, 401)
            cm.exception.close()
            headers = {'Authorization': 'Bearer '+service.access_code, 'Content-Type': 'application/json'}
            values = dict(equipment_id=101, maintenance_date=self.today)
            request = Request(base+'/api/history', data=json.dumps(values).encode(), headers=headers)
            with urlopen(request) as response:
                self.assertEqual(response.status, 201)
            self.assertEqual(pms.list_records()[0]['workers'], '')
            self.assertEqual(pms.list_records()[0]['notes'], '')
            with urlopen(Request(base+'/api/status', headers=headers)) as response:
                self.assertEqual(json.load(response)['status'][0]['status'], '정상')
            with self.assertRaises(HTTPError) as cm:
                urlopen(request)
            self.assertEqual(cm.exception.code, 400)
            cm.exception.close()
            old_code = service.access_code
        finally:
            server_thread = service.thread
            service.stop()
        self.assertFalse(server_thread.is_alive())
        self.assertFalse(service.running)
        service.start(host='127.0.0.1', port=0)
        try:
            self.assertNotEqual(service.access_code, old_code)
        finally:
            service.stop()


if __name__ == '__main__':
    unittest.main()
