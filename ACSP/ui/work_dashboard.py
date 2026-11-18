"""Compact, task-specific dashboard for QC and ARMGC fleets."""
import csv
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .. import work_tracking as store


class NewWorkDialog(tk.Toplevel):
    def __init__(self, parent, on_created):
        super().__init__(parent)
        self.title('작업 등록')
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.on_created = on_created
        body = ttk.Frame(self, padding=20)
        body.pack(fill='both', expand=True)
        self.name_var = tk.StringVar()
        self.round_var = tk.StringVar()
        for row, (label, var) in enumerate([('작업명 *',self.name_var),('차수 / 기간 (선택)',self.round_var)]):
            ttk.Label(body,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=8)
            ttk.Entry(body,textvariable=var,width=42).grid(row=row,column=1,pady=8)
        ttk.Label(body,text='예: 비상정지 스위치 점검 / 2026년 10월\n새 작업은 전체 장비를 대상으로 시작합니다. 제외할 호기는 화면에서 선택하세요.',
                  wraplength=450).grid(row=2,column=0,columnspan=2,pady=12,sticky='w')
        ttk.Button(body,text='작업 등록',command=self.save).grid(row=3,column=1,sticky='e')
        self.grab_set()

    def save(self):
        try:
            task_id = store.create_campaign(self.name_var.get(),self.round_var.get())
        except Exception as exc:
            messagebox.showerror('등록 실패',str(exc),parent=self)
            return
        self.on_created(task_id)
        self.destroy()


