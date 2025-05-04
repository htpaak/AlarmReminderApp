import logging
import sys
import os
import threading
import time
import signal
from typing import List, Optional
# PyQt5 임포트 추가/수정
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import Qt, QSettings # QSettings 임포트 추가
from PyQt5.QtGui import QIcon # QIcon 임포트 추가
# ctypes 임포트 추가 (Windows API 호출용)
import ctypes
import platform
import schedule # schedule 모듈 임포트 추가
# Windows 레지스트리 접근용 winreg 임포트
if platform.system() == "Windows":
    try:
        import winreg
    except ImportError:
        logging.error("Windows 환경이지만 winreg 모듈을 찾을 수 없습니다. 시작 프로그램 설정 기능이 비활성화됩니다.")
        winreg = None # winreg 사용 불가 표시
else:
    winreg = None # Windows 외 환경에서는 사용 안 함


# --- Resource Path Helper ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running in development mode: Use the directory of the current file (__file__)
        base_path = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)
# ---------------------------

# --- 시작 프로그램 레지스트리 제어 함수 (Windows 전용) ---
def add_to_startup(app_name: str, executable_path: str):
    """현재 사용자의 시작 프로그램 목록에 애플리케이션을 추가합니다."""
    if not winreg:
        logging.warning("winreg 모듈을 사용할 수 없어 시작 프로그램에 추가할 수 없습니다.")
        return
    
    registry_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        # 레지스트리 키 열기 (없으면 생성 시도 안 함 - 기본 키는 존재해야 함)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_key, 0, winreg.KEY_WRITE)
        # 경로에 공백이 있을 수 있으므로 따옴표로 감싸고, 뒤에 실행 인자 추가
        quoted_path = f'"{executable_path}"'
        startup_command = f'{quoted_path} --minimized' # 실행 인자 추가
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, startup_command)
        winreg.CloseKey(key)
        logging.info(f"'{app_name}'을(를) 시작 프로그램에 추가했습니다: {startup_command}")
    except OSError as e:
        logging.error(f"시작 프로그램 추가 중 오류 발생 (키: {registry_key}, 앱: {app_name}): {e}")
    except Exception as e:
        logging.error(f"시작 프로그램 추가 중 예기치 않은 오류 발생: {e}")

def remove_from_startup(app_name: str):
    """현재 사용자의 시작 프로그램 목록에서 애플리케이션을 제거합니다."""
    if not winreg:
        logging.warning("winreg 모듈을 사용할 수 없어 시작 프로그램에서 제거할 수 없습니다.")
        return
        
    registry_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_key, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        logging.info(f"'{app_name}'을(를) 시작 프로그램에서 제거했습니다.")
    except FileNotFoundError:
        logging.warning(f"시작 프로그램에서 '{app_name}'을(를) 찾을 수 없어 제거하지 못했습니다.")
    except OSError as e:
        logging.error(f"시작 프로그램 제거 중 오류 발생 (키: {registry_key}, 앱: {app_name}): {e}")
    except Exception as e:
        logging.error(f"시작 프로그램 제거 중 예기치 않은 오류 발생: {e}")
# -----------------------------------------------------

# log_setup 모듈에서 setup_logging 함수 임포트
# from log_setup import setup_logging

from alarm import Alarm
from storage import load_alarms, save_alarms, APP_DATA_DIR, _ensure_dir_exists # APP_DATA_DIR, _ensure_dir_exists 임포트 추가
# from ui import AlarmApp # PyQt5 버전으로 변경
from ui import AlarmApp
from scheduler import start_scheduler, stop_scheduler, update_scheduled_alarm, remove_scheduled_alarm, _scheduler_thread # scheduler_thread 임포트 추가
# from notification import notification_helper, cleanup_sounds # notification_helper 제거
from notification import cleanup_sounds 

# --- 로깅 설정 수정 ---
# 패키지된 상태인지 확인 (PyInstaller는 sys.frozen 속성을 설정함)
is_packaged = getattr(sys, 'frozen', False)

