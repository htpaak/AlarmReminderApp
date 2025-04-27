import logging
import platform

# PyQt5 QApplication 임포트 (위치 조정을 위해)
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMetaObject, Qt, Q_ARG, QObject, pyqtSlot

# 새로 만든 커스텀 알림 창 임포트
from custom_notification_dialog import CustomNotificationDialog

# plyer 라이브러리 임포트 시도 (제거)
# try:
#     from plyer import notification
#     PLYER_AVAILABLE = True
# except ImportError:
#     logging.warning("plyer 라이브러리를 찾을 수 없습니다. 시스템 알림 대신 콘솔 출력을 사용합니다.")
#     PLYER_AVAILABLE = False

# 스레드 안전성을 위한 글로벌 변수 (생성된 다이얼로그 참조 유지)
# 여러 알림이 동시에 발생할 경우 리스트 등으로 관리 필요
_active_dialogs = []

# --- 알림 표시를 위한 헬퍼 클래스 --- 
class NotificationHelper(QObject):
    def __init__(self):
        super().__init__()
        # 명시적으로 부모를 설정하지 않음 (QApplication 종료 시 자동 정리되도록)

    @pyqtSlot(str, str) # 문자열 인자 두 개를 받는 슬롯으로 명시적 정의
    def create_and_show_dialog(self, title, message):
        """메인 GUI 스레드에서 실행될 슬롯: 다이얼로그 생성 및 표시"""
        global _active_dialogs
        try:
            dialog = CustomNotificationDialog(title, message)
            dialog.show()
            
            # 다이얼로그 소멸 시 리스트에서 제거하는 람다 함수 연결
            dialog.destroyed.connect(
                lambda obj=dialog: _active_dialogs.remove(obj) if obj in _active_dialogs else None
            )
            _active_dialogs.append(dialog) # 참조 유지
            
            logging.info(f"커스텀 알림 표시됨 (메인 스레드): {title} - {message}")
        except Exception as e:
            logging.error(f"메인 스레드에서 커스텀 알림 생성/표시 실패: {e}")
# ------------------------------------

# 헬퍼 클래스 인스턴스 (처음 필요할 때 생성)
_notification_helper_instance = None

def show_notification(title: str, message: str):
    """커스텀 알림 창을 스레드 안전하게 표시합니다."""
    global _notification_helper_instance
    
    app_instance = QApplication.instance()
    if app_instance is None:
        logging.warning("QApplication 인스턴스를 찾을 수 없어 커스텀 알림을 표시할 수 없습니다.")
        print(f"[알림] {title}: {message}") 
        return

    # 헬퍼 인스턴스가 없으면 생성 (메인 스레드에 존재하게 됨)
    if _notification_helper_instance is None:
        try:
            _notification_helper_instance = NotificationHelper()
            # 인스턴스가 메인 스레드에 속하도록 보장 (선택적이지만 안전함)
            _notification_helper_instance.moveToThread(app_instance.thread())
            logging.debug("NotificationHelper 인스턴스 생성됨 및 메인 스레드로 이동됨.")
        except Exception as e:
             logging.error(f"NotificationHelper 인스턴스 생성 또는 스레드 이동 실패: {e}")
             print(f"[알림] {title}: {message}") # 실패 시 콘솔 출력
             return

    try:
        # QMetaObject.invokeMethod를 사용하여 헬퍼 인스턴스의 슬롯 호출
        QMetaObject.invokeMethod(
            _notification_helper_instance, # 대상: NotificationHelper 인스턴스
            "create_and_show_dialog",    # 호출할 슬롯 이름 (@pyqtSlot으로 정의된 메서드)
            Qt.QueuedConnection,           # 이벤트 큐를 통해 비동기적으로 호출
            Q_ARG(str, title),             # 전달할 인자 1 (타입 명시)
            Q_ARG(str, message)            # 전달할 인자 2 (타입 명시)
        )

    except Exception as e:
        # invokeMethod 자체에서 예외가 발생하는 경우 (드묾)
        logging.error(f"커스텀 알림 표시 요청 중 예외 발생: {e}")
        print(f"알림: {title} - {message}") 

# 이전 plyer 코드 제거
# def show_notification(title: str, message: str):
#     """시스템 알림을 표시합니다."""
#     try:
#         notification.notify(
#             title=title,
#             message=message,
#             app_name='MyCompanyName.MyProductName.AlarmReminderApp.1', # AppUserModelID 와 일치시켜야 함
#             # app_icon='path/to/icon.ico', # 아이콘 경로 지정 (선택 사항)
#             timeout=10 # 알림 표시 시간 (초)
#         )
#         logging.info(f"알림 표시: {title} - {message}")
#     except Exception as e:
#         # plyer가 특정 시스템에서 작동하지 않을 경우 로그만 남김
#         logging.error(f"알림 표시 실패: {e}")
#         print(f"알림: {title} - {message}") # 콘솔에 대신 출력 