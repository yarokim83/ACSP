"""Regression checks for sorting after the live dashboard reloads its rows."""
import os
import tempfile
import tkinter as tk
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from ACSP import database, pms
from ACSP.ui.app import ACSPApp


class DashboardSortTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, ACSP_DB_PATH=str(Path(self.temp.name) / 'sort.db'))
        env.start()
        self.addCleanup(env.stop)
        database.init_database()
        with database.get_connection() as conn:
            for equipment_id, days in [(211, 5), (212, 50), (213, 20), (214, 65)]:
                conn.execute('UPDATE equipment SET last_maintenance_date=? WHERE id=?',
                             ((date.today()-timedelta(days=days)).isoformat(), equipment_id))
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = ACSPApp(self.root)
        self.addCleanup(self.app.close)

    def rows(self):
        return [self.app.tree.item(key)['values'] for key in self.app.tree.get_children()]

    def refresh(self):
        # Run the real timer callback without waiting 15 seconds or adding timers.
        self.root.after_cancel(self.app.refresh_timer)
        self.app.refresh_dashboard()

    def assert_remaining_order(self, reverse):
        values = [int(row[4].replace(' days', '')) for row in self.rows() if row[4] != '—']
        self.assertEqual(values, sorted(values, reverse=reverse))
        self.assertEqual(self.app.sort_reverse, reverse)

    def test_remaining_both_directions_survive_repeated_refresh_and_selection(self):
        tree = self.app.tree
        selected = next(key for key in tree.get_children() if tree.item(key)['values'][0] == 213)
        tree.selection_set(selected)
        for reverse in (False, True):
            self.app.sort_treeview('Remaining')
            expected = self.rows()
            self.assert_remaining_order(reverse)
            for _ in range(3):
                self.refresh()
                self.assertEqual(self.rows(), expected)
                self.assert_remaining_order(reverse)
                self.assertEqual([tree.item(key)['values'][0] for key in tree.selection()], [213])

    def test_filter_fleet_switch_and_updated_dates_keep_sort(self):
        self.app.sort_treeview('Remaining')
        self.app.switch_status('overdue')
        self.assertEqual([row[0] for row in self.rows()], [214, 212])
        self.app.switch_status('all')
        with database.get_connection() as conn:
            conn.execute('UPDATE equipment SET last_maintenance_date=? WHERE id=213',
                         ((date.today()-timedelta(days=90)).isoformat(),))
        self.refresh()
        self.assertEqual(self.rows()[0][0], 213)
        self.assert_remaining_order(False)
        for eq, task, days in [(101, 'PMS', 5), (102, 'PMS', 70), (103, 'PMS', 30)]:
            pms.save_record(eq, task, (date.today()-timedelta(days=days)).isoformat(), 'Sort test')
        self.app.switch_type('QC')
        self.assertEqual(self.rows()[0][0], 102)
        for reverse in (False, True):
            if reverse:
                self.app.sort_treeview('Remaining')
            expected = self.rows()
            self.refresh()
            self.assertEqual(self.rows(), expected)
            self.assert_remaining_order(reverse)
        self.app.switch_type('ARMGC')
        self.assert_remaining_order(True)

    def test_default_order_and_other_headers_survive_reload(self):
        expected = self.rows()
        self.refresh()
        self.assertEqual(self.rows(), expected)
        self.assertIsNone(self.app.sort_column)
        for column in ('ID', 'Last Maintenance', 'Status', 'Days Passed'):
            for reverse in (False, True):
                self.app.sort_treeview(column)
                expected = self.rows()
                self.app.load_data()
                self.assertEqual(self.rows(), expected)
                self.assertEqual(self.app.sort_reverse, reverse)


if __name__ == '__main__':
    unittest.main()