if not is_packaged:
    # 소스 코드로 실행 중일 때만 파일 로깅 설정
    log_dir = "logs"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            # 로그 디렉토리 생성 실패 시 오류 메시지 출력 (콘솔에만)
            print(f"Error creating log directory {log_dir}: {e}", file=sys.stderr)
            log_file_path = None # 경로 None으로 설정
        else:
             log_file_path = os.path.join(log_dir, "debug.log")
    else:
        log_file_path = os.path.join(log_dir, "debug.log")

    if log_file_path: # 로그 파일 경로가 유효할 때만 파일 핸들러 설정
        try:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s [%(levelname)s] %(message)s',
                filename=log_file_path,
                filemode='w',
                encoding='utf-8',
                force=True
            )
            logging.debug("--- File Logging Setup Complete (Running from Source) ---")
        except Exception as e:
            print(f"Error during file logging setup: {e}", file=sys.stderr)
    else:
        # 로그 파일 경로가 없으면 (디렉토리 생성 실패 등) 기본 콘솔 로깅 설정
         logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')
         logging.warning("--- File Logging Skipped (Log directory issue), Basic Config Active ---")

else:
    # 패키지된 상태로 실행 중일 때
    try:
        # 로그 디렉토리 생성 확인 (storage 모듈 함수 사용)
        _ensure_dir_exists()
        
        # 로그 파일 경로를 AppData 내로 설정
        log_file_path = os.path.join(APP_DATA_DIR, "packaged_debug.log")
        
        logging.basicConfig(
            level=logging.DEBUG, # 디버깅을 위해 DEBUG 레벨 유지
            format='%(asctime)s [%(levelname)s] %(message)s',
            filename=log_file_path,
            filemode='w', # 실행 시마다 새로 쓰기
            encoding='utf-8',
            force=True
        )
        logging.info("--- Logging Setup Complete (Running Packaged - Logging to AppData) ---")
        
    except Exception as e:
        # 파일 로깅 설정 실패 시 (예: 쓰기 권한 없음 등)
        # 이 경우 로그를 볼 수 없지만, 앱 실행은 계속 시도
        print(f"Error setting up file logging in packaged mode: {e}", file=sys.stderr) # 콘솔에라도 출력 시도
        # 로깅 완전 비활성화 대신 경고 레벨 이상만 콘솔 출력 시도 (선택 사항)
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')
        logging.error(f"--- Failed to setup file logging for packaged app: {e} ---")
        # logging.disable(logging.CRITICAL) # 로깅 완전 비활성화 제거
    
    # 최종 배포 시 로깅 비활성화 복원 (제거됨)
    # logging.disable(logging.CRITICAL)

# --- 애플리케이션 정보 ---
COMPANY_NAME = "MyCompanyName"
APP_NAME = "AlarmReminderPAAKApp"
APP_USER_MODEL_ID = f'{COMPANY_NAME}.{APP_NAME}.1' # AppUserModelID
# -----------------------

# --- QSettings 초기화 ---
settings = QSettings(COMPANY_NAME, APP_NAME)
# -------------------------

# --- 전역 예외 처리 후크 --- 
def handle_exception(exc_type, exc_value, exc_traceback):
    """처리되지 않은 예외를 로깅하는 함수"""
    if issubclass(exc_type, KeyboardInterrupt):
        # 사용자가 Ctrl+C로 종료한 경우는 정상 종료로 간주
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Unhandled exception caught:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception
# -------------------------

# --- AppUserModelID 설정 (Windows 작업 표시줄 아이콘용) --- 
if platform.system() == "Windows":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        # logging.info(f"AppUserModelID 설정 완료: {APP_USER_MODEL_ID}") # 로깅 비활성화됨
    except AttributeError:
        # logging.warning("ctypes 또는 SetCurrentProcessExplicitAppUserModelID를 사용할 수 없습니다.") # 로깅 비활성화됨
        pass # 최종본에서는 오류 처리 무시 (로깅 불가)
    except Exception as e:
        # logging.error(f"AppUserModelID 설정 중 오류 발생: {e}") # 로깅 비활성화됨
        pass # 최종본에서는 오류 처리 무시 (로깅 불가)
# --------------------------------------------------------

# --- DPI 스케일링 활성화 --- 
# QApplication 인스턴스 생성 전에 호출해야 함
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) 
# QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True) # 아이콘/이미지에도 적용 (선택 사항)
logging.info("High DPI Scaling 활성화됨.")
# -------------------------

# 저장된 알람 로드
logging.debug("Loading alarms...") 
alarms = load_alarms()
logging.info(f"{len(alarms)}개의 알람 로드 완료.")

logging.debug("Initializing QApplication...") 
app = QApplication(sys.argv)
# --- 창 닫을 때 종료하지 않도록 설정 --- 
app.setQuitOnLastWindowClosed(False)
# --------------------------------------

