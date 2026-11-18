from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import os
from pathlib import Path
import tempfile
import unittest

from ACSP import database
from ACSP import work_tracking as work


class WorkTrackingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = os.environ.get('ACSP_DB_PATH')
        os.environ['ACSP_DB_PATH'] = str(Path(self.temp.name)/'test.db')
        database.init_database()
        self.task = work.create_campaign('비상정지 스위치 점검','2026년 10월')
        self.today = date.today().isoformat()

    def tearDown(self):
        if self.old_path is None:
            os.environ.pop('ACSP_DB_PATH',None)
        else:
            os.environ['ACSP_DB_PATH'] = self.old_path
        self.temp.cleanup()

    def update(self, unit, action, version=1, **kwargs):
        return work.update_equipment(self.task,unit,version,action,**kwargs)

    def complete(self, unit=101, version=1):
        return self.update(unit,'complete',version,completion_date=self.today,workers='김정비, 이정비',notes='이상 없음')

    def test_initial_fleet_exactly_50_units_no_example_completions(self):
        state = work.dashboard(self.task)
        self.assertEqual(state['fleets']['QC']['total'],12)
        self.assertEqual(state['fleets']['ARMGC']['total'],38)
        self.assertEqual(len({r['equipment_id'] for r in state['equipment']}),50)
        self.assertEqual(state['summary']['completed'],0)
        self.assertEqual(state['summary']['target'],50)
        self.assertEqual(work.changes(self.task),[])

    def test_work_and_round_isolation(self):
        other = work.create_campaign('작업등 교체')
        repeat = work.create_campaign('비상정지 스위치 점검','2026년 11월')
        self.complete()
        self.update(211,'exclude')
        for task in (other,repeat):
            state = work.dashboard(task)['summary']
            self.assertEqual((state['completed'],state['excluded']),(0,0))

    def test_excluding_incomplete_changes_denominator_only(self):
        self.complete()
        self.update(211,'exclude')
        stats = work.dashboard(self.task)['summary']
        self.assertEqual(stats,dict(total=50,target=49,completed=1,pending=48,excluded=1,percent=2.0))

    def test_excluding_completed_preserves_details_and_include_restores(self):
        self.complete()
        self.update(101,'exclude',2)
        state = work.dashboard(self.task)
        self.assertEqual(state['summary']['completed'],0)
        row = state['equipment'][0]
        self.assertEqual(row['status'],'제외')
        self.assertEqual(row['completion_date'],self.today)
        self.assertEqual(row['workers'],'김정비, 이정비')
        self.update(101,'include',3)
        self.assertEqual(work.dashboard(self.task)['summary']['completed'],1)
        self.assertEqual(work.dashboard(self.task)['equipment'][0]['notes'],'이상 없음')

    def test_all_excluded_has_no_false_100_percent(self):
        for row in work.dashboard(self.task)['equipment']:
            self.update(row['equipment_id'],'exclude')
        stats = work.dashboard(self.task)['summary']
        self.assertEqual((stats['target'],stats['pending'],stats['excluded']),(0,0,50))
        self.assertIsNone(stats['percent'])

    def test_restart_persists_work_completion_and_exclusions(self):
        self.complete(272)
        self.update(102,'exclude')
        database.init_database()
        self.assertEqual(len(work.list_campaigns()),1)
        stats = work.dashboard(self.task)['summary']
        self.assertEqual((stats['completed'],stats['excluded']),(1,1))

    def test_excluded_units_reject_completion(self):
        self.update(101,'exclude')
        with self.assertRaises(ValueError):
            self.complete(version=2)
        self.assertEqual(len(work.changes(self.task)),1)

    def test_edit_clear_and_audit_preserve_prior_details(self):
        self.complete()
        self.update(101,'complete',2,completion_date=self.today,workers='수정 작업자',notes='수정 비고')
        self.update(101,'clear',3)
        self.assertIsNone(work.dashboard(self.task)['equipment'][0]['completion_date'])
        history = work.changes(self.task,101)
        self.assertEqual(len(history),3)
        self.assertEqual(history[0]['before']['notes'],'수정 비고')
        self.assertEqual(history[1]['before']['workers'],'김정비, 이정비')

    def test_stale_change_fails_and_does_not_append_audit(self):
        self.complete()
        with self.assertRaises(ValueError):
            self.update(101,'exclude',1)
        self.assertEqual(len(work.changes(self.task)),1)
        self.assertFalse(work.dashboard(self.task)['equipment'][0]['excluded'])

    def test_simultaneous_clicks_have_single_winner(self):
        def click(_):
            try:
                self.update(101,'exclude')
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            result = list(pool.map(click,range(4)))
        self.assertEqual(sum(result),1)
        self.assertEqual(len(work.changes(self.task)),1)

    def test_validation_and_duplicate_work(self):
        for name in ['', ' '*4, '가'*121]:
            with self.assertRaises(ValueError):
                work.create_campaign(name)
        with self.assertRaises(ValueError):
            work.create_campaign('비상정지 스위치 점검','2026년 10월')
        for day in ['2026-02-30',(date.today()+timedelta(days=1)).isoformat()]:
            with self.assertRaises(ValueError):
                self.update(101,'complete',completion_date=day,workers='작업자')
        with self.assertRaises(ValueError):
            self.update(101,'complete',completion_date=self.today,workers=' ')
        with self.assertRaises(ValueError):
            self.update(999,'exclude')
        self.assertEqual(work.changes(self.task),[])

    def test_upgrade_backup_and_existing_pms_preserved(self):
        from ACSP import pms
        pms.save_record(101,'PMS',self.today,'기존 PMS 작업자')
        with database.get_connection() as conn:
            conn.execute('DROP TABLE work_changes')
            conn.execute('DROP TABLE work_equipment')
            conn.execute('DROP TABLE work_campaigns')
        database.init_database()
        database.init_database()
        self.assertEqual(len(list((Path(self.temp.name)/'backups').glob('*before_work_v4*.db'))),1)
        self.assertEqual(pms.list_records()[0]['workers'],'기존 PMS 작업자')
        self.assertEqual(work.list_campaigns(),[])


if __name__ == '__main__':
    unittest.main()
