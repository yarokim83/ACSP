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
        """Generates a bar chart image matching the ACSP style."""
        fig, ax = plt.subplots(figsize=(10, 4.5), dpi=150)
        
        crane_ids = [str(d['id']) for d in data]
        days_passed = [d['days_passed'] for d in data]
        
        # Color bar: Red if > 45 days, Blue otherwise
        colors = ['#FF0000' if d > 45 else '#87CEEB' for d in days_passed]
        
        bars = ax.bar(crane_ids, days_passed, color=colors, width=0.6)
        
        # Draw 45 Days Limit Line
        ax.axhline(y=45, color='#FFA500', linestyle='--', linewidth=1.5, label='45 Days Limit')
        
        # Y-Axis Limits & Labels
        max_y = max(max(days_passed, default=50), 60) + 15
        ax.set_ylim(0, max_y)
        ax.set_ylabel('Days Lapsed', fontsize=9)
        plt.xticks(rotation=45 if len(crane_ids) > 20 else 0, fontsize=8)
        
        # Values on top of bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{height}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=7, fontweight='bold')
                            
        # Overdue Rate Badge Box
        rate_text = f"Overdue Rate: {rate:.1f}% ({overdue_count}대/{total_count}대)"
        ax.text(0.98, 0.92, rate_text, transform=ax.transAxes, fontsize=11,
                fontweight='bold', color='#FF0000', ha='right', va='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#FF0000', linewidth=2))
                
        ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
        ax.grid(axis='y', linestyle=':', alpha=0.5)
        plt.tight_layout()
        
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, filename)
        plt.savefig(out_path, dpi=150)
        plt.close(fig)
        return out_path

    @staticmethod
    def generate_calendar_image(year, month, assignments, filename):
        """Generates a Monthly PMS Calendar Image."""
        fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
        ax.axis('off')
        
        # Calendar matrix
        cal = calendar.monthcalendar(year, month)
        days_header = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        
        # Grid parameters
        rows = len(cal) + 1
        cols = 7
        
        # Header title
        title_str = f"{year}년 {month:02d}월"
        ax.text(0.5, 0.95, f"◀   {title_str}   ▶", transform=ax.transAxes,
                fontsize=16, fontweight='bold', ha='center', va='top', color='#1e293b')
                
        table_top = 0.85
        cell_width = 1.0 / cols
        cell_height = table_top / rows
        
        # Draw Day Names
        for col_idx, day_name in enumerate(days_header):
            x = col_idx * cell_width
            y = table_top
            color = '#FF0000' if col_idx == 0 else ('#0000FF' if col_idx == 6 else '#000000')
            ax.text(x + cell_width/2, y + cell_height/2, day_name,
                    fontsize=11, fontweight='bold', ha='center', va='center', color=color)
            ax.add_patch(patches.Rectangle((x, y), cell_width, cell_height, fill=False, edgecolor='#cbd5e1', lw=1))
            
        # Draw Calendar Days & Assigned Cranes
        for row_idx, week in enumerate(cal):
            y = table_top - (row_idx + 1) * cell_height
            for col_idx, day in enumerate(week):
                x = col_idx * cell_width
                ax.add_patch(patches.Rectangle((x, y), cell_width, cell_height, fill=False, edgecolor='#cbd5e1', lw=1))
                
                if day != 0:
                    day_color = '#FF0000' if col_idx == 0 else ('#0000FF' if col_idx == 6 else '#000000')
                    # Day number at top-left of cell
                    ax.text(x + 0.1 * cell_width, y + cell_height - 0.2 * cell_height, str(day),
                            fontsize=10, fontweight='bold', ha='left', va='top', color=day_color)
                            
                    # Assigned cranes below day number
                    if day in assignments:
                        cranes = assignments[day]
                        cranes_text = "\n".join(cranes[:3]) # Limit to top 3 for space
                        if len(cranes) > 3:
                            cranes_text += f"\n+{len(cranes)-3}"
                        ax.text(x + cell_width/2, y + cell_height*0.35, cranes_text,
                                fontsize=8, color='#0284c7', fontweight='bold', ha='center', va='center')
                                
        plt.tight_layout()
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, filename)
        plt.savefig(out_path, dpi=150)
        plt.close(fig)
        return out_path

    @staticmethod
    def build_html_body(stats):
        """Constructs HTML body matching the daily status email format."""
        
        # RM Table Rows HTML
        rm_rows_html = ""
        if stats['rm_list']:
            for rm in stats['rm_list']:
                rm_rows_html += f"""
                <tr style="text-align:center; background-color:#ffffff;">
                    <td style="padding:6px; border:1px solid #cbd5e1;">{rm['failure_date']}</td>
                    <td style="padding:6px; border:1px solid #cbd5e1; text-align:left;">{rm['details']}</td>
                    <td style="padding:6px; border:1px solid #cbd5e1;">{rm['rm_request_date']}</td>
                    <td style="padding:6px; border:1px solid #cbd5e1; color:#dc2626; font-weight:bold;">{rm['elapsed_days']}</td>
                    <td style="padding:6px; border:1px solid #cbd5e1; text-align:left;">{rm['remark']}</td>
                </tr>
                """
        else:
            rm_rows_html = """
            <tr style="text-align:center; background-color:#ffffff;">
                <td colspan="5" style="padding:10px; border:1px solid #cbd5e1; color:#64748b;">특이 RM 요청 건 없음</td>
            </tr>
            """

        html = f"""
        <html>
        <body style="font-family:'Malgun Gothic', Arial, sans-serif; color:#1e293b; line-height:1.6; margin:20px;">
            
            <p><strong>수신자 제위</strong></p>
            <p>기술팀 예방정비계획(<strong>{stats['today_str']}</strong>) 및 정비실적을 송부 드립니다.</p>
            
            <br>
            <h4 style="color:#0f172a; margin-bottom:8px;">1) RM 요청 건</h4>
            <table style="width:100%; max-width:850px; border-collapse:collapse; font-size:13px;">
                <thead>
                    <tr style="background-color:#e2e8f0; color:#0f172a; font-weight:bold; text-align:center;">
                        <th style="padding:8px; border:1px solid #cbd5e1; width:120px;">고장 발생(확인)일</th>
                        <th style="padding:8px; border:1px solid #cbd5e1;">고장내용</th>
                        <th style="padding:8px; border:1px solid #cbd5e1; width:110px;">RM 요청일</th>
                        <th style="padding:8px; border:1px solid #cbd5e1; width:70px;">경과일</th>
                        <th style="padding:8px; border:1px solid #cbd5e1;">Remark</th>
                    </tr>
                </thead>
                <tbody>
                    {rm_rows_html}
                </tbody>
            </table>

            <br>
            <h4 style="color:#0f172a; margin-bottom:8px;">2) 정비작업 계획</h4>
            <p style="margin-left:10px; font-size:13px;">- 첨부 및 아래 현황 참조</p>

            <br>
            <h4 style="color:#0f172a; margin-bottom:8px;">3) Overdue 현황 - 15일/월 기준</h4>
            <ul style="font-size:13px; margin-top:4px;">
                <li><strong>QC</strong> : <span style="color:#dc2626; font-weight:bold;">{stats['qc_rate']:.1f}%</span> (전체 {stats['qc_total']}대 중 {stats['qc_overdue']}대)</li>
                <li><strong>ARMGC</strong> : <span style="color:#dc2626; font-weight:bold;">{stats['armgc_rate']:.1f}%</span> (전체 {stats['armgc_total']}대 중 {stats['armgc_overdue']}대)</li>
            </ul>
            <p style="font-size:12px; color:#64748b; margin-left:10px;">※ Overdue : 지정된 기간(15일/월)내 PMS 미시행 Crane</p>

            <br>
            <h4 style="color:#0f172a; margin-bottom:8px;">4) 당월 PMS ARMGC 배정 대수 및 Overdue 현황</h4>
            <div style="margin-left:10px; margin-bottom:15px;">
                <img src="cid:qc_chart" style="max-width:850px; width:100%; height:auto; margin-bottom:15px; border:1px solid #e2e8f0; border-radius:8px;">
                <br>
                <img src="cid:armgc_chart" style="max-width:850px; width:100%; height:auto; border:1px solid #e2e8f0; border-radius:8px;">
            </div>

            <br>
            <h4 style="color:#0f172a; margin-bottom:8px;">5) 당월 PMS 배정 달력 ({stats['year']}년 {stats['month']:02d}월)</h4>
            <div style="margin-left:10px;">
                <img src="cid:cal_image" style="max-width:750px; width:100%; height:auto; border:1px solid #e2e8f0; border-radius:8px;">
            </div>

            <br><br>
            <p style="color:#64748b;">감사합니다.</p>
        </body>
        </html>
        """
        return html

    @staticmethod
    def create_outlook_draft(to_emails, cc_emails, subject, html_body, image_map):
        """
        Creates an Outlook Mail Item with inline images (CID) and opens the composition window.
        image_map: dict of {'cid_name': 'absolute_filepath'}
        """
        try:
            outlook = win32com.client.Dispatch('Outlook.Application')
            mail = outlook.CreateItem(0) # 0 = olMailItem
            
            mail.Subject = subject
            if to_emails:
                mail.To = "; ".join(to_emails) if isinstance(to_emails, list) else to_emails
            if cc_emails:
                mail.CC = "; ".join(cc_emails) if isinstance(cc_emails, list) else cc_emails
                
            # Add image attachments with CIDs
            for cid_name, file_path in image_map.items():
                if os.path.exists(file_path):
                    attachment = mail.Attachments.Add(file_path)
                    # Property PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001E"
                    attachment.PropertyAccessor.SetProperty("http://schemas.microsoft.com/mapi/proptag/0x3712001E", cid_name)
                    
            mail.HTMLBody = html_body
            mail.Display() # Open Outlook compose window
            return True, "Outlook 메일 작성 창이 정상적으로 생성되었습니다."
        except Exception as e:
            return False, f"Outlook 연동 오류: {str(e)}"
