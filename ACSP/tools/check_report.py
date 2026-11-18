"""Offline report packaging check. Uses a temporary DB and never opens Outlook."""
import json
import os
import sys
import tempfile
import traceback
from datetime import date, timedelta
from pathlib import Path


def check_report(result_path):
    result = {'ok': False, 'frozen': bool(getattr(sys, 'frozen', False))}
    previous_db = os.environ.get('ACSP_DB_PATH')
    root = None
    try:
        with tempfile.TemporaryDirectory(prefix='craneon-report-check-') as folder:
            os.environ['ACSP_DB_PATH'] = str(Path(folder) / 'test.db')
            try:
                import tkinter as tk
                import numpy as np
                import pythoncom
                import pywintypes
                import win32com.client
                from ACSP import database
                from ACSP import work_tracking
                from ACSP.ui.work_dashboard import WorkDashboard
                from ACSP.ui.styles import apply_styles
                from ACSP.ui.report import DailyReportWindow
                from ACSP.logic.report_generator import ReportGenerator
                from ACSP.version import __version__

                result.update(version=__version__, numpy=np.__version__)
                result['outlook_modules'] = 'ok'
                # Exercise native NumPy imports as well as Python module imports.
                if not np.allclose(np.linalg.solve([[2., 0.], [0., 4.]], [4., 8.]), [2., 2.]):
                    raise AssertionError('NumPy native calculation failed')
                database.init_database()
                with database.get_connection() as conn:
                    conn.execute('UPDATE equipment SET last_maintenance_date=? WHERE id=101',
                                 ((date.today()-timedelta(days=50)).isoformat(),))
                root = tk.Tk()
                root.withdraw()
                apply_styles(root)
                callback_errors = []
                root.report_callback_exception = lambda *error: callback_errors.append(str(error))
                from ACSP.ui.app import ACSPApp
                from ACSP.ui.pms import PMSRecordDialog
                app = ACSPApp(root)
                app.switch_type('QC')
                if len(app.tree.get_children()) != 12:
                    raise AssertionError('QC must show exactly one row per unit')
                dialog = PMSRecordDialog(root, equipment_id=102, on_saved=app.load_data)
                dialog.withdraw()
                if set(dialog.fields) != {'equipment_id', 'maintenance_date'}:
                    raise AssertionError('QC entry must contain only unit and date')
                dialog.save()
                result['unified_qc'] = '12 units / one PMS / entry ok'
                window = DailyReportWindow(root)
                window.withdraw()
                root.update()
                campaign = work_tracking.create_campaign('Packaging check')
                dashboard = WorkDashboard(root)
                dashboard.load_campaigns(campaign)
                dashboard.unit_clicked(101)
                dashboard.workers_var.set('Packaging test')
                dashboard.save_completion()
                dashboard.exclude_mode.set(True)
                dashboard.mode_changed()
                dashboard.tiles[101].invoke()
                if dashboard.data['summary']['target'] != 49 or dashboard.data['summary']['completed'] != 0:
                    raise AssertionError('Work exclusion failed')
                dashboard.tiles[101].invoke()
                if dashboard.data['summary']['completed'] != 1:
                    raise AssertionError('Work completion restoration failed')
                dashboard.destroy()
                result['work_dashboard'] = 'ok'
                if callback_errors:
                    raise RuntimeError(str(callback_errors))
                if window.notebook.index('end') != 2:
                    raise AssertionError('Report tabs missing')
                result['report_window'] = 'ok'
                stats = database.get_daily_report_stats()
                if stats['qc_overdue'] != 1 or stats['qc_data'][0]['source'] != 'unit':
                    raise AssertionError('Legacy QC overdue not included')
                result['legacy_qc_overdue'] = stats['qc_overdue']
                html = ReportGenerator.build_html_body(stats)
                if not html or '<table' not in html.lower():
                    raise AssertionError('Report HTML missing')
                for fleet in ('qc', 'armgc'):
                    chart = Path(folder) / f'{fleet}.png'
                    ReportGenerator.generate_chart(stats[f'{fleet}_data'], fleet.upper(),
                        stats[f'{fleet}_overdue'], stats[f'{fleet}_total'], stats[f'{fleet}_rate'], str(chart))
                    if chart.stat().st_size < 1000:
                        raise AssertionError(f'{fleet} chart missing')
                today = date.today()
                calendar = Path(folder) / 'calendar.png'
                ReportGenerator.generate_calendar_image(today.year, today.month, {}, str(calendar))
                if calendar.stat().st_size < 1000:
                    raise AssertionError('Calendar image missing')
                result.update(ok=True, charts='QC / ARMGC / calendar', html='ok')
            finally:
                if root is not None:
                    root.destroy()
    except Exception:
        result['error'] = traceback.format_exc()
    finally:
        if previous_db is None:
            os.environ.pop('ACSP_DB_PATH', None)
        else:
            os.environ['ACSP_DB_PATH'] = previous_db
    Path(result_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if result['ok'] else 1
