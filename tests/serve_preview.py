"""Ten-minute local browser preview, isolated from real maintenance data."""
from datetime import date, timedelta
import os
from pathlib import Path
import tempfile
import threading
from ACSP import database, pms
from ACSP.pms_server import PMSService

with tempfile.TemporaryDirectory() as folder:
    os.environ['ACSP_DB_PATH'] = str(Path(folder) / 'preview.db')
    database.init_database()
    for equipment in range(101, 108):
        for index, task in enumerate(pms.TASKS):
            age = 10 + (equipment - 101) * 6 + index
            pms.save_record(equipment, task, (date.today()-timedelta(days=age)).isoformat(), '테스트 작업자', '브라우저 검증용 임시 데이터')
    service = PMSService()
    service.start(host='127.0.0.1', port=18765)
    print(f'Preview: http://127.0.0.1:{service.port} Code: {service.access_code}', flush=True)
    try:
        threading.Event().wait(600)
    finally:
        service.stop()