# --- 시스템 트레이 아이콘 설정 --- 
logging.debug("Setting up system tray icon...")
tray_icon_path = resource_path("assets/icon.ico") # 경로 가져오기
logging.debug(f"Tray icon path: {tray_icon_path}") # 경로 로깅 추가 (테스트용)
tray_icon = QSystemTrayIcon(QIcon(tray_icon_path), parent=app) # 절대 경로 사용
tray_icon.setToolTip("AlarmReminderPAAKApp")

# 트레이 메뉴 생성
menu = QMenu()
show_action = QAction("Show/Hide", parent=app)
quit_action = QAction("Quit", parent=app)

# 액션 연결 (toggle_window_visibility 는 ui_app 생성 후에 정의되므로 lambda 사용)
# quit 액션은 바로 연결 가능
quit_action.triggered.connect(QApplication.instance().quit) # 앱 종료 시그널

# 메뉴에 액션 추가
menu.addAction(show_action) # 나중에 연결할 show_action 먼저 추가
menu.addSeparator()
menu.addAction(quit_action)

# 아이콘에 메뉴 설정
tray_icon.setContextMenu(menu)
# tray_icon.show() # UI 생성 및 show() 이후에 호출
# ---------------------------------

# --- 시작 프로그램 설정 로드 ---
initial_start_on_boot = settings.value("startOnBoot", False, type=bool)
logging.debug(f"Loaded 'startOnBoot' setting: {initial_start_on_boot}")
# ---------------------------

# UI 인스턴스 생성 (tray_icon 및 시작 프로그램 초기 상태 전달)
logging.debug("Creating AlarmApp UI instance...")
ui_app = AlarmApp(alarms, tray_icon, initial_start_on_boot)

# --- 트레이 아이콘 관련 함수 정의 --- 
def toggle_window_visibility(window):
    """창 보이기/숨기기 토글"""
    if window.isVisible():
        logging.debug("Hiding window via tray action.")
        window.hide()
    else:
        logging.debug("Showing window via tray action.")
        window.show()
        window.activateWindow() # 창을 활성화하고 앞으로 가져옴

def handle_tray_activation(reason, window):
    """트레이 아이콘 클릭 처리 (왼쪽 클릭 시 창 토글)"""
    if reason == QSystemTrayIcon.Trigger: # 왼쪽 버튼 클릭
        logging.debug("Tray icon activated (Trigger).")
        toggle_window_visibility(window)
# --------------------------

# --- 트레이 아이콘 액션 연결 완료 및 표시 --- 
# 이제 ui_app이 정의되었으므로 show_action 연결 가능
show_action.triggered.connect(lambda: toggle_window_visibility(ui_app))
# 트레이 아이콘 클릭 시 동작 연결
tray_icon.activated.connect(lambda reason: handle_tray_activation(reason, ui_app))
tray_icon.show() # 트레이 아이콘 표시
logging.debug("System tray icon setup complete and shown.")
# ----------------------------------------

# 스케줄러 시작 
start_scheduler(alarms)

# --- 시그널-슬롯 연결 (수정) --- 
def handle_alarms_updated(updated_alarms: List[Alarm]):
    """UI에서 알람 목록 변경 시 호출될 슬롯"""
    logging.info(f"UI로부터 알람 업데이트 시그널 수신. 총 {len(updated_alarms)}개.")
    save_alarms(updated_alarms)
    
    # 스케줄 업데이트 로직 (기존과 유사, 콜백 없이)
    current_scheduled_ids = set()
    try:
        current_scheduled_ids = {next(iter(job.tags)) for job in schedule.get_jobs() if job.tags}
    except Exception as e:
        logging.error(f"스케줄된 작업 ID 가져오기 실패: {e}")
        
    updated_alarm_map = {a.id: a for a in updated_alarms}
    
    ids_to_update_or_add = []
    ids_to_remove_from_schedule = list(current_scheduled_ids - set(updated_alarm_map.keys()))
    
    for alarm in updated_alarms:
        ids_to_update_or_add.append(alarm.id)

    for alarm_id in ids_to_remove_from_schedule:
         logging.info(f"파일 목록에 없는 알람 ID {alarm_id} 스케줄 제거 요청.")
         remove_scheduled_alarm(alarm_id)

    for alarm_id in ids_to_update_or_add:
        if alarm_id in updated_alarm_map:
            logging.info(f"알람 ID {alarm_id} 스케줄 업데이트 요청.")
            update_scheduled_alarm(updated_alarm_map[alarm_id]) # 콜백 없이 호출
        else:
            logging.warning(f"업데이트 대상 알람 ID {alarm_id}를 찾을 수 없습니다.")

