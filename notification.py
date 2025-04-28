import logging
import platform
import os

# PyQt5 QApplication 임포트 (위치 조정을 위해)
from PyQt5.QtWidgets import QApplication # QMessageBox 제거
from PyQt5.QtCore import QMetaObject, Qt, Q_ARG, QObject, pyqtSlot, QUrl, pyqtSignal
# QSoundEffect 대신 QMediaPlayer 사용
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtGui import QIcon

# 새로 만든 커스텀 알림 창 임포트
from custom_notification_dialog import CustomNotificationDialog

# plyer 라이브러리 임포트 시도 (제거)
# try:
#     from plyer import notification
#     PLYER_AVAILABLE = True
# except ImportError:
#     logging.warning("plyer 라이브러리를 찾을 수 없습니다. 시스템 알림 대신 콘솔 출력을 사용합니다.")
#     PLYER_AVAILABLE = False

# 스레드 안전성을 위한 글로벌 변수
_active_dialogs = [] # 생성된 다이얼로그 참조 유지 (이름 유지)
active_sounds = [] # 재생 중인 QMediaPlayer 객체 참조 유지 (이름 통일)

# 앱 아이콘 경로 (main.py와 동일하게)
APP_ICON_PATH = "assets/icon.svg"

# --- 알림 표시를 위한 헬퍼 클래스 --- 
class NotificationHelper(QObject):
    show_notification_signal = pyqtSignal(str, str)
    play_sound_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # 아이콘 로드 시도 및 결과 로깅 
        self.app_icon = QIcon(APP_ICON_PATH)
        if self.app_icon.isNull():
            logging.warning(f"NotificationHelper: 앱 아이콘 로드 실패 - {APP_ICON_PATH}")
        else:
            logging.debug("NotificationHelper: 앱 아이콘 로드 성공.")

    @pyqtSlot(str, str, str) # 슬롯 정의 유지
    def create_and_show_dialog(self, title, message, sound_path):
        """메인 GUI 스레드에서 실행될 슬롯: CustomNotificationDialog 생성, 표시 및 사운드 재생"""
        global _active_dialogs # 전역 리스트 사용 명시
        try:
            # --- CustomNotificationDialog 사용으로 복원 --- 
            dialog = CustomNotificationDialog(title, message)
            # 아이콘 설정 시도 (CustomNotificationDialog에 setWindowIcon 메서드가 있다고 가정)
            if not self.app_icon.isNull():
                try:
                    dialog.setWindowIcon(self.app_icon)
                except AttributeError:
                    logging.warning("CustomNotificationDialog에 setWindowIcon 메서드가 없습니다.")
            
            # 다이얼로그 표시
            dialog.show()
            
            # 다이얼로그 참조 관리 복원
            dialog.destroyed.connect(
                lambda obj=dialog: _active_dialogs.remove(obj) if obj in _active_dialogs else None
            )
            _active_dialogs.append(dialog)
            logging.info(f"CustomNotificationDialog 알림 표시됨 (메인 스레드): {title} - {message}")
            # --- QMessageBox 관련 코드 제거 ---
            
            # 사운드 재생 로직
            if sound_path:
                logging.debug(f"사운드 재생 로직 호출 (QMediaPlayer 사용): {sound_path}") 
                self.play_sound(sound_path)
            else:
                 logging.debug("지정된 사운드 경로 없음.")

        except Exception as e:
            logging.error(f"메인 스레드에서 알림 생성/표시 실패: {e}", exc_info=True)

    def play_sound(self, sound_path):
        """(QMediaPlayer 사용) 지정된 경로의 사운드 파일을 재생합니다."""
        global active_sounds
        try: 
            logging.info(f"사운드 재생 시도 (QMediaPlayer): {sound_path}")
            if not os.path.exists(sound_path):
                logging.error(f"사운드 파일 없음: {sound_path}")
                return

            # --- QMediaPlayer 객체 생성 --- 
            player = QMediaPlayer(self) # 부모를 self로 설정
            active_sounds.append(player) 
            logging.debug(f"  - QMediaPlayer 객체 생성 및 active_sounds 리스트 추가 완료 (총 {len(active_sounds)}개).")

            sound_url = QUrl.fromLocalFile(sound_path)
            logging.debug(f"  - 사운드 URL 생성: {sound_url.toString()}")

            if not sound_url.isValid():
                logging.error(f"유효하지 않은 사운드 URL: {sound_path}")
                if player in active_sounds: active_sounds.remove(player)
                return

            # --- 미디어 콘텐츠 설정 --- 
            media_content = QMediaContent(sound_url)
            player.setMedia(media_content)
            logging.debug(f"  - setMedia({sound_url.toString()}) 호출 완료.")
            # ------------------------

            # --- 시그널 연결 (QMediaPlayer 시그널로 변경) --- 
            logging.debug("  - mediaStatusChanged 연결 시도...")
            player.mediaStatusChanged.connect(self._handle_media_status_changed)
            logging.debug("  - mediaStatusChanged 연결 완료.")
            logging.debug("  - stateChanged 연결 시도...")
            player.stateChanged.connect(self._handle_media_state_changed)
            logging.debug("  - stateChanged 연결 완료.")
            # 테스트 람다 제거
            # -------------------------------------------

            # 볼륨 설정
            logging.debug("  - setVolume 시도...")
            player.setVolume(100) # QMediaPlayer 볼륨은 0-100
            logging.debug("  - setVolume 완료.")

            # 재생은 mediaStatusChanged 핸들러에서 LoadedMedia 상태일 때 시작됨
            # player.play() # 여기서 바로 호출하지 않음

        except Exception as e:
             logging.error(f"사운드 재생(QMediaPlayer) 중 예외 발생: {e}", exc_info=True)
             if 'player' in locals() and player in active_sounds:
                  active_sounds.remove(player)

    # --- 시그널 핸들러 메서드 (QMediaPlayer 용으로 수정) --- 
    def _handle_media_status_changed(self, status):
        """QMediaPlayer의 mediaStatusChanged 시그널을 처리하는 슬롯"""
        global active_sounds 
        sender_player = self.sender() # 시그널을 보낸 QMediaPlayer 객체 가져오기
        if not isinstance(sender_player, QMediaPlayer):
             logging.warning("_handle_media_status_changed: 발신자가 QMediaPlayer가 아님.")
             return

        try: 
            status_map = { 
                QMediaPlayer.UnknownMediaStatus: "UnknownMediaStatus", QMediaPlayer.NoMedia: "NoMedia", 
                QMediaPlayer.LoadingMedia: "LoadingMedia", QMediaPlayer.LoadedMedia: "LoadedMedia", 
                QMediaPlayer.StalledMedia: "StalledMedia", QMediaPlayer.BufferingMedia: "BufferingMedia", 
                QMediaPlayer.BufferedMedia: "BufferedMedia", QMediaPlayer.EndOfMedia: "EndOfMedia", 
                QMediaPlayer.InvalidMedia: "InvalidMedia"
            }
            status_str = status_map.get(status, "Unknown Status Value")
            logging.debug(f"_handle_media_status_changed 호출됨. status: {status_str} ({status}) ")

            current_source = "Unknown Source"
            try: 
                 if hasattr(sender_player, 'currentMedia') and callable(sender_player.currentMedia):
                      media = sender_player.currentMedia()
                      if media and media.canonicalUrl().isValid(): 
                          current_source = media.canonicalUrl().toString()
            except Exception as se:
                 logging.warning(f"핸들러 내에서 sender_player.currentMedia() 호출 오류: {se}")

            if status == QMediaPlayer.LoadingMedia:
                logging.debug(f"  - 미디어 로딩 중... ({current_source})")
            elif status == QMediaPlayer.LoadedMedia:
                logging.debug(f"  - 미디어 로딩 완료. 재생 시작! ({current_source})")
                sender_player.play() # 로드 완료 후 재생 시작
            elif status == QMediaPlayer.EndOfMedia:
                 logging.debug(f"  - 미디어 재생 완료 (EndOfMedia). ({current_source})")
                 if sender_player in active_sounds: active_sounds.remove(sender_player)
                 logging.debug(f"  - QMediaPlayer 객체 active_sounds 리스트에서 제거 (EndOfMedia). (남은 개수: {len(active_sounds)}개).")
            elif status in [QMediaPlayer.InvalidMedia, QMediaPlayer.StalledMedia]: # 오류 상태 처리 추가
                 logging.error(f"  - 미디어 오류 발생 ({status_str})! ({current_source})")
                 if sender_player in active_sounds: active_sounds.remove(sender_player)

        except Exception as e:
             logging.error(f"_handle_media_status_changed 핸들러 오류: {e}", exc_info=True)
             if sender_player in active_sounds: active_sounds.remove(sender_player)

    def _handle_media_state_changed(self, state):
        """QMediaPlayer의 stateChanged 시그널을 처리하는 슬롯"""
        global active_sounds 
        sender_player = self.sender()
        if not isinstance(sender_player, QMediaPlayer):
             logging.warning("_handle_media_state_changed: 발신자가 QMediaPlayer가 아님.")
             return
             
        try: 
            state_map = { QMediaPlayer.StoppedState: "StoppedState", QMediaPlayer.PlayingState: "PlayingState", QMediaPlayer.PausedState: "PausedState" }
            state_str = state_map.get(state, "Unknown State Value")
            logging.debug(f"_handle_media_state_changed 호출됨. state: {state_str} ({state})")

            current_source = "Unknown Source"
            try:
                 if hasattr(sender_player, 'currentMedia') and callable(sender_player.currentMedia):
                      media = sender_player.currentMedia()
                      if media and media.canonicalUrl().isValid(): 
                          current_source = media.canonicalUrl().toString()
            except Exception as se:
                 logging.warning(f"핸들러 내에서 sender_player.currentMedia() 호출 오류: {se}")
                 
            if state == QMediaPlayer.StoppedState:
                # EndOfMedia 에서 주로 처리되지만, 여기서도 정리할 수 있음
                # 예를 들어 사용자가 중지했거나 오류로 중지된 경우
                error_str = sender_player.errorString()
                if error_str: # 오류 메시지가 있다면 로깅
                     logging.error(f"  - 재생 중지됨 (오류: {error_str}). ({current_source})")
                else: # 정상 종료 또는 사용자에 의한 중지 등
                     logging.debug(f"  - 재생 중지됨 (StoppedState). ({current_source})")
                 
                # EndOfMedia 상태에서 제거되지 않았다면 여기서 제거
                if sender_player in active_sounds: 
                     active_sounds.remove(sender_player)
                     logging.debug(f"  - QMediaPlayer 객체 active_sounds 리스트에서 제거 (StoppedState). (남은 개수: {len(active_sounds)}개).")
            elif state == QMediaPlayer.PlayingState:
                logging.debug(f"  - 재생 시작됨 또는 계속됨 (PlayingState). ({current_source})")

        except Exception as e:
            logging.error(f"_handle_media_state_changed 핸들러 오류: {e}", exc_info=True)
            if sender_player in active_sounds: active_sounds.remove(sender_player)
    # ---------------------------------------------------------

