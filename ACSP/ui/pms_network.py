import socket
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser


class PMSNetworkWindow(tk.Toplevel):
    def __init__(self, parent, service):
        super().__init__(parent)
        self.service = service
        self.title('QC PMS · 회사 네트워크 입력')
        self.geometry('650x450')
        self.transient(parent)
        body = ttk.Frame(self, padding=20)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='다른 PC에서 브라우저로 PMS 입력', font=('맑은 고딕', 16, 'bold')).pack(anchor='w', pady=8)
        ttk.Label(body, text='1. 이 관리 PC에서 서버를 시작합니다.\n2. 다른 PC에 접속 주소와 코드를 전달합니다.\n3. 다른 PC의 브라우저에서 주소를 열고 코드를 입력합니다.\n\n관리 PC와 CRANEON이 켜져 있어야 입력할 수 있습니다.', justify='left').pack(anchor='w', pady=10)
        row = ttk.Frame(body)
        row.pack(fill='x')
        ttk.Label(row, text='포트').pack(side='left')
        self.port = tk.StringVar(value=str(service.port or 8765))
        ttk.Entry(row, textvariable=self.port, width=8).pack(side='left', padx=8)
        ttk.Button(row, text='서버 시작', command=self.start).pack(side='left', padx=5)
        ttk.Button(row, text='서버 중지', command=self.stop).pack(side='left', padx=5)
        ttk.Button(row, text='입력 화면 열기', command=self.open_browser).pack(side='left', padx=5)
        self.info = tk.Text(body, height=7, wrap='word', font=('맑은 고딕', 11))
        self.info.pack(fill='both', expand=True, pady=12)
        ttk.Label(body, text='접속이 안 되면 관리 PC의 IPv4 주소와 회사 방화벽의 해당 TCP 포트 허용 여부를 확인하세요.', wraplength=590).pack(anchor='w')
        self.refresh()

    def refresh(self):
        self.info.config(state='normal')
        self.info.delete('1.0', 'end')
        if self.service.running:
            try:
                addresses = sorted({r[4][0] for r in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET) if not r[4][0].startswith('127.')})
            except OSError:
                addresses = []
            urls = '\n'.join(f'http://{ip}:{self.service.port}' for ip in addresses)
            self.info.insert('end', f'서버 실행 중\n다른 PC 접속 주소 (회사 LAN 주소 선택):\n{urls or "ipconfig에서 IPv4 주소를 확인하세요."}\n접속 코드: {self.service.access_code}\n서버를 다시 시작하면 코드가 변경됩니다.')
        else:
            self.info.insert('end', '서버 중지 상태입니다. 서버 시작을 누르세요.')
        self.info.config(state='disabled')

    def start(self):
        try:
            port = int(self.port.get())
            if not 1024 <= port <= 65535:
                raise ValueError('포트는 1024~65535 사이로 입력하세요.')
            self.service.start(port=port)
            self.refresh()
        except Exception as exc:
            messagebox.showerror('서버 시작 실패', str(exc), parent=self)

    def stop(self):
        self.service.stop()
        self.refresh()

    def open_browser(self):
        if self.service.running:
            webbrowser.open(f'http://127.0.0.1:{self.service.port}')
        else:
            messagebox.showinfo('서버 중지', '먼저 서버를 시작하세요.', parent=self)
