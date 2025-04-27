import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer

class CustomNotificationDialog(QDialog):
    """커스텀 알림 대화 상자 클래스"""
    def __init__(self, title, message, timeout=5000, parent=None): # 기본 타임아웃 5초
        super().__init__(parent)
        
        # --- 창 설정 ---
        self.setWindowTitle("Notification") # 창 제목 설정 (선택 사항)
        # 항상 위에 표시 & 프레임 없는 창 & 작업 표시줄 아이콘 숨김
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        # self.setAttribute(Qt.WA_TranslucentBackground) # 배경 투명 속성 제거 (주석 처리)
        self.setAttribute(Qt.WA_DeleteOnClose) # 닫힐 때 메모리에서 제거

        # --- 레이아웃 및 위젯 ---
        layout = QVBoxLayout(self)
        
        # 스타일시트를 이용해 배경색, 테두리 등 꾸미기 (선택 사항)
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(50, 50, 50); /* 불투명 회색 배경 */
                border: 1px solid #555;
                border-radius: 10px;
            }
            QLabel {
                color: white; /* 흰색 텍스트 */
                padding: 10px;
            }
            QPushButton {
                color: white;
                background-color: #007bff; /* 파란색 버튼 */
                border: none;
                padding: 5px 10px;
                border-radius: 5px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3; /* 호버 시 어두운 파란색 */
            }
        """)

        title_label = QLabel(f"<b>{title}</b>") # 제목 (굵게)
        title_label.setAlignment(Qt.AlignCenter)
        
        message_label = QLabel(message) # 메시지
        message_label.setWordWrap(True) # 자동 줄 바꿈
        message_label.setAlignment(Qt.AlignCenter)

        # 닫기 버튼 추가
        close_button = QPushButton("OK") # 버튼 텍스트 "OK"로 변경
        close_button.clicked.connect(self.accept) # 클릭 시 accept 슬롯 호출 (Dialog 종료)

        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addWidget(close_button, alignment=Qt.AlignCenter) # 버튼을 레이아웃에 추가하고 중앙 정렬

        self.setLayout(layout)

        # --- 위치 조정 (화면 중앙) ---
        # 주 화면의 사용 가능한 영역 정보를 가져옵니다.
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        
        # 위젯 내용에 맞게 크기 조절 (더 정확한 크기 계산 위함)
        self.adjustSize()
        dialog_width = self.width()
        dialog_height = self.height()

        # 화면 중앙 좌표 계산
        x_pos = (screen_geometry.width() - dialog_width) // 2
        y_pos = (screen_geometry.height() - dialog_height) // 2
        # 계산된 중앙 위치로 이동
        self.move(x_pos, y_pos)

        # --- 자동 닫기 타이머 제거 ---
        # if timeout > 0:
        #     QTimer.singleShot(timeout, self.close) # 지정된 시간 후 자동으로 닫기

if __name__ == '__main__':
    # 테스트용 코드
    app = QApplication(sys.argv)
    
    # 테스트 알림 생성 및 표시
    notification_dialog = CustomNotificationDialog("Test Title", "This is a test notification message.")
    notification_dialog.show()
    
    sys.exit(app.exec_()) 