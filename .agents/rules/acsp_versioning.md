# ACSP 버전 관리 규칙

## 버전 파일 위치
- `C:\Users\baewoong.kim\.gemini\ACSPV2.0\ACSP\version.py`

## 버전 체계 (Semantic Versioning)
- **Major (v X.0.0)**: 전체 구조 변경, DB 스키마 변경, 대규모 신규 기능
- **Minor (v 1.X.0)**: 신규 기능 추가, UI 탭 추가, 새 모듈 생성
- **Patch (v 1.4.X)**: 버그 수정, 스타일/레이아웃 조정, 텍스트 변경 등 소규모 수정

## 버전업 의무 규칙
> ACSP 프로그램 소스 코드를 수정하는 모든 작업 시, 반드시 아래 절차를 따른다:

1. **`version.py` 수정** — `__version__` 숫자를 변경 내용에 맞게 올린다.
2. **VERSION HISTORY 주석 추가** — 변경 내용을 한 줄 요약으로 히스토리에 추가한다.
3. **`app.py` 타이틀** — `app.py`는 `version.py`에서 `__version__`을 import하므로 자동 반영된다.
4. **PyInstaller 재빌드** — `pyinstaller --clean -y ACSP.spec` 실행으로 `dist/ACSP.exe`를 재생성한다.
5. **Git 커밋/푸시** — 커밋 메시지에 버전 번호를 반드시 포함한다. 예: `git commit -m "v1.4.3: <변경내용>"`

## 예시
```
# version.py 수정 예시
#   v1.4.3  - ARMGC 그래프 세로 배치로 변경
__version__ = "1.4.3"

# 커밋 메시지 예시
git commit -m "v1.4.3: ARMGC chart moved below QC chart"
```
