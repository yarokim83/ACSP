"""QC task status, completion entry and completed-work list."""
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date
from .. import pms


def make_tree(parent, headings, widths=None):
    frame = ttk.Frame(parent)
    frame.pack(fill='both', expand=True, pady=8)
    tree = ttk.Treeview(frame, columns=headings, show='headings', selectmode='browse')
    for i, heading in enumerate(headings):
        tree.heading(heading, text=heading)
        tree.column(heading, width=widths[i] if widths else 120, minwidth=60, anchor='center')
    scroll = ttk.Scrollbar(frame, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side='left', fill='both', expand=True)
    scroll.pack(side='right', fill='y')
    return tree


class PMSRecordDialog(tk.Toplevel):
    def __init__(self, parent, equipment_id=None, task=None, initial_date=None, record=None, on_saved=None):
        super().__init__(parent)
        self.title('QC PMS 시행 실적 수정' if record else 'QC PMS 시행 실적 입력')
        self.resizable(False, False)
        self.transient(parent)
        self.record = record
        self.on_saved = on_saved
        body = ttk.Frame(self, padding=20)
        body.pack(fill='both', expand=True)
        values = record or dict(equipment_id=equipment_id or pms.equipment_ids()[0],
                                task=task or pms.TASKS[0], maintenance_date=initial_date or date.today().isoformat(),
                                workers='', notes='')
        self.fields = {}
        for i, (key, label) in enumerate([('equipment_id', 'QC 호기'),
                                          ('maintenance_date', '시행일 (YYYY-MM-DD)')]):
            ttk.Label(body, text=label).grid(row=i, column=0, sticky='w', pady=8, padx=(0, 15))
            var = tk.StringVar(value=values[key])
            self.fields[key] = var
            if key in ('equipment_id', 'task'):
                entry = ttk.Combobox(body, textvariable=var, state='readonly', width=35,
                                     values=pms.equipment_ids() if key == 'equipment_id' else pms.TASKS)
            else:
                entry = ttk.Entry(body, textvariable=var, width=38)
            entry.grid(row=i, column=1, sticky='ew', pady=8)
        ttk.Label(body, text='호기별 통합 PMS · 다음 예정일 = 시행일 + 45일').grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(body, text='저장', command=self.save).grid(row=3, column=1, sticky='e')
        self.grab_set()

    def save(self):
        try:
            values = {key: var.get().strip() for key, var in self.fields.items()}
            values['equipment_id'] = int(values['equipment_id'])
            if self.record:
                values.update(record_id=self.record['id'], version=self.record['version'])
            pms.save_record(**values)
        except Exception as exc:
            messagebox.showerror('저장 실패', str(exc), parent=self)
            return
        if self.on_saved:
            self.on_saved()
        self.destroy()


