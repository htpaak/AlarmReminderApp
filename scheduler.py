import schedule
import time
import threading
import logging
from typing import List, Callable, Optional
import datetime

# RepeatSetting 임포트 제거, WEEKDAYS 임포트
from alarm import Alarm, WEEKDAYS #, RepeatSetting 
from notification import show_notification

# 스케줄러 실행 루프를 제어하기 위한 이벤트
stop_run_continuously = threading.Event()

def run_alarm(alarm: Alarm):
    """알람이 울릴 때 실행될 함수. 알람 객체에서 직접 사운드 경로를 읽어 사용합니다."""
    repeat_str = alarm.get_repeat_str() if alarm.selected_days else "One-time"
    logging.info(f"알람 실행: {alarm.title} ({alarm.time_str}) - 반복: {repeat_str}")
    
    # 알람 객체에서 사운드 경로 가져오기
    sound_path = alarm.sound_path 
    logging.debug(f"알람 [{alarm.title}]의 sound_path: {sound_path}") # 확인용 로그

    show_notification(title=f"⏰ Alarm: {alarm.title}", message=f"It's {alarm.time_str}!", sound_path=sound_path)

    # 일회성 알람인 경우 (selected_days가 비어 있음), 실행 후 작업 취소
    if not alarm.selected_days:
        logging.info(f"일회성 알람 '{alarm.title}' 실행 완료. 스케줄에서 제거합니다.")
        # 실제 알람 비활성화는 UI/메인 로직과 연동 필요 (선택적)
        # alarm.enabled = False # 예시: 여기서 직접 비활성화
        # save_alarms(...) # 변경사항 저장 필요
        return schedule.CancelJob # 작업을 스케줄러에서 제거

def schedule_alarm(alarm: Alarm):
    """주어진 알람을 스케줄에 등록합니다. (콜백 제거)"""
    if not alarm.enabled:
        logging.debug(f"비활성화된 알람 건너뛰기: {alarm.title}")
        return

    scheduled_jobs_count = 0
    
    if alarm.selected_days:
        day_map = {
            0: schedule.every().monday,
            1: schedule.every().tuesday,
            2: schedule.every().wednesday,
            3: schedule.every().thursday,
            4: schedule.every().friday,
            5: schedule.every().saturday,
            6: schedule.every().sunday,
        }
        for day_index in alarm.selected_days:
            if day_index in day_map:
                try:
                    job = day_map[day_index].at(alarm.time_str).do(run_alarm, alarm=alarm)
                    job.tag(alarm.id)
                    scheduled_jobs_count += 1
                    logging.info(f"  -> {WEEKDAYS[day_index]} at {alarm.time_str} 스케줄됨 (Tag: {alarm.id})")
                except Exception as e:
                     logging.error(f"요일별 알람 스케줄 중 오류 ({WEEKDAYS[day_index]}): {e}")
            else:
                logging.warning(f"알 수 없는 요일 인덱스: {day_index}")
    else:
        # TODO: 이미 지난 시간 처리 개선 필요
        # 현재: 일단 오늘 해당 시간에 실행되도록 등록하고, run_alarm에서 취소
        try:
            job = schedule.every().day.at(alarm.time_str).do(run_alarm, alarm=alarm)
            job.tag(alarm.id)
            scheduled_jobs_count += 1
            logging.info(f"  -> One-time at {alarm.time_str} 스케줄됨 (Tag: {alarm.id})")
        except Exception as e:
             logging.error(f"일회성 알람 스케줄 중 오류: {e}")

    if scheduled_jobs_count > 0:
        repeat_str = alarm.get_repeat_str() if alarm.selected_days else "One-time"
        logging.info(f"알람 '{alarm.title}' 스케줄 완료 ({scheduled_jobs_count}개 작업 등록). 반복: {repeat_str}")
    else:
        logging.warning(f"알람 '{alarm.title}'에 대해 스케줄된 작업이 없습니다.")