class WorkDashboard(ttk.Frame):
    COLORS = {'완료':('#e3f3e9','#196f50'), '미완료':('#edf1f5','#4c6273'), '제외':('#fafbfc','#b9c1c8')}

    def __init__(self, parent):
        super().__init__(parent,style='Main.TFrame')
        self.campaign_id = None
        self.campaigns = []
        self.rows = {}
        self.tiles = {}
        self.selected = None
        self.selected_snapshot = None
        self.poll_id = None
        self.data = None
        self.columns = 12
        self.exclude_mode = tk.BooleanVar(value=False)
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.workers_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self._build()
        self.load_campaigns()
        self.bind('<Configure>',self.resize)
        self.poll_id = self.after(15000,self.poll)

    def _build(self):
        style = ttk.Style(self)
        style.configure('WorkSecondary.TButton',background='#f5f7fa',foreground='#526678',padding=6)
        style.map('WorkSecondary.TButton',background=[('disabled','#f5f7fa'),('pressed','#dce6ee'),('active','#e5edf3')],
                  foreground=[('disabled','#aab5bf'),('active','#2c3e50')])
        style.configure('Work.Horizontal.TProgressbar',background='#29936b',troughcolor='#dce5e8',
                        borderwidth=0,thickness=8,lightcolor='#29936b',darkcolor='#29936b')
        style.configure('Work.TCheckbutton',background='#ecf0f1',foreground='#526678')
        style.map('Work.TCheckbutton',background=[('active','#ecf0f1')])
        heading = ttk.Frame(self,style='Main.TFrame')
        heading.pack(fill='x',pady=(0,10))
        ttk.Label(heading,text='작업 완료 현황',font=('맑은 고딕',20,'bold')).pack(side='left')
        ttk.Button(heading,text='새로고침',style='WorkSecondary.TButton',command=lambda:self.load_campaigns(self.campaign_id)).pack(side='right')
        ttk.Button(heading,text='변경 이력',style='WorkSecondary.TButton',command=self.show_history).pack(side='right',padx=5)
        ttk.Button(heading,text='CSV 저장',style='WorkSecondary.TButton',command=self.export).pack(side='right')
        bar = ttk.Frame(self,style='Card.TFrame',padding=10)
        bar.pack(fill='x')
        ttk.Label(bar,text='작업',style='Card.TLabel').pack(side='left',padx=(0,8))
        self.combo = ttk.Combobox(bar,state='readonly')
        self.combo.pack(side='left',fill='x',expand=True)
        self.combo.bind('<<ComboboxSelected>>',self.choose_campaign)
        ttk.Button(bar,text='+ 작업 등록',command=lambda:NewWorkDialog(self,self.load_campaigns)).pack(side='left',padx=(8,0))
        self.summary_label = ttk.Label(self,font=('맑은 고딕',13,'bold'))
        self.summary_label.pack(anchor='w',pady=(9,5))
        self.progress = ttk.Progressbar(self,maximum=100,style='Work.Horizontal.TProgressbar')
        self.progress.pack(fill='x')
        modebar = ttk.Frame(self,style='Main.TFrame')
        modebar.pack(fill='x',pady=7)
        self.mode_button = ttk.Checkbutton(modebar,text='대상 제외 / 포함 모드',style='Work.TCheckbutton',variable=self.exclude_mode,command=self.mode_changed)
        self.mode_button.pack(side='left')
        self.mode_hint = ttk.Label(modebar,text='',foreground='#a65e0c')
        self.mode_hint.pack(side='left',padx=10)
        ttk.Label(modebar,text='✓ 완료   — 미완료   × 대상 제외').pack(side='right')
        self.work_title = ttk.Label(self,text='작업을 등록해 주세요',font=('맑은 고딕',16,'bold'),wraplength=850)
        self.work_title.pack(anchor='w',pady=(0,7))
        self.fleet_frames = {}
        self.fleet_labels = {}
        for fleet in ('QC','ARMGC'):
            panel = ttk.Frame(self,style='Card.TFrame',padding=8)
            panel.pack(fill='x',pady=(0,7))
            self.fleet_labels[fleet] = ttk.Label(panel,text=fleet,style='Card.TLabel',font=('맑은 고딕',11,'bold'))
            self.fleet_labels[fleet].pack(anchor='w',pady=(0,7))
            grid = ttk.Frame(panel,style='Card.TFrame')
            grid.pack(fill='x')
            self.fleet_frames[fleet] = grid
        editor = ttk.Frame(self,style='Card.TFrame',padding=10)
        editor.pack(fill='x',pady=(0,6))
        self.detail_label = ttk.Label(editor,text='작업을 등록한 후 호기를 선택하세요.',style='Card.TLabel')
        self.detail_label.grid(row=0,column=0,columnspan=5,sticky='w',pady=(0,7))
        self.entries = []
        for column, (label,var,width) in enumerate([('완료일 (YYYY-MM-DD)',self.date_var,14),('작업자',self.workers_var,24)]):
            cell = ttk.Frame(editor,style='Card.TFrame')
            cell.grid(row=1,column=column,sticky='ew',padx=(0,8))
            ttk.Label(cell,text=label,style='Card.TLabel').pack(anchor='w')
            entry = ttk.Entry(cell,textvariable=var,width=width)
            entry.pack(fill='x')
            self.entries.append(entry)
        self.save_button = ttk.Button(editor,text='완료 저장 / 수정',command=self.save_completion)
        self.save_button.grid(row=1,column=2,sticky='s',padx=3)
        self.clear_button = ttk.Button(editor,text='완료 취소',style='WorkSecondary.TButton',command=self.clear_completion)
        self.clear_button.grid(row=1,column=3,sticky='s',padx=3)
        ttk.Label(editor,text='비고',style='Card.TLabel').grid(row=2,column=0,sticky='w',pady=(7,0))
        self.notes_entry = ttk.Entry(editor,textvariable=self.notes_var)
        self.notes_entry.grid(row=3,column=0,columnspan=4,sticky='ew')
        self.entries.append(self.notes_entry)
        editor.columnconfigure(1,weight=1)
        self.feedback = ttk.Label(self,text='',wraplength=850)
        self.feedback.pack(anchor='w')

    def load_campaigns(self, preferred=None):
        self.campaigns = store.list_campaigns()
        labels = [c['name'] + (f" / {c['round_name']}" if c['round_name'] else '') for c in self.campaigns]
        self.combo.configure(values=labels)
        if not self.campaigns:
            self.combo.set('등록된 작업 없음 — 작업 등록을 눌러 시작하세요')
            self.summary_label.config(text='작업을 등록하면 QC 12대 · ARMGC 38대가 표시됩니다.')
            self.update_editor()
            self.mode_button.state(['disabled'])
            return
        self.mode_button.state(['!disabled'])
        index = next((i for i,c in enumerate(self.campaigns) if c['id']==preferred),0)
        self.combo.current(index)
        self.choose_campaign()

    def choose_campaign(self, event=None):
        index = self.combo.current()
        if index < 0 or index >= len(self.campaigns):
            return
        new_id = self.campaigns[index]['id']
        if new_id != self.campaign_id:
            self.selected = self.selected_snapshot = None
        self.campaign_id = new_id
        self.exclude_mode.set(False)
        self.refresh(reset_form=True)
        self.mode_changed()

    def refresh(self, reset_form=False):
        if self.campaign_id is None:
            return
        self.data = store.dashboard(self.campaign_id)
        campaign = self.data['campaign']
        self.work_title.config(text=campaign['name'] + (f"  ·  {campaign['round_name']}" if campaign['round_name'] else ''))
        self.rows = {r['equipment_id']:r for r in self.data['equipment']}
        stats = self.data['summary']
        percent = f"{stats['percent']:g}%" if stats['percent'] is not None else '대상 없음'
        self.summary_label.config(text=f"완료 {stats['completed']} / 대상 {stats['target']}대   ·   미완료 {stats['pending']}대   ·   제외 {stats['excluded']}대   |   {percent}")
        self.progress['value'] = stats['percent'] or 0
        for fleet, counts in self.data['fleets'].items():
            self.fleet_labels[fleet].config(text=f"{fleet}  {counts['total']}대       완료 {counts['completed']} / 대상 {counts['target']}   ·   미완료 {counts['pending']}   ·   제외 {counts['excluded']}")
        self.draw_tiles()
        if reset_form:
            self.selected_snapshot = self.rows.get(self.selected)
            self.fill_form()
        self.update_editor()

    def draw_tiles(self):
        for frame in self.fleet_frames.values():
            for child in frame.winfo_children():
                child.destroy()
            for column in range(12):
                frame.columnconfigure(column,weight=1 if column<self.columns else 0,minsize=0)
        self.tiles = {}
        for fleet, frame in self.fleet_frames.items():
            units = [r for r in self.rows.values() if r['equipment_type']==fleet]
            for index,row in enumerate(units):
                bg,fg = self.COLORS[row['status']]
                mark = {'완료':'✓','미완료':'—','제외':'×'}[row['status']]
                selected = row['equipment_id'] == self.selected
                # Tk has no per-widget alpha; blend excluded tiles into the white panel.
                border = tk.Frame(frame,bg='#2684b5' if selected else bg,padx=2,pady=2)
                border.grid(row=index//self.columns,column=index%self.columns,sticky='ew',padx=2,pady=2)
                button = tk.Button(border,text=f"{row['equipment_id']}  {mark}",font=('맑은 고딕',11,'normal' if row['excluded'] else 'bold'),
                                   bg=bg,fg=fg,activebackground=bg,activeforeground=fg,relief='flat',
                                   bd=0,padx=0,pady=4,cursor='hand2',highlightthickness=0,
                                   command=lambda eq=row['equipment_id']:self.unit_clicked(eq))
                button.pack(fill='x')
                self.tiles[row['equipment_id']] = button

    def resize(self, event):
        if event.widget is not self:
            return
        self.work_title.configure(wraplength=max(300,event.width-10))
        columns = 12 if event.width >= 720 else 6
        if columns != self.columns:
            self.columns = columns
            self.draw_tiles()

    def unit_clicked(self, equipment_id):
        row = self.rows[equipment_id]
        self.selected = equipment_id
        if self.exclude_mode.get():
            action = 'include' if row['excluded'] else 'exclude'
            try:
                store.update_equipment(self.campaign_id,equipment_id,row['version'],action)
                self.feedback.config(text=f"{row['equipment_type']} {equipment_id}호: {'대상에 포함했습니다.' if action=='include' else '대상에서 제외했습니다.'} 변경 사항이 저장되었습니다.")
            except Exception as exc:
                messagebox.showerror('변경 실패',str(exc),parent=self)
            self.refresh(reset_form=True)
        else:
            self.selected_snapshot = dict(row)
            self.fill_form()
            self.draw_tiles()
            self.update_editor()

    def mode_changed(self):
        self.mode_hint.config(text='클릭 → 제외 / 복원 · 즉시 저장' if self.exclude_mode.get() else '')
        self.feedback.config(text='호기를 클릭하면 제외 / 포함으로 전환합니다. 기존 완료 실적은 보존됩니다.'
                             if self.exclude_mode.get() else '호기를 클릭하면 완료일과 작업자를 입력하거나 확인할 수 있습니다.')
        self.update_editor()

    def fill_form(self):
        row = self.selected_snapshot
        self.date_var.set(row['completion_date'] if row and row['completion_date'] else date.today().isoformat())
        self.workers_var.set(row['workers'] if row else '')
        self.notes_var.set(row['notes'] if row else '')

    def update_editor(self):
        row = self.rows.get(self.selected)
        enabled = row is not None and not row['excluded'] and not self.exclude_mode.get()
        for widget in self.entries+[self.save_button]:
            widget.state(['!disabled'] if enabled else ['disabled'])
        self.clear_button.state(['!disabled'] if enabled and row['completion_date'] else ['disabled'])
        if not row:
            text = '호기를 선택하세요.' if self.campaign_id else '작업을 먼저 등록하세요.'
        else:
            text = f"{row['equipment_type']} {row['equipment_id']}호 · {row['status']}"
            if row['completion_date']:
                text += f" · 완료일 {row['completion_date']} · {row['workers']}"
            if row['excluded']:
                text += ' · 완료율에서 제외 (기존 실적 보존)'
            if self.selected_snapshot and self.selected_snapshot['version'] != row['version']:
                text += ' · 다른 창에서 변경됨: 호기를 다시 선택하세요'
        self.detail_label.config(text=text,wraplength=max(650,self.winfo_width()-40))

    def save_completion(self):
        row = self.selected_snapshot
        if not row or self.exclude_mode.get():
            return
        try:
            store.update_equipment(self.campaign_id,row['equipment_id'],row['version'],'complete',
                                   completion_date=self.date_var.get().strip(),workers=self.workers_var.get(),notes=self.notes_var.get())
        except Exception as exc:
            messagebox.showerror('저장 실패',str(exc),parent=self)
            return
        self.feedback.config(text=f"{row['equipment_id']}호의 완료 실적을 저장했습니다.")
        self.refresh(reset_form=True)

    def clear_completion(self):
        row = self.selected_snapshot
        if not row or not row['completion_date'] or self.exclude_mode.get():
            return
        if not messagebox.askyesno('완료 취소',f"{row['equipment_id']}호를 미완료로 되돌릴까요? 이전 실적은 변경 이력에 보존됩니다.",parent=self):
            return
        try:
            store.update_equipment(self.campaign_id,row['equipment_id'],row['version'],'clear')
            self.feedback.config(text=f"{row['equipment_id']}호를 미완료로 변경했습니다.")
            self.refresh(reset_form=True)
        except Exception as exc:
            messagebox.showerror('변경 실패',str(exc),parent=self)

    def show_history(self):
        if self.campaign_id is None:
            return
        window = tk.Toplevel(self)
        window.title('작업 변경 이력 — '+self.combo.get())
        window.geometry('1050x480')
        window.transient(self.winfo_toplevel())
        ttk.Label(window,text='시간은 UTC 기준입니다. 제외·포함·완료 수정·완료 취소 이력을 보존합니다.').pack(anchor='w',padx=12,pady=10)
        columns = ('시간 (UTC)','호기','변경','완료일 (변경 전 → 후)','작업자','비고')
        tree = ttk.Treeview(window,columns=columns,show='headings')
        for col,width in zip(columns,[150,60,95,205,160,260]):
            tree.heading(col,text=col)
            tree.column(col,width=width)
        scroll = ttk.Scrollbar(window,command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y')
        tree.pack(fill='both',expand=True,padx=12,pady=(0,12))
        actions = {'complete':'완료 저장','clear':'완료 취소','exclude':'대상 제외','include':'대상 포함'}
        for record in store.changes(self.campaign_id):
            before,after = record['before'],record['after']
            tree.insert('', 'end',values=(record['created_at'],record['equipment_id'],actions[record['action']],
                f"{before['completion_date'] or '—'} → {after['completion_date'] or '—'}",
                after['workers'] or before['workers'],after['notes'] or before['notes']))

    def export(self):
        if not self.data:
            return
        path = filedialog.asksaveasfilename(parent=self,defaultextension='.csv',filetypes=[('Excel CSV','*.csv')])
        if not path:
            return
        try:
            data = store.dashboard(self.campaign_id)
            with open(path,'w',encoding='utf-8-sig',newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['작업명','차수 / 기간','장비','호기','대상 여부','상태','완료일','작업자','비고'])
                for row in data['equipment']:
                    values = [data['campaign']['name'],data['campaign']['round_name'],row['equipment_type'],row['equipment_id'],
                              '제외' if row['excluded'] else '포함',row['status'],row['completion_date'] or '',row['workers'],row['notes']]
                    writer.writerow(["'"+str(v) if str(v).lstrip().startswith(('=','+','-','@')) else v for v in values])
            self.feedback.config(text=f'조회 결과를 저장했습니다: {path}')
        except Exception as exc:
            messagebox.showerror('출력 실패',str(exc),parent=self)

    def poll(self):
        try:
            if self.winfo_ismapped():
                self.refresh()
        except Exception as exc:
            self.feedback.config(text=f'새로고침 실패: {exc}')
        finally:
            self.poll_id = self.after(15000,self.poll)

    def destroy(self):
        if self.poll_id:
            self.after_cancel(self.poll_id)
            self.poll_id = None
        super().destroy()
