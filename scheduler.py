import schedule
import time
import threading
import logging
from typing import List, Callable
from alarm import Alarm, RepeatSetting
from notification import show_notification

# 스케줄러 실행 루프를 제어하기 위한 이벤트
stop_run_continuously = threading.Event()

def run_alarm(alarm: Alarm):
    """알람이 울릴 때 실행될 함수"""
    logging.info(f"알람 실행: {alarm.title} ({alarm.time_str}) - 반복: {alarm.repeat.value}")
    show_notification(title=f"⏰ Alarm: {alarm.title}", message=f"It's {alarm.time_str}!")

def schedule_alarm(alarm: Alarm):
    """주어진 알람을 스케줄에 등록합니다."""
    if not alarm.enabled:
        logging.debug(f"비활성화된 알람 건너뛰기: {alarm.title}")
        return

    job = None
    if alarm.repeat == RepeatSetting.DAILY:
        job = schedule.every().day.at(alarm.time_str).do(run_alarm, alarm=alarm)
    elif alarm.repeat == RepeatSetting.WEEKLY:
        # schedule 라이브러리는 요일별 반복을 직접 지원하지 않음
        # 매일 지정된 시간에 실행하되, run_alarm 내에서 요일 체크 필요 (여기서는 단순화)
        # 또는 요일별로 schedule.every().monday.at(...) 등을 사용할 수 있으나 복잡해짐
        # 여기서는 매주 반복도 일단 매일 실행으로 등록 (개선 필요)
        # TODO: 주간 반복 정확하게 구현하기
        logging.warning(f"주간 반복({alarm.title})은 현재 매일 반복으로 동작합니다.")
        job = schedule.every().day.at(alarm.time_str).do(run_alarm, alarm=alarm)
    elif alarm.repeat == RepeatSetting.NONE:
        # 일회성 알람은 오늘 지정된 시간에 실행
        # TODO: 이미 지난 시간의 일회성 알람은 스케줄하지 않거나 다음 날로 처리하는 로직 필요
        job = schedule.every().day.at(alarm.time_str).do(run_alarm, alarm=alarm)
        # 일회성 작업 실행 후 자동으로 제거되도록 태그 지정
        job.tag(f'once_{alarm.id}')
    else:
        logging.error(f"알 수 없는 반복 설정: {alarm.repeat}")

    if job:
        job.tag(alarm.id) # 알람 ID로 태그 지정하여 관리 용이하게
        logging.info(f"알람 스케줄됨: {alarm.title} ({alarm.time_str}) - 반복: {alarm.repeat.value}, 태그: {alarm.id}")

def schedule_alarms(alarms: List[Alarm]):
    """모든 알람을 스케줄에 등록합니다."""
    schedule.clear() # 기존 스케줄 제거
    logging.info(f"기존 스케줄 클리어됨. {len(alarms)}개의 알람 스케줄링 시작.")
    for alarm in alarms:
        schedule_alarm(alarm)
    logging.info("모든 활성 알람 스케줄링 완료.")
    logging.info(f"현재 스케줄된 작업: {schedule.get_jobs()}")

def run_continuously(interval=1):
    """스케줄러를 백그라운드에서 계속 실행합니다."""
    logging.info("스케줄러 백그라운드 스레드 시작.")
    while not stop_run_continuously.is_set():
        try:
            schedule.run_pending()

            # 일회성 작업 처리: 실행 후 스케줄에서 제거
            jobs_to_remove = []
            for job in schedule.get_jobs():
                if 'once_' in job.tags and job.last_run is not None:
                    # job.last_run이 설정되었다면 한번 실행된 것
                    # TODO: 정확한 일회성 처리를 위해서는 실행 시점에서 비활성화하고 저장하는 로직 필요
                    #       여기서는 단순히 스케줄에서만 제거
                    alarm_id_tag = next((tag for tag in job.tags if tag.startswith('once_')), None)
                    if alarm_id_tag:
                        logging.info(f"일회성 알람 '{alarm_id_tag}' 실행 완료. 스케줄에서 제거합니다.")
                        jobs_to_remove.append(job)
                        # 실제 알람 비활성화는 UI나 메인 로직에서 처리해야 함

            for job in jobs_to_remove:
                schedule.cancel_job(job)

            time.sleep(interval)
        except Exception as e:
            logging.exception("스케줄러 실행 중 오류 발생")
            time.sleep(interval) # 오류 발생 시에도 잠시 대기 후 계속

    logging.info("스케줄러 백그라운드 스레드 종료.")

def start_scheduler(alarms: List[Alarm]):
    """스케줄러를 시작하고 백그라운드 스레드를 실행합니다."""
    schedule_alarms(alarms)
    # 데몬 스레드로 설정하여 메인 스레드 종료 시 함께 종료되도록 함
    scheduler_thread = threading.Thread(target=run_continuously, daemon=True)
    scheduler_thread.start()
    logging.info("스케줄러 시작 및 백그라운드 스레드 실행됨.")
    return scheduler_thread

def stop_scheduler():
    """스케줄러 백그라운드 스레드를 중지 신호를 보냅니다."""
    logging.info("스케줄러 중지 요청됨.")
    stop_run_continuously.set()

def update_scheduled_alarm(alarm: Alarm):
    """특정 알람의 스케줄을 업데이트합니다 (기존 것 제거 후 새로 추가)."""
    # 해당 ID를 가진 모든 태그된 작업 제거
    logging.debug(f"'{alarm.id}' 태그를 가진 스케줄 작업 제거 시도.")
    schedule.clear(alarm.id)
    logging.info(f"알람 '{alarm.title}' ({alarm.id}) 스케줄 업데이트 중: 기존 작업 제거 완료.")
    # 알람이 활성화 상태일 때만 새로 스케줄
    if alarm.enabled:
        schedule_alarm(alarm)
        logging.info(f"알람 '{alarm.title}' ({alarm.id})이(가) 활성화되어 새로 스케줄됨.")
    else:
        logging.info(f"알람 '{alarm.title}' ({alarm.id})이(가) 비활성화 상태이므로 스케줄하지 않음.")
    logging.info(f"업데이트 후 현재 스케줄된 작업: {schedule.get_jobs()}")

def remove_scheduled_alarm(alarm_id: str):
    """특정 ID의 알람을 스케줄에서 제거합니다."""
    logging.debug(f"'{alarm_id}' 태그를 가진 스케줄 작업 제거 시도.")
    schedule.clear(alarm_id)
    logging.info(f"알람 ID '{alarm_id}' 스케줄 제거 완료.")
    logging.info(f"제거 후 현재 스케줄된 작업: {schedule.get_jobs()}") 