# 헬퍼 클래스 인스턴스 (처음 필요할 때 생성)
_notification_helper_instance = None

def show_notification(title: str, message: str, sound_path: str = None):
    """커스텀 알림 창을 스레드 안전하게 표시하고, 지정된 경우 사운드를 재생합니다."""
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
            Q_ARG(str, message),           # 전달할 인자 2 (타입 명시)
            Q_ARG(str, sound_path or "")  # 전달할 인자 3 (사운드 경로, 없으면 빈 문자열)
        )

    except Exception as e:
        # invokeMethod 자체에서 예외가 발생하는 경우 (드묾)
        logging.error(f"커스텀 알림 표시 요청 중 예외 발생: {e}")
        print(f"알림: {title} - {message}") 

# 앱 종료 시 모든 사운드 중지 및 정리 (QMediaPlayer 용으로 수정)
def cleanup_sounds():
    global active_sounds 
    logging.debug(f"애플리케이션 종료 전 QMediaPlayer 정리 시작 (정리할 플레이어 {len(active_sounds)}개)")
    for player in list(active_sounds): # 복사본으로 반복
        try:
            if player.state() == QMediaPlayer.PlayingState:
                player.stop() # stop 메서드 호출
            if player in active_sounds:
                 active_sounds.remove(player)
        except Exception as e:
            logging.error(f"QMediaPlayer 정리 중 오류: {e}", exc_info=True)
    logging.debug("QMediaPlayer 정리 완료.")

# NotificationHelper 인스턴스 생성 
notification_helper = NotificationHelper()

# QApplication 종료 시 cleanup_sounds 함수 호출 연결
# main.py의 if __name__ == '__main__': 블록 마지막 app.exec_() 전에 연결 필요
# 예: app.aboutToQuit.connect(cleanup_sounds)

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