class PMSWindow(tk.Toplevel):
    def __init__(self, parent, tab='status', on_saved=None):
        super().__init__(parent)
        self.title('QC PMS — 호기별 현황 / 시행 내역')
        self.geometry('1120x720')
        self.minsize(900, 580)
        self.transient(parent)
        self.on_saved = on_saved
        self.records = {}
        self.timer = None
        self.book = ttk.Notebook(self)
        self.book.pack(fill='both', expand=True, padx=16, pady=16)
        status = ttk.Frame(self.book, padding=12)
        history = ttk.Frame(self.book, padding=12)
        self.book.add(status, text='호기별 PMS 현황')
        self.book.add(history, text='PMS 시행 내역')
        bar = ttk.Frame(status)
        bar.pack(fill='x')
        ttk.Label(bar, text='QC PMS · 호기별 통합 / 45일 주기', font=('맑은 고딕', 16, 'bold')).pack(side='left')
        ttk.Button(bar, text='시행 실적 입력', command=self.add).pack(side='right', padx=4)
        ttk.Button(bar, text='새로고침', command=self.refresh).pack(side='right', padx=4)
        self.summary = ttk.Label(status)
        self.summary.pack(anchor='w', pady=8)
        self.matrix = make_tree(status, ('호기', '최근 시행일', '다음 예정일', '남은 일수', '상태', '작업자'), [65, 130, 130, 100, 90, 260])
        self.matrix.bind('<Double-1>', self.add_from_cell)
        ttk.Label(status, text='호기를 더블클릭하여 통합 PMS 실적을 입력하세요.').pack(anchor='w')
        filters = ttk.Frame(history)
        filters.pack(fill='x')
        self.filter_vars = {}
        for key, label, options in [('equipment_id', '호기', ['전체'] + [str(i) for i in pms.equipment_ids()]),
                                    ('task', '조회 구분', ['PMS', '분류별 보관 이력']),
                                    ('start', '시작일', None), ('end', '종료일', None)]:
            ttk.Label(filters, text=label).pack(side='left', padx=(6, 2))
            var = tk.StringVar(value=options[0] if options else '')
            self.filter_vars[key] = var
            widget = ttk.Combobox(filters, textvariable=var, values=options, state='readonly', width=10) if options else ttk.Entry(filters, textvariable=var, width=12)
            widget.pack(side='left')
        ttk.Button(filters, text='조회', command=self.load_history).pack(side='left', padx=8)
        actions = ttk.Frame(history)
        actions.pack(fill='x', pady=8)
        for label, command in [('실적 입력', self.add), ('선택 수정', self.edit), ('선택 삭제', self.delete), ('CSV 저장 (엑셀)', self.export)]:
            ttk.Button(actions, text=label, command=command).pack(side='left', padx=3)
        self.count_label = ttk.Label(actions)
        self.count_label.pack(side='right')
        self.history = make_tree(history, ('시행일', 'QC 호기', '작업', '작업자', '비고'), [110, 75, 100, 240, 430])
        ttk.Label(history, text='기존 호기별 실적은 통합 PMS로 표시합니다. 분류별 보관 이력은 조회만 가능하며 통합 완료로 집계하지 않습니다.').pack(anchor='w')
        self.book.select(history if tab == 'history' else status)
        self.refresh()
        self.timer = self.after(15000, self.poll)

    def refresh(self):
        jobs = pms.task_status()
        groups = {}
        for job in jobs:
            groups.setdefault(job['equipment_id'], {})[job['task']] = job
        self.matrix.delete(*self.matrix.get_children())
        for eq, tasks in groups.items():
            job = tasks['PMS']
            self.matrix.insert('', 'end', iid=str(eq), values=[eq, job['maintenance_date'] or '—', job['next_date'] or '—', job['remaining'] if job['remaining'] is not None else '—', job['status'], job['workers']])
        self.summary.config(text=f"{len(groups)}호기 · 통합 PMS | 지연 {sum(j['status']=='지연' for j in jobs)} · 임박 {sum(j['status']=='임박' for j in jobs)} · 미등록 {sum(j['status']=='미등록' for j in jobs)} | 15초마다 현황 갱신")
        self.load_history()

    def poll(self):
        # Keep a user's history selection/filter stable during automatic refresh.
        try:
            selected = self.history.selection()
            self.refresh()
            if selected and self.history.exists(selected[0]):
                self.history.selection_set(selected[0])
        except Exception:
            self.summary.config(text='갱신 실패 — 데이터베이스 연결을 확인하고 새로고침하세요.')
        self.timer = self.after(15000, self.poll)

    def destroy(self):
        if self.timer:
            self.after_cancel(self.timer)
            self.timer = None
        super().destroy()

    def load_history(self):
        try:
            filters = {k: v.get().strip() for k, v in self.filter_vars.items()}
            filters = {k: v for k, v in filters.items() if v and v != '전체'}
            rows = pms.list_records(**filters)
        except ValueError as exc:
            self.count_label.config(text=str(exc))
            return
        self.history.delete(*self.history.get_children())
        self.records = {}
        for row in rows:
            key = f"{'legacy' if row['legacy'] else 'pms'}-{row['id']}"
            self.records[key] = row
            self.history.insert('', 'end', iid=key, values=[row[k] for k in ('maintenance_date', 'equipment_id', 'task', 'workers', 'notes')])
        self.count_label.config(text=f'{len(rows)}건')

    def saved(self):
        self.refresh()
        if self.on_saved:
            self.on_saved()

    def add(self):
        PMSRecordDialog(self, on_saved=self.saved)

    def add_from_cell(self, event):
        row = self.matrix.identify_row(event.y)
        col = self.matrix.identify_column(event.x)
        if row and col:
            PMSRecordDialog(self, equipment_id=int(row), on_saved=self.saved)

    def selected_record(self):
        selection = self.history.selection()
        if not selection:
            messagebox.showinfo('실적 선택', '수정 또는 삭제할 실적을 선택하세요.', parent=self)
            return None
        row = self.records[selection[0]]
        if row['legacy']:
            messagebox.showinfo('기존 이력', '분류별 보관 이력은 원본 보존을 위해 조회만 가능합니다.', parent=self)
            return None
        return row

    def edit(self):
        row = self.selected_record()
        if row:
            PMSRecordDialog(self, record=row, on_saved=self.saved)

    def delete(self):
        row = self.selected_record()
        if row and messagebox.askyesno('실적 삭제', f"QC {row['equipment_id']} / {row['task']} / {row['maintenance_date']} 실적을 삭제할까요?", parent=self):
            try:
                pms.delete_record(row['id'], row['version'])
                self.saved()
            except Exception as exc:
                messagebox.showerror('삭제 실패', str(exc), parent=self)

    def export(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.csv', filetypes=[('Excel CSV', '*.csv')])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['시행일', 'QC 호기', '작업', '작업자', '비고'])
                for r in self.records.values():
                    cells = [str(r[k]) for k in ('maintenance_date', 'equipment_id', 'task', 'workers', 'notes')]
                    writer.writerow(["'" + v if v.lstrip().startswith(('=', '+', '-', '@')) else v for v in cells])
            messagebox.showinfo('저장 완료', path, parent=self)
        except OSError as exc:
            messagebox.showerror('저장 실패', str(exc), parent=self)
