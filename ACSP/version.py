# ACSP Version Management
# -------------------------
# VERSION HISTORY:
#   v1.0.0  - Initial release: Equipment PMS scheduler, RM list, Overdue graph
#   v1.1.0  - RM list delete bug fix (sqlite_master-based init check)
#   v1.2.0  - Daily Report email automation (Option A / Outlook win32com)
#   v1.2.1  - Recipient address book UI (TO/CC management tab)
#   v1.3.0  - Email layout: compact table, 10pt font, customizable title
#   v1.3.1  - Calendar image overlap fix (title vs day header gap)
#   v1.3.2  - Monthly Overdue Rate: last-day-of-month basis for past months
#   v1.4.0  - Legibility improvements: navy titles, red % highlights, current month column highlight
#   v1.4.1  - Ultra-compact table row height (18px, line-height 1.0)
#   v1.4.2  - ARMGC chart moved below QC chart (vertical stacking)
#   v1.4.3  - Added version rule & versioning system
#   v1.4.4  - Fix: win32com lazy import (Daily Report 버튼 무반응 근본 원인 해결)
#   v1.4.6  - Email chart stacked bar style (blue 0~45, red above 45) matching program graph
#   v1.4.7  - Fix: absolute DB path resolution & safe null date parsing for existing databases
#   v1.4.8  - Performance: instant startup optimization (lazy loading submodules + excluding unused packages)
#   v1.4.9  - Fix: restore optimize=0 to prevent numpy 2.x docstring stripping crash
#   v1.5.0  - Feature: Add default 25 team email recipients seed to database
#   v1.5.1  - Change: Update 25 default recipients type from TO to CC
#   v1.5.2  - Feature: Add recipient info editing & TO/CC toggle buttons in address book UI
#   v1.5.3  - Fix: Email calendar image weekday alignment fix (set firstweekday=Sunday)
#   v1.5.4  - Fix: Email calendar image exact match to program UI calendar (QC Red, ARMGC Blue, Today circle)
#   v1.5.5  - Feature: Display tomorrow's date & weekday in default email subject & body title
#   v2.0.0  - Major: Rebranded application name to CRANEON with CraneOn logo integration

__version__ = "2.0.0"
__app_name__ = "CRANEON"
__full_name__ = "CraneOn Schedule & Management"

