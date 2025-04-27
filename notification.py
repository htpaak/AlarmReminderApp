from plyer import notification
import logging

def show_notification(title: str, message: str):
    """시스템 알림을 표시합니다."""
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Alarm App", # 앱 이름
            timeout=10 # 10초 동안 표시
        )
        logging.info(f"알림 표시: {title} - {message}")
    except Exception as e:
        # plyer가 특정 시스템에서 작동하지 않을 경우 로그만 남김
        logging.error(f"알림 표시 실패: {e}")
        print(f"알림: {title} - {message}") # 콘솔에 대신 출력 