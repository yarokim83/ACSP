"""Isolated desktop layout preview; closes automatically after two minutes."""
from datetime import date
import os
from pathlib import Path
import tempfile
import tkinter as tk
from ACSP import database, work_tracking
from ACSP.ui.app import ACSPApp

with tempfile.TemporaryDirectory() as folder:
    os.environ['ACSP_DB_PATH'] = str(Path(folder)/'preview.db')
    database.init_database()
    campaign = work_tracking.create_campaign('비상정지 스위치 기능 점검','2026년 10월 · 테스트')
    rows = work_tracking.dashboard(campaign)['equipment']
    for row in rows:
        if row['equipment_id'] % 3 != 0:
            work_tracking.update_equipment(campaign,row['equipment_id'],1,'complete',
                completion_date=date.today().isoformat(),workers='테스트 작업자')
    for row in work_tracking.dashboard(campaign)['equipment']:
        if row['equipment_id'] in (104,105,211,213,271):
            work_tracking.update_equipment(campaign,row['equipment_id'],row['version'],'exclude')
    root = tk.Tk()
    app = ACSPApp(root)
    root.title('CRANEON 작업 대시보드 검증 (임시 데이터)')
    app.show_work_dashboard()
    app.work_dashboard.unit_clicked(101)
    def inspect_layout():
        view = app.work_dashboard
        bottom = view.feedback.winfo_rooty()+view.feedback.winfo_height()
        window = app.work_window
        viewport_bottom = window.winfo_rooty()+window.winfo_height()
        fits = (view.feedback.winfo_ismapped() and bottom <= viewport_bottom
                and view.feedback.winfo_height() >= view.feedback.winfo_reqheight())
        print(f'LAYOUT: tiles={len(view.tiles)}, content_bottom={bottom}, window_bottom={viewport_bottom}, fits={fits}',flush=True)
    root.after(1000,inspect_layout)
    root.after(120000,app.close)
    root.mainloop()