def schedule_alarms(alarms: List[Alarm]):
    """모든 알람을 스케줄에 등록합니다."""
    schedule.clear() # 기존 스케줄 제거
    logging.info(f"기존 스케줄 클리어됨. {len(alarms)}개의 알람 스케줄링 시작.")
    for alarm in alarms:
        schedule_alarm(alarm)
    logging.info("모든 활성 알람 스케줄링 완료.")
    logging.info(f"현재 스케줄된 작업 ({len(schedule.get_jobs())}개): {schedule.get_jobs()}")

def run_continuously(interval=1):
    """스케줄러를 백그라운드에서 계속 실행합니다."""
    logging.info("스케줄러 백그라운드 스레드 시작.")
    while not stop_run_continuously.is_set():
        try:
            schedule.run_pending()
            # 일회성 작업 처리는 run_alarm 내부에서 schedule.CancelJob 반환으로 처리됨
            time.sleep(interval)
        except Exception as e:
            logging.exception("스케줄러 실행 중 오류 발생")
            time.sleep(interval) # 오류 발생 시에도 잠시 대기 후 계속
    logging.info("스케줄러 백그라운드 스레드 종료.")

def start_scheduler(initial_alarms: List[Alarm]):
    """초기 알람 목록으로 스케줄러를 설정하고 백그라운드 스레드에서 시작합니다. (콜백 제거)"""
    global _scheduler_thread
    if _scheduler_thread is not None:
        logging.warning("스케줄러가 이미 실행 중입니다.")
        return
    
    logging.info("스케줄러 설정 및 시작 중...")
    schedule.clear()
    for alarm in initial_alarms:
        schedule_alarm(alarm) # 콜백 없이 호출
    
    logging.info(f"초기 스케줄된 작업 ({len(schedule.get_jobs())}개): {schedule.get_jobs()}")

    # 스레드 중지 이벤트 리셋
    stop_run_continuously.clear()
    # 스케줄러 실행 루프를 백그라운드 스레드에서 시작
    _scheduler_thread = threading.Thread(target=run_continuously, daemon=True)
    _scheduler_thread.start()
    logging.info("스케줄러 백그라운드 스레드 시작됨.")

def stop_scheduler():
    """스케줄러 백그라운드 스레드를 중지 신호를 보냅니다."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        logging.info("스케줄러 중지 요청 중...")
        stop_run_continuously.set() # 루프 중지 플래그 설정
        _scheduler_thread.join() # 스레드가 완전히 종료될 때까지 대기
        _scheduler_thread = None
        logging.info("스케줄러 중지 완료.")
    else:
        logging.info("스케줄러가 실행 중이지 않음.")

_scheduler_thread: Optional[threading.Thread] = None

def update_scheduled_alarm(alarm: Alarm):
    """특정 알람의 스케줄을 업데이트합니다. (콜백 제거)"""
    logging.debug(f"'{alarm.id}' 태그를 가진 스케줄 작업 제거 시도.")
    schedule.clear(alarm.id)
    logging.info(f"알람 '{alarm.title}' ({alarm.id}) 스케줄 업데이트 중: 기존 작업 제거 완료.")
    if alarm.enabled:
        schedule_alarm(alarm) # 콜백 없이 호출
    else:
        logging.info(f"알람 '{alarm.title}' ({alarm.id})이(가) 비활성화 상태이므로 스케줄하지 않음.")
    logging.info(f"업데이트 후 현재 스케줄된 작업 ({len(schedule.get_jobs())}개): {schedule.get_jobs()}")

def remove_scheduled_alarm(alarm_id: str):
    """특정 ID의 알람을 스케줄에서 제거합니다."""
    logging.debug(f"'{alarm_id}' 태그를 가진 스케줄 작업 제거 시도.")
    schedule.clear(alarm_id)
    logging.info(f"알람 ID '{alarm_id}' 스케줄 제거 완료.")
    logging.info(f"제거 후 현재 스케줄된 작업 ({len(schedule.get_jobs())}개): {schedule.get_jobs()}") 