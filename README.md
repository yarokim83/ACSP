# ACSP - Ai Crane Scheduler Program

A Python-based maintenance scheduling application for crane equipment.

## Features
- Dashboard with equipment status overview
- Sidebar with quick stats (Total, Overdue, Warning)
- Calendar view for maintenance history
- Add/Edit/Delete maintenance records from calendar
- Filter equipment by status

## Requirements
- Python 3.8+
- tkinter (included with Python)

## Run
```bash
python run.py
```

## 작업 완료 현황 (v4.0.0)

1. 왼쪽 **작업 완료 현황 → + 작업 등록**에서 작업명과 차수/기간을 등록합니다. 예: `비상정지 스위치 점검 / 2026년 10월`.
2. 작업별로 QC 12대와 ARMGC 38대의 대상 여부, 완료일, 작업자, 비고가 DB에 저장됩니다. 같은 작업을 다시 할 때는 새 차수로 등록하면 과거 실적이 유지됩니다.
3. 호기를 클릭하고 완료일·작업자·비고를 입력한 뒤 **완료 저장 / 수정**을 누릅니다.
4. **대상 제외 / 포함 모드**를 켜고 호기를 클릭하면 즉시 제외됩니다. 같은 호기를 다시 클릭하면 포함됩니다. 제외 여부는 현재 선택한 작업에만 적용됩니다.
5. 제외 호기는 `×`로 표시하고 완료율의 분모·분자에서 모두 뺍니다. 완료 실적이 있던 호기도 제외 시 실적을 보존하며 다시 포함하면 복원됩니다. 모든 호기가 제외되면 `대상 없음`으로 표시합니다.
6. **변경 이력**에서 완료 입력/수정/취소와 대상 제외/포함 기록을 확인합니다. **CSV 저장**은 현재 작업의 전체 호기와 제외 상태를 출력합니다.

작업 종류와 차수는 하나의 로컬 `acsp.db` 안에서 독립적으로 구분해 저장합니다. 새 버전 첫 실행 시 기존 v3 DB는 `backups/`에 자동 백업됩니다. 기존 QC PMS와는 별도의 작업 실적이며 이 새 메뉴의 입력·대상 관리는 관리 PC 프로그램에서 수행합니다. 기존 브라우저 QC PMS 입력 기능은 그대로 사용할 수 있습니다.

## QC PMS (v5.0.0 통합 복원)

- QC 101~112호기를 호기당 PMS 1개로 관리합니다. 장비현황은 QC 12행입니다.
- 최근 호기별 시행일 + 45일이 다음 예정일이며, 46일부터 지연입니다.
- QC 호기를 선택하고 완료 입력 시 시행일만 저장합니다. v5.0.1부터 작업자·비고 입력은 제거했으며, 기존 값은 날짜 수정 시에도 보존합니다.
- 장비현황·달력·그래프·Daily Report·브라우저 입력이 같은 호기별 이력을 사용합니다.
- 기존 `maintenance_history`와 장비의 정비일을 그대로 사용합니다. 기존 이력도 통합 PMS로 조회·수정 가능합니다.
- Front / Back / Gantry / H.B 기록은 원본 테이블에 보존합니다. PMS 시행 내역의 `분류별 보관 이력` 필터로 조회하며, 일부 작업을 전체 PMS 완료로 간주하지 않습니다.
- 최초 실행 전 DB를 자동 백업하고, 기존 호기별 이력에 작업자·비고·수정 버전 필드를 추가합니다. 이력 ID와 기존 날짜는 유지됩니다.
- 작업 완료 현황 대시보드의 작업별 DB 및 대상 제외 기능은 유지됩니다.

### 회사 네트워크에서 다른 PC로 입력하기

1. 관리 PC에서 `dist/CRANEON.exe`를 실행합니다. Python 실행 시에는 `python -m pip install -r requirements.txt` 후 `python run.py`를 실행합니다.
2. 왼쪽 **네트워크 입력 → 서버 시작**을 선택합니다. 기본 TCP 포트는 `8765`이며 변경할 수 있습니다.
3. 표시된 회사 LAN 주소(예: `http://관리PC의IPv4주소:8765`)와 접속 코드를 입력 담당자에게 안내합니다.
4. 다른 PC의 Edge/Chrome에서 해당 주소를 열고 코드를 입력합니다. Python이나 CRANEON을 설치할 필요가 없습니다.
5. **시행 실적 입력**에서 호기·시행일을 저장합니다. **PMS 시행 내역**에서 결과를 확인합니다. 관리 PC의 현황은 15초마다 갱신됩니다.
6. 프로그램을 닫거나 서버를 중지하면 접속이 종료됩니다. 서버 재시작 시 접속 코드가 바뀝니다. 네트워크 안내 창만 닫으면 서버는 계속 실행됩니다.

