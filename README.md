# ScreenAid Studio

ScreenAid Studio는 발표, 수업, 온라인 강의, 화면 시연을 위한 Windows 전용 화면 보조 도구입니다.
마우스 클릭 표시, 화면 그리기, 영역 캡처, 고정 화면, 실시간 영역 화면, 현재 화면 확대, Windows 기반 실시간 전체 화면 확대 기능을 제공합니다.

## 기본 정보

- 프로그램명: ScreenAid Studio
- 현재 배포 기준 버전: 0.2.1.2
- 운영체제: Windows 10 / Windows 11, 64bit
- 개발 언어: Python
- 라이선스: MIT License
- 저작권자: JunoSsam
- GitHub: [junossam/ScreenAid_Studio](https://github.com/junossam/ScreenAid_Studio)
- 프로그램 사이트: [junossam.github.io/ScreenAid_Studio](https://junossam.github.io/ScreenAid_Studio/)

## 개발 및 실행 환경

깨끗한 Python 환경에서 실행하려면 아래 버전을 권장합니다.

| 항목 | 기준 |
| --- | --- |
| Python | `>=3.12,<3.14` |
| 권장 Python | Python 3.12.x 또는 3.13.x 64bit |
| PySide6 | `6.8.3` 고정 |
| Windows | Windows 10 / Windows 11 |
| 아키텍처 | 64bit |
| DPI | Per Monitor DPI Aware V2 사용 |

필수 실행 의존성은 `requirements.txt`에서 확인할 수 있습니다.

```text
PySide6==6.8.3
```

Python 표준 라이브러리인 `ctypes`, `configparser`, `pathlib`, `dataclasses` 등을 적극 사용합니다.

선택 의존성은 `pyproject.toml`에 정의되어 있습니다.

| 그룹 | 패키지 | 용도 |
| --- | --- | --- |
| `capture` | `mss`, `Pillow` | 향후 고급 캡처/이미지 처리 검토용 |
| `dev` | `pytest`, `pytest-cov`, `ruff`, `mypy` | 테스트, 정적 검사, 개발 보조 |

## 개발 환경 설치

```powershell
cd D:\codex\ScreenAssistant
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Python 3.12를 사용할 경우:

```powershell
py -3.12 -m venv .venv
```

## 주요 기능

- 마우스 클릭 표시
- 화면 그리기: 펜, 형광펜, 직선, 사각형, 원, 화살표, 도장, 지우개
- 영역 캡처
- 마지막 캡처 파일 저장
- 고정 화면
- 실시간 영역 화면
- 현재 화면 확대 및 확대 화면 위 그리기
- Windows Magnification API 기반 실시간 전체 화면 확대
- 한국어/영어 UI
- 명령 모드 단축키
- 트레이 아이콘 상태 표시
- 휴대용 모드 설정 저장
- 사용자 설명서 열기

## 기본 단축키

전역 단축키:

| 단축키 | 동작 |
| --- | --- |
| `Ctrl + Alt + A` | 명령 모드 열기 |
| `Ctrl + Alt + E` | 클릭 효과 임시 표시/숨김 |

명령 모드에서 사용하는 기본 키:

| 키 | 동작 |
| --- | --- |
| `D` | 그리기 모드 토글 |
| `P` | 입력 통과 모드 |
| `C` | 그리기 전체 지우기 |
| `Z` | 그리기 실행 취소 |
| `Y` | 그리기 다시 실행 |
| `R` | 영역 캡처 |
| `L` | 마지막 영역 다시 캡처 |
| `I` | 마지막 캡처 파일로 저장 |
| `M` | 현재 모니터 캡처 |
| `V` | 전체 가상 화면 캡처 |
| `W` | 활성 창 캡처 |
| `K` | 영역 선택 후 고정 화면 열기 |
| `B` | 마지막 캡처 고정 |
| `G` | 실시간 영역 선택 |
| `X` | 실시간 화면 모두 닫기 |
| `F` | 현재 화면 확대 |
| `J` | 실시간 전체 화면 확대 |
| `S` | 설정창 열기 |
| `Space` | 전체 일시중지/재개 |
| `Esc` | 명령 모드 또는 확대 상태 닫기 |

단축키는 설정창에서 변경할 수 있습니다.

## 확대 기능 구분

| 기능 | 실행 | 설명 |
| --- | --- | --- |
| 현재 화면 확대 | `Ctrl + Alt + A` 후 `F` | 현재 화면을 캡처한 확대 화면입니다. 확대 중 `D`를 눌러 확대 화면 위에 그릴 수 있습니다. |
| 실시간 전체 화면 확대 | `Ctrl + Alt + A` 후 `J` | Windows Magnification API를 사용해 마우스 위치 주변을 실시간으로 확대합니다. |
| 실시간 영역 화면 | `Ctrl + Alt + A` 후 `G` | 사용자가 드래그한 영역을 별도 작은 창으로 계속 갱신합니다. |

실시간 전체 화면 확대의 입력 위치 보정은 Windows의 `MagSetInputTransform`을 사용합니다. 이 기능은 실행 환경의 UIAccess 권한 상태에 영향을 받을 수 있으므로, 포터블 EXE를 다른 PC에서 사용할 때는 실제 환경 테스트가 필요합니다.

## 설정 저장 위치

기본값은 휴대용 모드입니다.

- 휴대용 모드: 실행 폴더의 `user_data\config.ini`
- AppData 모드: 사용자 AppData 영역

실행 폴더에 `portable.flag`가 있으면 기존 호환성을 위해 휴대용 모드를 우선 사용합니다.
설정창에서도 저장 위치를 선택할 수 있습니다.

## 개발자 진단 로그

일반 사용 모드에서는 로그 파일을 만들지 않습니다.

실행 파일 또는 `main.py`가 있는 폴더에 `developer.log` 파일이 있으면 개발자 진단 모드로 동작하고, 같은 파일에 시작 과정과 예외 정보를 기록합니다.
다른 PC에서 실행 문제가 있을 때 원인 파악용으로만 사용하는 것을 권장합니다.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

품질 게이트:

```powershell
python tools\quality_gate.py
```

## EXE 빌드

배포 빌드는 PyInstaller 기반 폴더 배포를 사용합니다.

```powershell
cd D:\codex\ScreenAssistant
.\build_exe.ps1
```

빌드 결과:

```text
dist\ScreenAidStudio\ScreenAidStudio.exe
```

배포 폴더에서는 실행 파일만 따로 옮기지 말고, `internal`, `config`, `locales`, `resources`, `docs`, `LICENSE`, `portable.flag` 등을 포함한 폴더 전체를 함께 배포해야 합니다.

## 배포 메모

- 빌드 도구: PyInstaller
- 배포 방식: 폴더 배포
- 콘솔 창: 숨김
- 관리자 권한: 요청 안 함
- 아이콘: `resources\tray_icon.ico`
- 기본 설정: 휴대용 모드
- 사용자 설명서: `docs\user_manual.html`
- GitHub Release 파일명 기준: `ScreenAidStudio.zip`