def handle_alarm_deleted(deleted_alarm_id: str):
    """UI에서 알람 삭제 시 호출될 슬롯"""
    logging.info(f"UI로부터 알람 삭제 시그널 수신: ID {deleted_alarm_id}")
    remove_scheduled_alarm(deleted_alarm_id)

def handle_start_on_boot_change(enabled: bool):
    """UI에서 시작 프로그램 설정 변경 시 호출될 슬롯"""
    logging.info(f"UI로부터 시작 프로그램 설정 변경 시그널 수신: {'Enabled' if enabled else 'Disabled'}")
    
    executable_path = sys.executable # 현재 실행 파일 경로
    # 패키지된 경우 .exe 경로, 개발 환경에서는 python.exe 경로일 수 있음
    logging.debug(f"Executable path for startup registration: {executable_path}")

    if platform.system() == "Windows" and winreg:
        try:
            if enabled:
                add_to_startup(APP_NAME, executable_path)
            else:
                remove_from_startup(APP_NAME)
            # 설정 저장
            settings.setValue("startOnBoot", enabled)
            logging.info(f"'startOnBoot' setting saved: {enabled}")
        except Exception as e:
            logging.error(f"시작 프로그램 설정 처리 중 오류 발생: {e}")
            # 사용자에게 오류 알림 (선택 사항)
            QMessageBox.warning(None, "Error", f"Failed to update startup settings: {e}")
    elif platform.system() != "Windows":
        logging.warning("시작 프로그램 설정은 Windows에서만 지원됩니다.")
        # 필요하다면 사용자에게 알림
        # QMessageBox.information(None, "Info", "Startup setting is only available on Windows.")
    else: # Windows지만 winreg가 없는 경우
         logging.warning("winreg 모듈 부재로 시작 프로그램 설정을 변경할 수 없습니다.")
         # QMessageBox.warning(None, "Error", "Failed to access Windows registry for startup settings.")


ui_app.alarms_updated.connect(handle_alarms_updated)
ui_app.alarm_deleted.connect(handle_alarm_deleted)
ui_app.start_on_boot_changed.connect(handle_start_on_boot_change) # 시그널 연결 추가
# -------------------------

logging.debug("Showing main window...")
# --- 시작 인자에 따라 창 표시 여부 결정 ---
if "--minimized" not in sys.argv:
    logging.info("일반 실행 모드: 메인 창을 표시합니다.")
    ui_app.show()
else:
    logging.info("최소화 모드(--minimized)로 시작: 메인 창을 숨깁니다.")
    # ui_app.show() 호출 안 함 (트레이 아이콘은 이미 표시됨)
# ---------------------------------------

# --- 앱 종료 시 정리 작업 연결 --- 
app.aboutToQuit.connect(stop_scheduler)
app.aboutToQuit.connect(cleanup_sounds) 

# --- 시그널 핸들러 설정 (Ctrl+C 종료용) --- 
def signal_handler(sig, frame):
    logging.info("Ctrl+C 감지됨. 애플리케이션 종료 중...")
    stop_scheduler()
    cleanup_sounds() # 시그널 핸들러에서도 사운드 정리
    QApplication.quit()
signal.signal(signal.SIGINT, signal_handler)
# -------------------------------------------

# --- 이벤트 루프 실행 (오류 로깅 포함) --- 
try:
    logging.info("QApplication 이벤트 루프 시작.")
    exit_code = app.exec_()
    logging.info(f"QApplication 이벤트 루프 종료됨. 종료 코드: {exit_code}")
    sys.exit(exit_code)
except Exception as e:
    logging.error("QApplication 이벤트 루프 중 예외 발생:", exc_info=True)
    stop_scheduler() # 예외 발생 시에도 스케줄러 중지 시도
    cleanup_sounds() # 예외 발생 시에도 사운드 정리 시도
    sys.exit(1) # 오류 코드 반환하며 종료

# 직접 실행 시 main() 호출 (위의 if 블록 대신 사용)
if __name__ == '__main__':
    # main() 함수 로직이 이미 전역 스코프에서 실행되고 있으므로 별도 호출 불필요
    pass # 전역 스코프에서 이미 실행됨
