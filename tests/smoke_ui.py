"""Run manually: python -m tests.smoke_ui (does not use the production database)."""
import os
from pathlib import Path
import tempfile
import tkinter as tk
from datetime import date

from ACSP import database, pms
from ACSP.ui.app import ACSPApp
from ACSP.ui.pms import PMSWindow, PMSRecordDialog
from ACSP.ui.calendar import MaintenanceCalendar
from ACSP.ui.pms_network import PMSNetworkWindow
from ACSP.ui.graph import OverdueGraph


def main():
    with tempfile.TemporaryDirectory() as folder:
        os.environ['ACSP_DB_PATH'] = str(Path(folder) / 'ui.db')
        database.init_database()
        root = tk.Tk()
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda *error: errors.append(error)
        app = ACSPApp(root)
        assert app.equipment_panel.winfo_manager() == 'pack'
        assert app.work_window is None
        app.switch_type('QC')
        assert len(app.tree.get_children()) == 12
        from ACSP import work_tracking
        app.show_work_dashboard()
        work_view = app.work_dashboard
        assert work_view.winfo_toplevel() is app.work_window
        assert app.equipment_panel.winfo_manager() == 'pack'
        assert app.stats_frame.winfo_manager() == 'pack'
        assert app.work_window.grab_current() is None
        app.show_work_dashboard()
        assert app.work_dashboard is work_view
        assert work_view.campaign_id is None
        campaign_id = work_tracking.create_campaign('UI 작업','1차')
        work_view.load_campaigns(campaign_id)
        assert len(work_view.tiles) == 50
        work_view.unit_clicked(101)
        work_view.workers_var.set('UI 작업자')
        work_view.save_completion()
        assert work_view.data['summary']['completed'] == 1
        work_view.exclude_mode.set(True)
        work_view.mode_changed()
        work_view.tiles[101].invoke()
        assert work_view.data['summary']['target'] == 49
        assert work_view.data['summary']['completed'] == 0
        assert work_view.rows[101]['completion_date'] == date.today().isoformat()
        work_view.tiles[101].invoke()
        assert work_view.data['summary']['target'] == 50
        assert work_view.data['summary']['completed'] == 1
        other_campaign = work_tracking.create_campaign('UI 다른 작업')
        work_view.load_campaigns(other_campaign)
        assert not work_view.exclude_mode.get()
        assert work_view.data['summary']['completed'] == 0
        timer = work_view.poll_id
        app.close_work_dashboard()
        assert timer not in root.tk.call('after','info')
        assert app.work_window is None and app.work_dashboard is None
        app.show_work_dashboard()
        app.work_dashboard.load_campaigns(campaign_id)
        assert app.work_dashboard.data['summary']['completed'] == 1
        app.show_equipment_dashboard()
        window = PMSWindow(root)
        window.withdraw()
        assert len(window.matrix.get_children()) == 12
        dialog = PMSRecordDialog(window, equipment_id=101, task='PMS', on_saved=window.saved)
        dialog.withdraw()
        assert set(dialog.fields) == {'equipment_id', 'maintenance_date'}
        dialog.save()
        assert len(window.history.get_children()) == 1
        app.load_data()
        app.sort_treeview('Days Passed')
        app.sort_treeview('Remaining')
        calendar = MaintenanceCalendar(root)
        calendar.withdraw()
        calendar.show_maintenance_info(date.today().isoformat())
        assert len(calendar.pms_records) == 1
        assert calendar.maintenance_equipment_map[date.today().isoformat()]['QC'] == ['101']
        graph = OverdueGraph(root)
        graph.withdraw()
        graph.switch_filter('QC')
        network = PMSNetworkWindow(root, app.pms_service)
        network.withdraw()
        root.update()
        from ACSP.logic.report_generator import ReportGenerator
        stats = database.get_daily_report_stats()
        assert '- QC :' in ReportGenerator.build_html_body(stats)
        chart = ReportGenerator.generate_chart(stats['qc_data'], 'QC PMS', stats['qc_overdue'],
                                                stats['qc_total'], stats['qc_rate'], str(Path(folder) / 'chart.png'))
        assert Path(chart).stat().st_size > 1000
        for child in (network, graph, calendar, window):
            child.destroy()
        app.close()
        assert not errors, errors
        assert pms.list_records()[0]['workers'] == ''
        print('Desktop smoke test passed: QC dashboard, status, entry, history, calendar, graph, network dialog.')
    os.environ.pop('ACSP_DB_PATH', None)


if __name__ == '__main__':
    main()
