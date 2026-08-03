import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from ..database import (
    get_email_recipients, 
    add_email_recipient, 
    update_email_recipient,
    delete_email_recipient, 
    get_daily_report_stats
)
from ..logic.report_generator import ReportGenerator
from .styles import COLORS, FONTS

class DailyReportWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Daily Email Report Generator")
        self.geometry("950x700")
        self.configure(bg=COLORS['bg'])
        
        # Main Frame
        self.main_frame = ttk.Frame(self, style='Main.TFrame')
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header
        self.header_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        self.header_frame.pack(fill='x', pady=(0, 15))
        ttk.Label(self.header_frame, text="📧 Daily Report & Outlook Auto-Emailer", font=FONTS['h1'], background=COLORS['bg']).pack(side='left')
        
        # Notebook (Tabs for Preview/Draft & Recipient Manager)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Tab 1: Email Generation & Draft
        self.tab_draft = ttk.Frame(self.notebook, style='Main.TFrame', padding=15)
        self.notebook.add(self.tab_draft, text=" 📧 보고서 생성 및 아웃룩 발송 ")
        
        # Tab 2: Recipient Manager (수신자 관리)
        self.tab_recipients = ttk.Frame(self.notebook, style='Main.TFrame', padding=15)
        self.notebook.add(self.tab_recipients, text=" 👥 수신자 주소록 관리 ")
        
        # Build UI Sections
        self.build_draft_tab()
        self.build_recipients_tab()
        
        # Load initial data
        self.refresh_stats()
        self.load_recipients()
        
    # =========================================================================
    # TAB 1: Report Generation & Outlook Draft
    # =========================================================================
    def build_draft_tab(self):
        # 1. Summary Card
        summary_card = ttk.Frame(self.tab_draft, style='Card.TFrame', padding=15)
        summary_card.pack(fill='x', pady=(0, 15))
        
        ttk.Label(summary_card, text="📊 Today's Maintenance Summary", style='CardHeader.TLabel').pack(anchor='w', pady=(0, 10))
        
        stats_frame = ttk.Frame(summary_card, style='Card.TFrame')
        stats_frame.pack(fill='x')
        
        self.lbl_qc_overdue = ttk.Label(stats_frame, text="QC Overdue: -", style='Card.TLabel', font=FONTS['h3'])
        self.lbl_qc_overdue.pack(side='left', padx=(0, 30))
        
        self.lbl_armgc_overdue = ttk.Label(stats_frame, text="ARMGC Overdue: -", style='Card.TLabel', font=FONTS['h3'])
        self.lbl_armgc_overdue.pack(side='left', padx=(0, 30))
        
        self.lbl_rm_count = ttk.Label(stats_frame, text="Active RM: -", style='Card.TLabel', font=FONTS['h3'])
        self.lbl_rm_count.pack(side='left')
        
        # 2. Email Subject & Recipients Card
        mail_card = ttk.Frame(self.tab_draft, style='Card.TFrame', padding=15)
        mail_card.pack(fill='x', pady=(0, 15))
        
        ttk.Label(mail_card, text="📝 Email Subject & Active Recipients", style='CardHeader.TLabel').pack(anchor='w', pady=(0, 10))
        
        # Subject Input
        sub_frame = ttk.Frame(mail_card, style='Card.TFrame')
        sub_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(sub_frame, text="메일 제목:", style='Card.TLabel', width=10).pack(side='left')
        
        today = datetime.now()
        weekdays_korean = ['월', '화', '수', '목', '금', '토', '일']
        date_str_short = f"{today.month}/{today.day}, {weekdays_korean[today.weekday()]}"
        default_subject = f"기술팀 일일 정비계획({date_str_short})"
        self.subject_var = tk.StringVar(value=default_subject)
        self.subject_entry = ttk.Entry(sub_frame, textvariable=self.subject_var, font=FONTS['body'])
        self.subject_entry.pack(side='left', fill='x', expand=True)
        
        # Active Recipients Display
        rec_frame = ttk.Frame(mail_card, style='Card.TFrame')
        rec_frame.pack(fill='x')
        
        ttk.Label(rec_frame, text="수신 (TO):", style='Card.TLabel', width=10).grid(row=0, column=0, sticky='w')
        self.lbl_to_list = ttk.Label(rec_frame, text="등록된 수신자 없음", style='Card.TLabel', foreground=COLORS['accent'])
        self.lbl_to_list.grid(row=0, column=1, sticky='w', pady=2)
        
        ttk.Label(rec_frame, text="참조 (CC):", style='Card.TLabel', width=10).grid(row=1, column=0, sticky='w')
        self.lbl_cc_list = ttk.Label(rec_frame, text="등록된 참조자 없음", style='Card.TLabel', foreground=COLORS['secondary'])
        self.lbl_cc_list.grid(row=1, column=1, sticky='w', pady=2)
        
        # 3. Action Buttons
        btn_card = ttk.Frame(self.tab_draft, style='Card.TFrame', padding=20)
        btn_card.pack(fill='x', pady=(10, 0))
        
        self.btn_outlook = ttk.Button(btn_card, text=" 📧 CREATE OUTLOOK DRAFT (아웃룩 메일 자동 생성) ", style='Action.TButton', command=self.create_outlook_draft)
        self.btn_outlook.pack(fill='x', ipady=8)
        
        ttk.Button(btn_card, text=" 🔄 데이터 & 그래프 새로고침 ", style='TButton', command=self.refresh_stats).pack(fill='x', pady=(10, 0))

    def refresh_stats(self):
        self.stats = get_daily_report_stats()
        
        # Update summary labels
        self.lbl_qc_overdue.config(text=f"QC Overdue: {self.stats['qc_rate']:.1f}% ({self.stats['qc_overdue']}/{self.stats['qc_total']}대)")
        self.lbl_armgc_overdue.config(text=f"ARMGC Overdue: {self.stats['armgc_rate']:.1f}% ({self.stats['armgc_overdue']}/{self.stats['armgc_total']}대)")
        self.lbl_rm_count.config(text=f"Active RM: {len(self.stats['rm_list'])}건")

    # =========================================================================
    # TAB 2: Recipient Manager (수신자 주소록 관리)
    # =========================================================================
    def build_recipients_tab(self):
        self.selected_recipient_id = None
        
        # Top Input Panel
        input_card = ttk.Frame(self.tab_recipients, style='Card.TFrame', padding=15)
        input_card.pack(fill='x', pady=(0, 15))
        
        ttk.Label(input_card, text="Email Recipient Editor (수신자 추가 및 정보 수정)", style='CardHeader.TLabel').grid(row=0, column=0, columnspan=6, sticky='w', pady=(0, 10))
        
        ttk.Label(input_card, text="구분 (TO/CC)", style='Card.TLabel').grid(row=1, column=0, sticky='w', padx=5)
        ttk.Label(input_card, text="이름 / 직함", style='Card.TLabel').grid(row=1, column=1, sticky='w', padx=5)
        ttk.Label(input_card, text="이메일 주소", style='Card.TLabel').grid(row=1, column=2, sticky='w', padx=5)
        
        self.rec_type_var = tk.StringVar(value='TO')
        self.combo_type = ttk.Combobox(input_card, textvariable=self.rec_type_var, values=['TO', 'CC'], width=8, state='readonly')
        self.combo_type.grid(row=2, column=0, padx=5, pady=5, sticky='w')
        
        self.rec_name_var = tk.StringVar()
        self.entry_name = ttk.Entry(input_card, textvariable=self.rec_name_var, width=20)
        self.entry_name.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        
        self.rec_email_var = tk.StringVar()
        self.entry_email = ttk.Entry(input_card, textvariable=self.rec_email_var, width=32)
        self.entry_email.grid(row=2, column=2, padx=5, pady=5, sticky='ew')
        
        self.btn_add_rec = ttk.Button(input_card, text="➕ 신규 추가", style='Action.TButton', command=self.add_recipient)
        self.btn_add_rec.grid(row=2, column=3, padx=5, pady=5)
        
        self.btn_edit_rec = ttk.Button(input_card, text="✏️ 선택 수정", style='TButton', command=self.update_recipient)
        self.btn_edit_rec.grid(row=2, column=4, padx=5, pady=5)
        
        input_card.columnconfigure(1, weight=1)
        input_card.columnconfigure(2, weight=2)
        
        # Recipients Table Card
        table_card = ttk.Frame(self.tab_recipients, style='Card.TFrame', padding=15)
        table_card.pack(fill='both', expand=True)
        
        # Treeview
        columns = ('ID', 'Type', 'Name', 'Email')
        self.rec_tree = ttk.Treeview(table_card, columns=columns, show='headings', selectmode='browse')
        
        self.rec_tree.heading('ID', text='ID')
        self.rec_tree.column('ID', width=0, stretch=tk.NO)
        
        self.rec_tree.heading('Type', text='구분 (TO/CC)')
        self.rec_tree.column('Type', width=100, anchor='center')
        
        self.rec_tree.heading('Name', text='이름 / 직함')
        self.rec_tree.column('Name', width=150, anchor='w')
        
        self.rec_tree.heading('Email', text='이메일 주소')
        self.rec_tree.column('Email', width=350, anchor='w')
        
        scrollbar = ttk.Scrollbar(table_card, orient='vertical', command=self.rec_tree.yview)
        self.rec_tree.configure(yscrollcommand=scrollbar.set)
        
        self.rec_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Treeview Selection Event Binding
        self.rec_tree.bind('<<TreeviewSelect>>', self.on_recipient_select)
        
        # Controls
        ctrl_frame = ttk.Frame(self.tab_recipients, style='Main.TFrame')
        ctrl_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(ctrl_frame, text="🔄 구분 (TO ↔ CC) 원클릭 전환", style='TButton', command=self.toggle_recipient_type).pack(side='left')
        ttk.Button(ctrl_frame, text="❌ 선택 수신자 삭제", style='TButton', command=self.delete_recipient).pack(side='right')

    def on_recipient_select(self, event=None):
        selected = self.rec_tree.selection()
        if not selected:
            return
        item = self.rec_tree.item(selected[0])
        values = item['values']
        self.selected_recipient_id = values[0]
        raw_type = str(values[1]).split(' ')[0] # Extract 'TO' or 'CC' from 'TO (수신)'
        self.rec_type_var.set(raw_type)
        self.rec_name_var.set(str(values[2]))
        self.rec_email_var.set(str(values[3]))

    def load_recipients(self):
        self.selected_recipient_id = None
        for item in self.rec_tree.get_children():
            self.rec_tree.delete(item)
            
        data = get_email_recipients()
        
        to_str_list = []
        cc_str_list = []
        
        # Load TO
        for r in data['TO']:
            self.rec_tree.insert('', 'end', values=(r['id'], 'TO (수신)', r['name'], r['email']))
            display_name = f"{r['name']} <{r['email']}>" if r['name'] else r['email']
            to_str_list.append(display_name)
            
        # Load CC
        for r in data['CC']:
            self.rec_tree.insert('', 'end', values=(r['id'], 'CC (참조)', r['name'], r['email']))
            display_name = f"{r['name']} <{r['email']}>" if r['name'] else r['email']
            cc_str_list.append(display_name)
            
        # Update tab 1 labels
        self.to_emails = [r['email'] for r in data['TO']]
        self.cc_emails = [r['email'] for r in data['CC']]
        
        self.lbl_to_list.config(text=", ".join(to_str_list) if to_str_list else "등록된 수신자 없음")
        self.lbl_cc_list.config(text=", ".join(cc_str_list) if cc_str_list else "등록된 참조자 없음")

    def add_recipient(self):
        name = self.rec_name_var.get().strip()
        email = self.rec_email_var.get().strip()
        type_val = self.rec_type_var.get()
        
        if not email or '@' not in email:
            messagebox.showwarning("입력 오류", "올바른 이메일 주소를 입력해 주세요.")
            return
            
        add_email_recipient(name, email, type_val)
        self.rec_name_var.set("")
        self.rec_email_var.set("")
        self.load_recipients()
        messagebox.showinfo("성공", "수신자가 저장되었습니다.")

    def update_recipient(self):
        if not hasattr(self, 'selected_recipient_id') or not self.selected_recipient_id:
            messagebox.showwarning("선택 오류", "수정할 수신자를 아래 목록에서 먼저 선택해 주세요.")
            return
            
        name = self.rec_name_var.get().strip()
        email = self.rec_email_var.get().strip()
        type_val = self.rec_type_var.get()
        
        if not email or '@' not in email:
            messagebox.showwarning("입력 오류", "올바른 이메일 주소를 입력해 주세요.")
            return
            
        update_email_recipient(self.selected_recipient_id, name, email, type_val)
        self.rec_name_var.set("")
        self.rec_email_var.set("")
        self.load_recipients()
        messagebox.showinfo("성공", "수신자 정보가 수정되었습니다.")

    def toggle_recipient_type(self):
        selected = self.rec_tree.selection()
        if not selected:
            messagebox.showwarning("선택 오류", "구분을 전환할 수신자를 목록에서 선택해 주세요.")
            return
            
        item = self.rec_tree.item(selected[0])
        values = item['values']
        r_id = values[0]
        r_name = values[2]
        r_email = values[3]
        current_type = str(values[1]).split(' ')[0]
        new_type = 'CC' if current_type == 'TO' else 'TO'
        
        update_email_recipient(r_id, r_name, r_email, new_type)
        self.load_recipients()
        messagebox.showinfo("성공", f"'{r_name}' 수신 구분이 [{new_type}]로 변경되었습니다.")

    def delete_recipient(self):
        selected = self.rec_tree.selection()
        if not selected:
            messagebox.showwarning("선택 오류", "삭제할 수신자를 선택해 주세요.")
            return
            
        item = self.rec_tree.item(selected[0])
        r_id = item['values'][0]
        r_name = item['values'][2]
        
        if messagebox.askyesno("삭제 확인", f"'{r_name}' 수신자를 주소록에서 삭제하시겠습니까?"):
            delete_email_recipient(r_id)
            self.load_recipients()
            messagebox.showinfo("성공", "수신자가 삭제되었습니다.")

    # =========================================================================
    # CREATE OUTLOOK DRAFT ACTION
    # =========================================================================
    def create_outlook_draft(self):
        self.refresh_stats()
        
        if not self.to_emails and not self.cc_emails:
            if not messagebox.askyesno("수신자 확인", "등록된 이메일 수신자가 없습니다. 수신자 없이 아웃룩 메일을 생성하시겠습니까?"):
                self.notebook.select(self.tab_recipients)
                return

        # Show status
        self.btn_outlook.config(state='disabled', text=" ⏳ 차트 및 메일 생성 중... ")
        self.update_idletasks()
        
        try:
            # 1. Generate QC Chart Image
            qc_chart_path = ReportGenerator.generate_chart(
                self.stats['qc_data'],
                "QC Crane Overdue Status",
                self.stats['qc_overdue'],
                self.stats['qc_total'],
                self.stats['qc_rate'],
                "qc_overdue_chart.png"
            )
            
            # 2. Generate ARMGC Chart Image
            armgc_chart_path = ReportGenerator.generate_chart(
                self.stats['armgc_data'],
                "ARMGC Crane Overdue Status",
                self.stats['armgc_overdue'],
                self.stats['armgc_total'],
                self.stats['armgc_rate'],
                "armgc_overdue_chart.png"
            )
            
            # 3. Generate Monthly Calendar Image
            cal_img_path = ReportGenerator.generate_calendar_image(
                self.stats['year'],
                self.stats['month'],
                self.stats['calendar_assignments'],
                "monthly_pms_calendar.png"
            )
            
            # 4. Build HTML Body with custom title
            html_body = ReportGenerator.build_html_body(self.stats, custom_title=self.subject_var.get())
            
            # 5. CID Image Mapping
            image_map = {
                'qc_chart': qc_chart_path,
                'armgc_chart': armgc_chart_path,
                'cal_image': cal_img_path
            }
            
            # 6. Create Outlook Draft
            success, msg = ReportGenerator.create_outlook_draft(
                self.to_emails,
                self.cc_emails,
                self.subject_var.get(),
                html_body,
                image_map
            )
            
            if success:
                messagebox.showinfo("아웃룩 연동 성공", "아웃룩 메일 작성 창이 성공적으로 생성되었습니다!\n\n아웃룩 화면에서 최종 확인 후 보내기를 누르세요.")
            else:
                messagebox.showerror("오류", msg)
                
        except Exception as e:
            messagebox.showerror("생성 오류", f"보고서 생성 중 오류 발생: {str(e)}")
        finally:
            self.btn_outlook.config(state='normal', text=" 📧 CREATE OUTLOOK DRAFT (아웃룩 메일 자동 생성) ")
