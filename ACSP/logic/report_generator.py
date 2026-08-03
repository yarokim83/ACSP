import os
import tempfile
import calendar
from datetime import datetime
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import win32com.client

# Set Korean font support for matplotlib on Windows
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

class ReportGenerator:
    @staticmethod
    def generate_chart(data, title, overdue_count, total_count, rate, filename):
        """Generates an optimized bar chart image matching the user's report style."""
        fig, ax = plt.subplots(figsize=(8, 3.0), dpi=95)
        
        crane_ids = [str(d['id']) for d in data]
        days_passed = [d['days_passed'] for d in data]
        
        # Color bar: Red if > 45 days, SkyBlue (#62c2e6) otherwise matching screenshot
        colors = ['#FF0000' if d > 45 else '#62c2e6' for d in days_passed]
        
        bars = ax.bar(crane_ids, days_passed, color=colors, width=0.55)
        
        # Draw 45 Days Limit Line (dashed orange)
        ax.axhline(y=45, color='#FFA500', linestyle=':', linewidth=1.2)
        ax.text(len(crane_ids)-0.5, 46, '45 Days Limit', color='#FFA500', fontsize=8, fontweight='bold', ha='right')
        
        # Y-Axis Limits & Style
        max_y = max(max(days_passed, default=50), 60) + 15
        ax.set_ylim(0, max_y)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#94a3b8')
        ax.spines['bottom'].set_color('#94a3b8')
        ax.tick_params(colors='#334155', labelsize=8)
        
        plt.xticks(rotation=45 if len(crane_ids) > 20 else 0, fontsize=7)
        
        # Values on top of bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{height}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 2),
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=7, fontweight='bold', color='#1e293b')
                            
        # Overdue Rate Badge Box matching exact screenshot style
        rate_text = f"Overdue Rate: {rate:.1f}% ({overdue_count}대/{total_count}대)"
        ax.text(0.98, 0.88, rate_text, transform=ax.transAxes, fontsize=10,
                fontweight='bold', color='#FF0000', ha='right', va='top',
                bbox=dict(boxstyle='square,pad=0.4', facecolor='white', edgecolor='#0000FF', linewidth=1.5))
                
        ax.grid(axis='y', linestyle=':', alpha=0.3)
        plt.tight_layout()
        
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, filename)
        plt.savefig(out_path, dpi=95, bbox_inches='tight')
        plt.close(fig)
        return out_path

    @staticmethod
    def generate_calendar_image(year, month, assignments, filename):
        """Generates an optimized Monthly PMS Calendar Image without text overlap."""
        fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=95)
        ax.axis('off')
        
        cal = calendar.monthcalendar(year, month)
        days_header = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        
        rows = len(cal) + 1
        cols = 7
        
        # Header title placed high at y=0.96 so it never overlaps day names
        title_str = f"{year}년 {month:02d}월"
        ax.text(0.5, 0.96, title_str, transform=ax.transAxes,
                fontsize=15, fontweight='bold', ha='center', va='top', color='#0f172a')
                
        # Lower table_top to 0.78 to guarantee ample space below title
        table_top = 0.78
        cell_width = 1.0 / cols
        cell_height = table_top / rows
        
        # Draw Day Names Header Row
        for col_idx, day_name in enumerate(days_header):
            x = col_idx * cell_width
            y = table_top
            color = '#FF0000' if col_idx == 0 else ('#0000FF' if col_idx == 6 else '#0f172a')
            
            # Header background fill
            ax.add_patch(patches.Rectangle((x, y), cell_width, cell_height, fill=True, facecolor='#f8fafc', edgecolor='#cbd5e1', lw=0.8))
            ax.text(x + cell_width/2, y + cell_height/2, day_name,
                    fontsize=10, fontweight='bold', ha='center', va='center', color=color)
            
        # Draw Calendar Days & Assigned Cranes
        for row_idx, week in enumerate(cal):
            y = table_top - (row_idx + 1) * cell_height
            for col_idx, day in enumerate(week):
                x = col_idx * cell_width
                ax.add_patch(patches.Rectangle((x, y), cell_width, cell_height, fill=False, edgecolor='#cbd5e1', lw=0.8))
                
                if day != 0:
                    day_color = '#FF0000' if col_idx == 0 else ('#0000FF' if col_idx == 6 else '#0f172a')
                    # Day number
                    ax.text(x + 0.1 * cell_width, y + cell_height - 0.22 * cell_height, str(day),
                            fontsize=9.5, fontweight='bold', ha='left', va='top', color=day_color)
                            
                    # Assigned cranes below day number
                    if day in assignments:
                        cranes = assignments[day]
                        cranes_text = "\n".join(cranes[:3])
                        if len(cranes) > 3:
                            cranes_text += f"\n+{len(cranes)-3}"
                        ax.text(x + cell_width/2, y + cell_height*0.35, cranes_text,
                                fontsize=7.5, color='#0284c7', fontweight='bold', ha='center', va='center')
                                
        plt.tight_layout()
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, filename)
        plt.savefig(out_path, dpi=95, bbox_inches='tight')
        plt.close(fig)
        return out_path

    @staticmethod
    def build_html_body(stats, custom_title=None):
        """Constructs HTML body with 10pt font size inside tables, ultra-compact cell height, and customizable title."""
        
        today = datetime.now()
        weekdays_korean = ['월', '화', '수', '목', '금', '토', '일']
        weekday_str = weekdays_korean[today.weekday()]
        date_str_short = f"{today.month}/{today.day}, {weekday_str}"
        
        if custom_title and custom_title.strip():
            header_title_line = f"{custom_title.strip()} 및 정비실적을 송부 드립니다."
        else:
            header_title_line = f"기술팀 일일 정비계획({date_str_short}) 및 정비실적을 송부 드립니다."

        # Working days calculation for target
        _, last_day = calendar.monthrange(today.year, today.month)
        working_days = sum(1 for d in range(1, last_day + 1) if datetime(today.year, today.month, d).weekday() < 5)
        target_pms_count = working_days # 1대 / Working day
        actual_pms_count = sum(len(cranes) for cranes in stats['calendar_assignments'].values())
        pms_percent = (actual_pms_count / target_pms_count * 100) if target_pms_count > 0 else 0
        
        font_style = "font-family:'Malgun Gothic', '맑은 고딕', Arial, sans-serif; font-size:11pt; color:#111111; line-height:1.6;"
        # Set table cell font size strictly to 10pt with ultra-compact height & line-height 1.0
        cell_font = "font-family:'Malgun Gothic', '맑은 고딕', sans-serif; font-size:10pt; line-height:1.0; height:18px;"

        # RM Table Rows HTML (Compact width 650px, soft pink background for active RM items, padding 2px 4px)
        rm_rows_html = ""
        if stats['rm_list']:
            for rm in stats['rm_list']:
                rm_rows_html += f"""
                <tr style="text-align:center; background-color:#fde8e8; color:#9b1c1c; height:18px;">
                    <td style="padding:2px 4px; height:18px; border:1px solid #f87171; {cell_font}">{rm['failure_date']}</td>
                    <td style="padding:2px 4px; height:18px; border:1px solid #f87171; {cell_font} text-align:left; font-weight:bold;">{rm['details']}</td>
                    <td style="padding:2px 4px; height:18px; border:1px solid #f87171; {cell_font}">{rm['rm_request_date']}</td>
                    <td style="padding:2px 4px; height:18px; border:1px solid #f87171; {cell_font} font-weight:bold;">{rm['elapsed_days']}</td>
                    <td style="padding:2px 4px; height:18px; border:1px solid #f87171; {cell_font} text-align:left;">{rm['remark']}</td>
                </tr>
                """
        else:
            rm_rows_html = f"""
            <tr style="text-align:center; background-color:#ffffff; height:18px;">
                <td colspan="5" style="padding:3px 4px; height:18px; border:1px solid #cbd5e1; {cell_font} color:#64748b;">특이 RM 요청 List 없음</td>
            </tr>
            """

        # Overdue Rate History Table HTML (Ultra-compact vertical cell height padding: 1px 3px, height: 18px, font-size: 10pt)
        # Highlight current month column with soft blue background for instant visual clarity
        history_qc = stats.get('history_qc', {})
        history_armgc = stats.get('history_armgc', {})

        months_headers_list = []
        qc_trend_cells_list = []
        armgc_trend_cells_list = []
        
        for m in range(1, today.month + 1):
            is_curr = (m == today.month)
            th_style = f"background-color:#dbeafe; color:#1e40af; font-weight:bold;" if is_curr else "background-color:#f1f5f9; color:#0f172a;"
            td_style = f"background-color:#eff6ff; font-weight:bold; color:#1e40af;" if is_curr else ""
            
            months_headers_list.append(f'<th style="padding:1px 3px; height:18px; border:1px solid #334155; width:48px; {cell_font} {th_style} text-align:center;">{m} 월</th>')
            qc_trend_cells_list.append(f'<td style="padding:1px 3px; height:18px; border:1px solid #334155; {cell_font} {td_style} text-align:center;">{history_qc.get(m, round(stats["qc_rate"]))}%</td>')
            armgc_trend_cells_list.append(f'<td style="padding:1px 3px; height:18px; border:1px solid #334155; {cell_font} {td_style} text-align:center;">{history_armgc.get(m, round(stats["armgc_rate"]))}%</td>')

        months_headers = "".join(months_headers_list)
        qc_trend_cells = "".join(qc_trend_cells_list)
        armgc_trend_cells = "".join(armgc_trend_cells_list)

        font_title = "font-family:'Malgun Gothic', '맑은 고딕', sans-serif; font-size:11.5pt; font-weight:bold; color:#1e3a8a;"
        
        qc_pct_str = f'<span style="color:#dc2626; font-weight:bold;">{round(stats["qc_rate"])}%</span>'
        armgc_pct_str = f'<span style="color:#dc2626; font-weight:bold;">{round(stats["armgc_rate"])}%</span>'

        html = f"""
        <html>
        <body style="{font_style} margin:20px;">
            
            <p style="{font_style} margin-bottom:12px;">수신자 제위</p>
            
            <p style="{font_style} margin-bottom:18px;">{header_title_line}</p>
            
            <!-- 1) RM 요청 List -->
            <p style="{font_title} margin-top:16px; margin-bottom:6px;">1) RM 요청 List</p>
            <div style="width:650px; margin-bottom:18px;">
                <table style="width:650px; border-collapse:collapse; {cell_font}">
                    <thead>
                        <tr style="background-color:#94a3b8; color:#0f172a; font-weight:bold; text-align:center; height:18px;">
                            <th style="padding:2px 4px; height:18px; border:1px solid #64748b; width:125px; {cell_font}">고장 발생(확인)일</th>
                            <th style="padding:2px 4px; height:18px; border:1px solid #64748b; width:210px; {cell_font}">고장내용</th>
                            <th style="padding:2px 4px; height:18px; border:1px solid #64748b; width:90px; {cell_font}">RM 요청일</th>
                            <th style="padding:2px 4px; height:18px; border:1px solid #64748b; width:50px; {cell_font}">경과일</th>
                            <th style="padding:2px 4px; height:18px; border:1px solid #64748b; width:175px; {cell_font}">Remark</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rm_rows_html}
                    </tbody>
                </table>
            </div>

            <!-- 2) 일일작업 계획 -->
            <p style="{font_title} margin-top:16px; margin-bottom:18px;">2) 일일작업 계획 – 첨부 참조</p>

            <!-- 3) Overdue 현황 -->
            <p style="{font_title} margin-top:16px; margin-bottom:4px;">3) Overdue 현황 – 아래표 참조</p>
            <p style="{font_style} margin:2px 0 2px 20px;">- QC : {qc_pct_str} ({stats['qc_total']}대中 {stats['qc_overdue']}대)</p>
            <p style="{font_style} margin:2px 0 6px 20px;">- ARMGC : {armgc_pct_str} ({stats['armgc_total']}대中 {stats['armgc_overdue']}대)</p>
            <p style="{cell_font} color:#475569; margin:0 0 18px 20px;">※ Overdue : 지정된 기간(1회/45일)內 PM 미시행 Rate</p>

            <!-- 4) 당월 PM ARMGC 배정 대수 & Overdue -->
            <p style="{font_title} margin-top:16px; margin-bottom:8px;">4) {today.month}월 PM ARMGC 배정 대수 : {actual_pms_count}대 / Target {target_pms_count}대(1대/Working day)</p>
            
            <div style="margin-left:20px; width:650px;">
                <p style="{font_style} font-weight:bold; margin-bottom:4px;">● 월별 Overdue Rate</p>
                <table style="border-collapse:collapse; {cell_font} text-align:center; margin-bottom:18px; width:650px;">
                    <thead>
                        <tr style="background-color:#f1f5f9; font-weight:bold; height:18px;">
                            <th style="padding:1px 3px; height:18px; border:1px solid #334155; width:150px; text-align:center; {cell_font}">구분</th>
                            {months_headers}
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="height:18px;">
                            <td style="padding:1px 3px; height:18px; border:1px solid #334155; text-align:left; padding-left:10px; font-weight:bold; {cell_font}">Overdue Rate QC</td>
                            {qc_trend_cells}
                        </tr>
                        <tr style="height:18px;">
                            <td style="padding:1px 3px; height:18px; border:1px solid #334155; text-align:left; padding-left:10px; font-weight:bold; {cell_font}">Overdue Rate ARMGC</td>
                            {armgc_trend_cells}
                        </tr>
                    </tbody>
                </table>

                <p style="{font_style} font-weight:bold; margin-bottom:10px;">● QC, ARMGC - Overdue 현황</p>
                <p style="margin:0 0 15px 0; padding:0; clear:both; width:650px;">
                    <img src="cid:qc_chart" width="650" style="width:650px; max-width:650px; height:auto; display:block; clear:both;">
                </p>
                <p style="margin:0 0 15px 0; padding:0; clear:both; width:650px;">
                    <img src="cid:armgc_chart" width="650" style="width:650px; max-width:650px; height:auto; display:block; clear:both;">
                </p>

                <p style="{font_style} margin:14px 0 20px 0;">- PMS 장비 배정 실적 : {today.month}월 PMS 장비 배정 ARMGC Target : {target_pms_count}대 / 실적 {actual_pms_count}대 ({pms_percent:.0f}%)</p>
            </div>

            <!-- 5) 당월 PMS 배정 달력 -->
            <div style="margin-left:20px; width:650px; margin-bottom:20px; clear:both;">
                <p style="margin:0 0 15px 0; padding:0; clear:both; width:650px;">
                    <img src="cid:cal_image" width="650" style="width:650px; max-width:650px; height:auto; display:block; clear:both;">
                </p>
            </div>

            <br>
            <p style="{font_style}">감사합니다.</p>
        </body>
        </html>
        """
        return html

    @staticmethod
    def create_outlook_draft(to_emails, cc_emails, subject, html_body, image_map):
        """Creates an Outlook Mail Item with inline images (CID) and opens composition window."""
        try:
            outlook = win32com.client.Dispatch('Outlook.Application')
            mail = outlook.CreateItem(0) # 0 = olMailItem
            
            mail.Subject = subject
            if to_emails:
                mail.To = "; ".join(to_emails) if isinstance(to_emails, list) else to_emails
            if cc_emails:
                mail.CC = "; ".join(cc_emails) if isinstance(cc_emails, list) else cc_emails
                
            for cid_name, file_path in image_map.items():
                if os.path.exists(file_path):
                    attachment = mail.Attachments.Add(file_path)
                    attachment.PropertyAccessor.SetProperty("http://schemas.microsoft.com/mapi/proptag/0x3712001E", cid_name)
                    
            mail.HTMLBody = html_body
            mail.Display() # Open Outlook compose window
            return True, "Outlook 메일 작성 창이 성공적으로 생성되었습니다."
        except Exception as e:
            return False, f"Outlook 연동 오류: {str(e)}"
