import logging
import sys
import os
import threading
import time
import signal
from typing import List, Optional
# Tkinter 임포트 제거
# from tkinter import messagebox 
# PyQt5 임포트 추가
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt # Qt 임포트 추가
# ctypes 임포트 추가 (Windows API 호출용)
import ctypes
import platform
import schedule # schedule 모듈 임포트 추가

# log_setup 모듈에서 setup_logging 함수 임포트
# from log_setup import setup_logging

from alarm import Alarm
from storage import load_alarms, save_alarms
# from ui import AlarmApp # PyQt5 버전으로 변경
from ui import AlarmApp
from scheduler import start_scheduler, stop_scheduler, update_scheduled_alarm, remove_scheduled_alarm
from notification import notification_helper, cleanup_sounds # notification_helper 임포트 및 cleanup 추가

# --- 로깅 설정 (가장 먼저 수행, 가장 단순한 형태로 변경) --- 
log_dir = "logs"
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except OSError as e:
        print(f"Error creating log directory {log_dir}: {e}", file=sys.stderr)
        # 로그 디렉토리 생성 실패 시 처리를 추가할 수 있음 (예: 임시 디렉토리 사용)
log_file_path = os.path.join(log_dir, "debug.log")

try:
    # force=True 를 사용하여 기존 핸들러가 있어도 재설정 시도
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        filename=log_file_path, # 콘솔 핸들러 제거, 파일 핸들러만 사용
        filemode='w', # 매번 새로 쓰기 (이전 로그 제거)
        encoding='utf-8',
        force=True 
    )
    logging.debug("--- Logging Setup Complete (Simplified) ---")
except Exception as e:
    print(f"Error during logging.basicConfig: {e}", file=sys.stderr)
# -----------------------------------------------------------

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
    myappid = u'MyCompanyName.MyProductName.AlarmReminderApp.1' # 고유 ID 문자열
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        logging.info(f"AppUserModelID 설정 완료: {myappid}")
    except AttributeError:
        logging.warning("ctypes 또는 SetCurrentProcessExplicitAppUserModelID를 사용할 수 없습니다.")
    except Exception as e:
        logging.error(f"AppUserModelID 설정 중 오류 발생: {e}")
# --------------------------------------------------------

# --- DPI 스케일링 활성화 --- 
# QApplication 인스턴스 생성 전에 호출해야 함
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) 
# QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True) # 아이콘/이미지에도 적용 (선택 사항)
logging.info("High DPI Scaling 활성화됨.")
# -------------------------

# 저장된 알람 로드
logging.debug("Loading alarms...") # 로깅 추가
alarms = load_alarms()
logging.info(f"{len(alarms)}개의 알람 로드 완료.")

# PyQt5 Application 생성
logging.debug("Initializing QApplication...") # 로깅 추가
app = QApplication(sys.argv)

# UI 인스턴스 생성
ui_app = AlarmApp(alarms)

# --- 사운드 경로 가져오기 콜백 제거 ---
# get_sound_path = lambda: ui_app.selected_sound_path
# ------------------------------------

# 스케줄러 시작 (콜백 없이)
start_scheduler(alarms)

# --- 시그널-슬롯 연결 --- 
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

ui_app.alarms_updated.connect(handle_alarms_updated)
ui_app.alarm_deleted.connect(handle_alarm_deleted)
# -------------------------

ui_app.show()

app.aboutToQuit.connect(stop_scheduler)
app.aboutToQuit.connect(cleanup_sounds) # 앱 종료 시 사운드 정리 추가

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

if __name__ == "__main__":
    # 전역 스케줄러 임포트 (시그널 핸들러에서 사용하기 위함)
    import scheduler 
    main()
