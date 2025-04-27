import logging
import sys
from typing import List, Optional
# Tkinter 임포트 제거
# from tkinter import messagebox 
# PyQt5 임포트 추가
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt # Qt 임포트 추가

from alarm import Alarm
from storage import load_alarms, save_alarms
# from ui import AlarmApp # PyQt5 버전으로 변경
from ui import AlarmApp
from scheduler import start_scheduler, stop_scheduler, update_scheduled_alarm, remove_scheduled_alarm

def setup_logging():
    """기본 로깅 설정을 구성합니다."""
    logging.basicConfig(
        level=logging.INFO, # 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
        handlers=[
            logging.FileHandler("alarm_app.log", encoding='utf-8'), # 로그 파일 핸들러
            logging.StreamHandler(sys.stdout) # 콘솔 출력 핸들러
        ]
    )
    logging.info("로깅 설정 완료.")

def main():
    setup_logging()

    # --- DPI 스케일링 활성화 --- 
    # QApplication 인스턴스 생성 전에 호출해야 함
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) 
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True) # 아이콘/이미지에도 적용 (선택 사항)
    logging.info("High DPI Scaling 활성화됨.")
    # -------------------------

    # 저장된 알람 로드
    alarms = load_alarms()
    logging.info(f"{len(alarms)}개의 알람 로드 완료.")

    # 스케줄러 시작 (별도 스레드)
    start_scheduler(alarms)

    # PyQt5 Application 생성
    app = QApplication(sys.argv)

    # UI 인스턴스 생성
    ui_app = AlarmApp(alarms)

    # --- 시그널-슬롯 연결 --- 
    def handle_alarms_updated(updated_alarms: List[Alarm]):
        """UI에서 알람 목록 변경 시 호출될 슬롯"""
        logging.info(f"UI로부터 알람 업데이트 시그널 수신. 총 {len(updated_alarms)}개.")
        # 업데이트된 전체 목록 저장
        save_alarms(updated_alarms)
        
        # 스케줄 업데이트 (기존 로직과 유사하게 처리)
        # TODO: 변경된 알람만 효율적으로 찾아 업데이트하는 로직 개선
        # current_scheduled_ids = {job.tags[0] for job in scheduler.schedule.get_jobs() if job.tags and not job.tags[0].startswith('once_')}
        # job.tags는 set이므로 인덱싱 불가. 각 job에는 alarm.id 태그 하나만 있다고 가정.
        current_scheduled_ids = {next(iter(job.tags)) for job in scheduler.schedule.get_jobs() if job.tags}
        updated_alarm_map = {a.id: a for a in updated_alarms}
        
        ids_to_update_or_add = []
        ids_to_remove_from_schedule = list(current_scheduled_ids - set(updated_alarm_map.keys()))
        
        for alarm in updated_alarms:
            # 내용 변경 여부와 관계없이 일단 업데이트 대상에 포함 (개선 필요)
            ids_to_update_or_add.append(alarm.id)

        # 스케줄에서 제거
        for alarm_id in ids_to_remove_from_schedule:
             logging.info(f"파일 목록에 없는 알람 ID {alarm_id} 스케줄 제거 요청.")
             remove_scheduled_alarm(alarm_id)

        # 스케줄 업데이트/추가
        for alarm_id in ids_to_update_or_add:
             if alarm_id in updated_alarm_map:
                 alarm = updated_alarm_map[alarm_id]
                 logging.info(f"알람 ID {alarm_id} 스케줄 업데이트/추가 요청.")
                 update_scheduled_alarm(alarm)
             else:
                 logging.warning(f"업데이트 대상 알람 ID {alarm_id}를 찾을 수 없어 스케줄링 건너뜁니다.")

        logging.info("알람 저장 및 리스케줄 완료.")

    def handle_alarm_deleted(deleted_alarm_id: str):
        """UI에서 알람 삭제 시 호출될 슬롯"""
        logging.info(f"UI로부터 알람 삭제 시그널 수신: ID {deleted_alarm_id}")
        # 저장된 목록은 UI에서 이미 처리 후 updated 시그널을 보냈으므로,
        # 여기서는 스케줄러에서만 제거
        remove_scheduled_alarm(deleted_alarm_id)
        logging.info(f"삭제된 알람 ID {deleted_alarm_id} 스케줄 제거 완료.")
        # 삭제 후 전체 목록을 다시 저장할 수도 있음 (선택 사항)
        # save_alarms(ui_app.alarms)

    # UI의 시그널을 메인 로직의 슬롯 함수에 연결
    ui_app.alarms_updated.connect(handle_alarms_updated)
    ui_app.alarm_deleted.connect(handle_alarm_deleted)

    # --- 애플리케이션 종료 처리 --- 
    def about_to_quit_handler():
        """QApplication 종료 직전에 호출될 함수"""
        logging.info("애플리케이션 종료 시퀀스 시작.")
        # 사용자 확인 없이 바로 스케줄러 중지
        logging.info("스케줄러 중지 시도...")
        stop_scheduler()
        logging.info("애플리케이션 종료 완료.")
        # 참고: PyQt 앱이 종료되면 스케줄러 스레드도 데몬이므로 자동 종료됨
        # 명시적 중지는 리소스 정리 및 로그 기록을 위해 수행

    # Qt 애플리케이션의 aboutToQuit 시그널에 핸들러 연결
    app.aboutToQuit.connect(about_to_quit_handler)

    # UI 표시
    ui_app.show()

    # 애플리케이션 실행 루프 시작
    try:
        logging.info("PyQt5 애플리케이션 이벤트 루프 시작.")
        exit_code = app.exec_()
        logging.info(f"PyQt5 애플리케이션 이벤트 루프 종료. 종료 코드: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt 수신. 애플리케이션 강제 종료.")
        # KeyboardInterrupt 시 aboutToQuit 시그널이 발생하지 않을 수 있으므로
        # 여기서도 스케줄러 중지 호출 고려 (선택적)
        stop_scheduler()
        sys.exit(1)

if __name__ == "__main__":
    # 전역 스케줄러 임포트 (시그널 핸들러에서 사용하기 위함)
    import scheduler 
    main()