관리 PC를 켜 두고 절전 진입을 피하세요. 다른 PC에서 연결되지 않으면 `ipconfig`로 관리 PC의 회사 LAN IPv4 주소를 확인하고, 사내 IT 담당자를 통해 해당 TCP 포트의 사내망 접근을 허용하세요. VPN/가상 어댑터 등 여러 주소가 표시될 수 있습니다. 방화벽 규칙은 프로그램이 자동 변경하지 않습니다.

서버는 시작 버튼을 누른 경우에만 켜지며 접속 코드를 요구합니다. 기본 연결은 HTTP이므로 회사에서 허용한 내부망에서 사용하세요. 전송 암호화가 필요한 환경은 사내 HTTPS 프록시 뒤에 배치해야 합니다. 브라우저는 입력·조회만 지원하며 수정·삭제는 관리 PC에서 수행합니다.

### 데이터 위치 및 업그레이드

- 실행 파일은 **실행 파일 옆 `acsp.db`**, 소스 실행은 **프로젝트 루트 `acsp.db`**를 사용합니다. 두 파일은 별개이므로 실제 사용 중인 DB와 실행 위치를 유지하세요.
- 첫 v5 실행 시 기존 DB는 옆 `backups/`에 자동 백업된 후 통합 이력의 작업자·비고·수정 버전 필드를 추가합니다. 기존 ARMGC/QC 이력은 유지됩니다.
- NAS에서 사용하는 경우 실행 파일과 기존 `acsp.db`를 같은 공유폴더에 유지합니다. 프로그램이 DB를 로컬로 옮기거나 별도 복사본으로 전환하지 않습니다. 브라우저 입력을 사용할 때에는 관리 PC의 서버가 해당 DB를 사용합니다.
- 백업은 프로그램 종료 후 `acsp.db`를 복사하세요. 복구 시 프로그램을 종료한 뒤 해당 위치에 백업 DB를 복원합니다.
- `ACSP_DB_PATH` 환경 변수는 테스트용 별도 DB 또는 지정한 **로컬** DB 경로를 사용할 때만 설정합니다.

### 검증 및 실행 파일 빌드

```powershell
python -m unittest discover -s tests -v
python -m PyInstaller --clean -y ACSP.spec
```

빌드 결과는 `dist/CRANEON.exe`입니다. 테스트는 임시 DB를 사용하며 실제 정비 데이터를 변경하지 않습니다.

EXE 배포 전 `dist/CRANEON.exe --self-test-report build/report-check.json`을 실행하고 결과 JSON의 `ok: true`와 종료 코드 0을 확인합니다. 실제 번들 안에서 Daily Report 창, QC/ARMGC 차트, 달력 이미지와 HTML 생성을 검사합니다. 임시 DB만 사용하며 Outlook 실행이나 메일 발송은 하지 않습니다.

v4.0.8은 NAS 직접 실행용 단일 EXE를 유지하면서 사용하지 않는 AVIF/MFC/XML 보조 모듈을 제외합니다. 보고서는 NAS 연결 1회, 데이터 조회 3회(v5.0.0 기준)로 동일 시점의 데이터를 읽고 연결을 닫은 뒤 계산합니다. 매 조회마다 새로 읽으므로 다른 PC의 변경도 다음 새로고침에 반영됩니다. EXE 자체 검사는 작업 완료 저장·제외·복원과 Outlook 연동 모듈 로딩도 확인하며, 실제 메일 작성·발송은 수행하지 않습니다.

## Project Structure
```
ACSP/
  main.py           # Entry point (via module)
  database.py       # SQLite database handling
  ui/
    app.py          # Main application window
    calendar.py     # Calendar view components
    styles.py       # UI styling
  tools/
    import_legacy.py    # Import from legacy pms.db
    sync_equipment.py   # Sync equipment dates
run.py              # Simple entry point
```
