import sys
import logging
import os # os 모듈 임포트
from typing import List, Callable, Optional, Set
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QComboBox, QPushButton, QListWidget, 
    QMessageBox, QListWidgetItem, QFrame, QSizePolicy, QDesktopWidget, QButtonGroup,
    QListView, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QUrl
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtMultimedia import QSoundEffect

from alarm import Alarm, WEEKDAYS

class AlarmApp(QWidget):
    # 알람 목록 변경 시 메인 로직에 알리기 위한 시그널
    alarms_updated = pyqtSignal(list)
    alarm_deleted = pyqtSignal(str) # 삭제된 알람 ID 전달

    def __init__(self, alarms: List[Alarm]):
        super().__init__()
        self.alarms = alarms
        self.selected_alarm: Optional[Alarm] = None
        self.edit_mode = False
        self.day_buttons: List[QPushButton] = [] # 요일 버튼 리스트
        self.selected_sound_path: Optional[str] = None # UI 임시 저장용 경로 다시 추가

        self.initUI()
        self.update_alarm_listwidget()

    def initUI(self):
        self.setWindowTitle("AlarmReminderApp") # 띄어쓰기 제거
        self.resize(600, 550) # 너비와 높이 증가
        self.setMinimumSize(600, 550) # 최소 너비와 높이 설정
        self.center() # 화면 중앙으로 이동시키는 메서드 호출
        
        # --- 창 아이콘 설정 --- 
        app_icon = QIcon("assets/icon.svg")
        if not app_icon.isNull():
             self.setWindowIcon(app_icon)
             print("애플리케이션 아이콘 설정 완료: assets/icon.svg")
        else:
             print("경고: assets/icon.svg 파일을 찾을 수 없거나 유효하지 않습니다.")
        # ---------------------

        self.setStyleSheet("""
            QWidget { 
                background-color: #f0f0f0; 
                font-family: Helvetica; 
                font-size: 10pt; 
            }
            QLabel { background-color: transparent; }
            /* QComboBox 스타일 복원 (padding 제외, min-width 추가) */
            QLineEdit, QComboBox { 
                /* padding: 5px; */ /* 패딩 제외 */
                border: 1px solid #c0c0c0; 
                border-radius: 3px; 
                background-color: white;
                min-width: 40px; /* 최소 너비 지정 */
            }
            QPushButton { 
                padding: 6px 10px; 
                border: 1px solid #b0b0b0; 
                border-radius: 3px; 
                background-color: #e0e0e0; 
            }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #c0c0c0; }
            QPushButton:disabled { background-color: #f5f5f5; color: #a0a0a0; }
            QListWidget { 
                border: 1px solid #c0c0c0; 
                border-radius: 3px; 
                background-color: white;
                font-family: Consolas; /* 고정폭 폰트 */
                font-size: 10pt;
            }
            QListWidget::item:selected { background-color: #d0e4f8; color: black; }
            QFrame#formFrame, QFrame#listFrame { /* Frame 구분선 */
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 10px; /* 프레임 간 간격 */
            }
            QLabel#frameTitle { /* 프레임 제목 스타일 */
                font-weight: bold;
                font-size: 11pt;
                margin-bottom: 5px;
                color: #333;
            }
            QPushButton#dayButton { /* 요일 버튼 기본 스타일 */
                padding: 5px 8px;
                font-size: 9pt;
                min-width: 40px; /* 최소 너비 */
                background-color: #f8f8f8;
                border: 1px solid #c0c0c0;
            }
            QPushButton#dayButton:checked { /* 선택된 요일 버튼 스타일 변경 */
                background-color: #d9f7d9; /* 연한 녹색 */
                border: 1px solid #9fdf9f; /* 조금 더 진한 녹색 테두리 */
                font-weight: bold;
            }
            /* --- 사운드 옵션 버튼 스타일 추가 --- */
            QPushButton#soundOptionButton { /* 사운드 버튼 기본 스타일 */
                padding: 5px 8px;
                font-size: 9pt;
                background-color: #f8f8f8;
                border: 1px solid #c0c0c0;
            }
            QPushButton#soundOptionButton:checked { /* 선택된 사운드 버튼 스타일 */
                background-color: #d9f7d9; /* 연한 녹색 */
                border: 1px solid #9fdf9f; /* 조금 더 진한 녹색 테두리 */
                font-weight: bold;
            }
            /* ------------------------------------ */
            /* --- Save Alarm 버튼 스타일 추가 --- */
            QPushButton#saveButton {
                background-color: #3498db; /* 파란색 배경 */
                color: white; /* 흰색 텍스트 */
                border: 1px solid #2980b9;
                font-weight: bold;
            }
            QPushButton#saveButton:hover {
                background-color: #2980b9; /* 조금 더 진한 파랑 */
            }
            QPushButton#saveButton:pressed {
                background-color: #1f618d; /* 더 진한 파랑 */
            }
            QPushButton#saveButton:disabled { /* 비활성화 시 스타일 */
                 background-color: #a9cce3;
                 border-color: #a9cce3;
                 color: #eaf2f8;
            }
            /* --- Save Alarm 버튼 스타일 끝 --- */
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15) # 전체 여백

        # --- 알람 추가/수정 섹션 --- 
        form_frame = QFrame(self)
        form_frame.setObjectName("formFrame")
        form_layout_wrapper = QVBoxLayout(form_frame) # 제목과 폼 레이아웃을 포함할 래퍼
        
        self.form_title_label = QLabel("Add Alarm") # 동적으로 변경될 제목
        self.form_title_label.setObjectName("frameTitle")
        form_layout_wrapper.addWidget(self.form_title_label)
        
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 5, 0, 0) # 폼 내부 여백 (상단만)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(8)

        self.title_edit = QLineEdit()
        form_layout.addRow("Title:", self.title_edit)

        # 시간 선택
        time_layout = QHBoxLayout()
        hours = [f"{h:02d}" for h in range(24)]
        minutes = [f"{m:02d}" for m in range(60)] # 1분 단위
        self.hour_combo = QComboBox()
        self.hour_combo.addItems(hours)
        self.hour_combo.setCurrentText("07")
        self.hour_combo.setMaxVisibleItems(10) # 최대 표시 항목 수 다시 10으로
        self.minute_combo = QComboBox()
        self.minute_combo.addItems(minutes)
        self.minute_combo.setCurrentText("00")
        self.minute_combo.setMaxVisibleItems(10) # 최대 표시 항목 수 다시 10으로
        time_layout.addWidget(self.hour_combo)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(self.minute_combo)
        time_layout.addStretch(1)
        form_layout.addRow("Time:", time_layout)

        # --- 반복 설정: 요일 버튼 --- 
        day_button_layout = QHBoxLayout()
        day_button_layout.setSpacing(5) # 버튼 간 간격
        self.day_buttons = [] # 버튼 객체 저장 리스트 초기화
        for i, day_name in enumerate(WEEKDAYS):
            button = QPushButton(day_name)
            button.setObjectName("dayButton") # 스타일 적용 위한 ID
            button.setCheckable(True) # 클릭 시 상태 유지
            day_button_layout.addWidget(button)
            self.day_buttons.append(button)
        day_button_layout.addStretch(1)
        form_layout.addRow("Repeat on:", day_button_layout)
        # --- 요일 버튼 끝 --- 
        
        # --- 사운드 설정 버튼 (폼 내부) --- 
        sound_layout = QHBoxLayout()
        self.form_sound_button = QPushButton("Sound 🔊")
        self.form_sound_button.setObjectName("soundOptionButton") # 객체 이름 설정
        self.form_sound_button.setCheckable(True) # Checkable 설정
        self.form_sound_button.clicked.connect(self.select_sound_file)
        
        self.clear_sound_button = QPushButton("No Sound 🔇") # 텍스트 변경
        self.clear_sound_button.setObjectName("soundOptionButton") # 객체 이름 설정
        self.clear_sound_button.setCheckable(True) # Checkable 설정
        self.clear_sound_button.clicked.connect(self.clear_selected_sound) 
        # self.clear_sound_button.setEnabled(False) # 초기 활성화 상태 제거 (선택 상태로 관리)

        # 버튼 그룹으로 묶어 하나만 선택되도록 함
        self.sound_button_group = QButtonGroup(self)
        self.sound_button_group.setExclusive(True) # 배타적 선택
        self.sound_button_group.addButton(self.clear_sound_button)
        self.sound_button_group.addButton(self.form_sound_button)
        # 초기 상태: No Sound 선택
        self.clear_sound_button.setChecked(True)
        
        sound_layout.addWidget(self.clear_sound_button) 
        sound_layout.addWidget(self.form_sound_button) 
        sound_layout.addStretch(1)
        form_layout.addRow("Sound:", sound_layout)
        # ---------------------------------------
        
        form_layout_wrapper.addLayout(form_layout)

        # 저장/취소 버튼
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Alarm")
        self.save_button.setObjectName("saveButton")
        self.save_button.clicked.connect(self.save_alarm)
        self.cancel_button = QPushButton("Cancel Edit")
        self.cancel_button.clicked.connect(self.cancel_edit)
        self.cancel_button.setVisible(False) # 처음엔 숨김
        button_layout.addStretch(1)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        form_layout_wrapper.addLayout(button_layout)

        main_layout.addWidget(form_frame)

        # --- 등록된 알람 목록 섹션 --- 
        list_frame = QFrame(self)
        list_frame.setObjectName("listFrame")
        list_layout_wrapper = QVBoxLayout(list_frame)
        
        list_title_label = QLabel("Registered Alarms")
        list_title_label.setObjectName("frameTitle")
        list_layout_wrapper.addWidget(list_title_label)
        
        self.alarm_listwidget = QListWidget()
        self.alarm_listwidget.currentItemChanged.connect(self.on_alarm_select)
        self.alarm_listwidget.itemDoubleClicked.connect(self.toggle_alarm_enabled)
        list_layout_wrapper.addWidget(self.alarm_listwidget)

        # 목록 조작 버튼 (Sound 버튼 제거)
        list_button_layout = QHBoxLayout()
        self.edit_button = QPushButton("Edit ✏️")
        self.edit_button.clicked.connect(self.edit_alarm)
        self.edit_button.setEnabled(False)
        self.delete_button = QPushButton("Delete 🗑️")
        self.delete_button.clicked.connect(self.delete_alarm)
        self.delete_button.setEnabled(False)
        self.toggle_button = QPushButton("Toggle 🔔/🔕")
        self.toggle_button.clicked.connect(self.toggle_alarm_enabled)
        self.toggle_button.setEnabled(False)
        list_button_layout.addWidget(self.edit_button)
        list_button_layout.addWidget(self.delete_button)
        list_button_layout.addWidget(self.toggle_button)
        list_button_layout.addStretch(1)
        list_layout_wrapper.addLayout(list_button_layout)
        
        main_layout.addWidget(list_frame)

    def center(self):
        """창을 화면 중앙으로 이동시킵니다."""
        qr = self.frameGeometry() # 창의 프레임 형상 정보 (위치, 크기)
        # 사용 가능한 화면 영역의 중앙점을 구함
        cp = QApplication.primaryScreen().availableGeometry().center() 
        qr.moveCenter(cp) # 창의 중앙을 화면 중앙으로 이동
        self.move(qr.topLeft()) # 계산된 왼쪽 상단 좌표로 창 이동

    def update_alarm_listwidget(self):
        """리스트 위젯을 현재 알람 목록으로 업데이트합니다."""
        self.alarm_listwidget.clear()
        sorted_alarms = sorted(self.alarms, key=lambda a: a.time_str)
        logging.debug(f"Updating list widget with {len(sorted_alarms)} alarms.")
        for alarm in sorted_alarms:
            logging.debug(f"  - Creating item for: {alarm} (ID: {alarm.id}, Sound Path: {alarm.sound_path})") 
            item = QListWidgetItem(str(alarm))
            item.setData(Qt.UserRole, alarm) 
            if not alarm.enabled:
                item.setForeground(QColor('grey'))
            self.alarm_listwidget.addItem(item)
        self.clear_selection()
        logging.debug("알람 리스트 위젯 업데이트 완료.")

    def clear_selection(self):
        """리스트 위젯 선택 해제 및 관련 버튼 비활성화"""
        self.alarm_listwidget.setCurrentItem(None) 
        self.selected_alarm = None
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.toggle_button.setEnabled(False)
        logging.debug("리스트 위젯 선택 해제됨.")

    def on_alarm_select(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """리스트 위젯에서 알람을 선택했을 때 호출됩니다."""
        if current_item is None:
            self.selected_alarm = None
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.toggle_button.setEnabled(False)
            return

        self.selected_alarm = current_item.data(Qt.UserRole) 
        if self.selected_alarm:
            self.edit_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.toggle_button.setEnabled(True)
            logging.debug(f"알람 선택됨: {self.selected_alarm}")
        else:
            logging.error("선택된 아이템에서 알람 데이터를 가져올 수 없습니다.")
            self.clear_selection()
            
    def validate_input(self) -> bool:
        """입력값 유효성 검사"""
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Input Error", "Alarm title cannot be empty.")
            return False
        # 시간 형식은 콤보박스로 제한되므로 별도 검사 불필요
        return True

    def save_alarm(self):
        """알람을 저장 (추가 또는 수정)합니다."""
        if not self.validate_input():
            return

        title = self.title_edit.text().strip()
        time_str = f"{self.hour_combo.currentText()}:{self.minute_combo.currentText()}"
        selected_days: Set[int] = set()
        for i, button in enumerate(self.day_buttons):
            if button.isChecked():
                selected_days.add(i)
        
        # --- UI의 임시 경로를 알람 객체에 저장 --- 
        sound_path_to_save = self.selected_sound_path
        # ----------------------------------------

        if self.edit_mode and self.selected_alarm:
            # 수정 모드
            logging.info(f"알람 수정 시작: ID {self.selected_alarm.id}, 이전 값: {self.selected_alarm}")
            self.selected_alarm.title = title
            self.selected_alarm.time_str = time_str
            self.selected_alarm.selected_days = selected_days
            self.selected_alarm.sound_path = sound_path_to_save # sound_path 업데이트
            logging.info(f"알람 수정 완료: ID {self.selected_alarm.id}, 새 값: {self.selected_alarm}")
        else:
            # 추가 모드
            new_alarm = Alarm(
                title=title, 
                time_str=time_str, 
                selected_days=selected_days,
                sound_path=sound_path_to_save # 새 알람에 sound_path 저장
            )
            self.alarms.append(new_alarm)
            logging.info(f"새 알람 추가됨: {new_alarm}")

        self.alarms_updated.emit(self.alarms) 
        self.update_alarm_listwidget()
        self.reset_form() 
        self.cancel_edit() 

    def edit_alarm(self):
        """선택된 알람을 수정 모드로 전환합니다."""
        if not self.selected_alarm:
            return
        
        logging.info(f"알람 수정 모드 진입: {self.selected_alarm}")
        self.title_edit.setText(self.selected_alarm.title)
        hour, minute = self.selected_alarm.time_str.split(':')
        self.hour_combo.setCurrentText(hour)
        self.minute_combo.setCurrentText(minute)
        for i, button in enumerate(self.day_buttons):
            button.setChecked(i in self.selected_alarm.selected_days)
        
        # --- 알람 객체의 사운드 경로 UI 임시 변수에 로드, 버튼 텍스트 및 선택 상태 업데이트 --- 
        alarm_sound_path = self.selected_alarm.sound_path
        self.selected_sound_path = alarm_sound_path 
        if alarm_sound_path:
            file_name = os.path.basename(alarm_sound_path)
            self.form_sound_button.setText(f"Sound ({file_name}) 🔊") 
            # self.clear_sound_button.setEnabled(True) # Enabled 대신 Checked 사용
            self.form_sound_button.setChecked(True) # Sound 버튼 선택
        else:
            self.form_sound_button.setText("Sound 🔊") 
            # self.clear_sound_button.setEnabled(False) # Enabled 대신 Checked 사용
            self.clear_sound_button.setChecked(True) # No Sound 버튼 선택
        # -------------------------------------------------------------------------------------

        self.edit_mode = True
        self.form_title_label.setText("Edit Alarm")
        self.save_button.setText("Update Alarm")
        self.cancel_button.setVisible(True)
        self.alarm_listwidget.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.toggle_button.setEnabled(False)

    def cancel_edit(self):
        """수정 모드를 취소하고 폼을 초기화합니다."""
        if not self.edit_mode: 
             return
        logging.info("수정 모드 취소됨.")
        self.reset_form() 
        self.edit_mode = False
        self.form_title_label.setText("Add Alarm")
        self.save_button.setText("Save Alarm")
        self.cancel_button.setVisible(False)
        self.alarm_listwidget.setEnabled(True) 
        self.on_alarm_select(self.alarm_listwidget.currentItem(), None)

    def delete_alarm(self):
        """선택된 알람을 삭제합니다."""
        if not self.selected_alarm:
            return

        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete the alarm '{self.selected_alarm.title}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            logging.info(f"알람 삭제 시작: {self.selected_alarm}")
            deleted_alarm_id = self.selected_alarm.id
            self.alarms.remove(self.selected_alarm)
            logging.info(f"알람 삭제 완료: ID {deleted_alarm_id}")
            self.alarm_deleted.emit(deleted_alarm_id) # 삭제된 ID 시그널 발생
            self.update_alarm_listwidget()
            self.reset_form()
        else:
            logging.info(f"알람 삭제 취소됨: {self.selected_alarm}")

    def toggle_alarm_enabled(self, item: Optional[QListWidgetItem] = None):
        """선택된 알람의 활성화 상태를 토글합니다."""
        target_alarm = None
        if item: # 더블클릭 시
            target_alarm = item.data(Qt.UserRole)
        elif self.selected_alarm: # 버튼 클릭 시
            target_alarm = self.selected_alarm
        
        if not target_alarm:
            logging.warning("토글할 알람을 찾을 수 없습니다.")
            return

        target_alarm.enabled = not target_alarm.enabled
        logging.info(f"알람 활성화 상태 변경: {target_alarm.title} -> {'Enabled' if target_alarm.enabled else 'Disabled'}")
        self.alarms_updated.emit(self.alarms) # 변경 사항 저장 요청
        self.update_alarm_listwidget() # 목록 업데이트 (아이콘 및 색상 변경)

        # 토글 후에도 선택 유지 (리스트 위젯에서 해당 아이템 다시 찾기)
        for i in range(self.alarm_listwidget.count()):
            list_item = self.alarm_listwidget.item(i)
            if list_item.data(Qt.UserRole) == target_alarm:
                self.alarm_listwidget.setCurrentItem(list_item) # 다시 선택
                self.on_alarm_select(list_item, None) # 버튼 상태 업데이트
                break

    def reset_form(self):
        """입력 폼을 초기 상태로 리셋합니다."""
        self.title_edit.clear()
        self.hour_combo.setCurrentText("07")
        self.minute_combo.setCurrentText("00")
        for button in self.day_buttons:
            button.setChecked(False)
        # --- UI 임시 사운드 선택 상태 및 버튼 초기화 --- 
        self.selected_sound_path = None
        self.form_sound_button.setText("Sound 🔊") 
        # self.clear_sound_button.setEnabled(False) # Enabled 대신 Checked 사용
        self.clear_sound_button.setChecked(True) # No Sound 버튼을 기본 선택으로
        # -----------------------------------------
        self.clear_selection() 
        logging.debug("입력 폼 리셋됨.")

    def closeEvent(self, event):
        """QWidget.close() 또는 창 닫기 버튼 클릭 시 호출됨"""
        # 여기서 종료 확인 메시지를 표시하고 스케줄러 중지 로직 연결 가능
        # 단, main.py에서 QApplication 종료 전에 처리하는 것이 더 일반적임
        logging.debug("AlarmApp 위젯 closeEvent 호출됨.")
        # event.accept() # 종료 허용
        # event.ignore() # 종료 무시
        super().closeEvent(event) # 기본 동작 수행

    def select_sound_file(self):
        """폼 내부 Sound 버튼 클릭 시 파일 선택하고 UI 임시 변수에 저장."""
        # Sound 버튼 클릭 시 -> 파일을 선택하면 Sound 버튼이 선택됨
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Alarm Sound", "", "Sound Files (*.mp3 *.wav);;All Files (*)", options=options
        )
        
        if file_path:
            self.selected_sound_path = file_path
            logging.info(f"폼에서 사운드 파일 선택됨 (임시 저장): {file_path}")
            file_name = os.path.basename(file_path)
            self.form_sound_button.setText(f"Sound ({file_name}) 🔊")
            # self.clear_sound_button.setEnabled(True) # Enabled 대신 Checked 사용
            self.form_sound_button.setChecked(True) # Sound 버튼 선택 상태로
        else:
            logging.info("폼에서 사운드 파일 선택 취소됨.")
            # 파일 선택 취소 시: 
            # - 만약 이전에 선택된 사운드가 없었다면 No Sound 선택 유지
            # - 만약 이전에 선택된 사운드가 있었다면 해당 사운드 선택 유지 (텍스트는 유지됨)
            # 즉, 파일 선택 취소 시에는 버튼 선택 상태 변경 없음
            pass

    def clear_selected_sound(self):
        """폼에서 선택된 사운드를 제거(None으로 설정)합니다."""
        # No Sound 버튼 클릭 시 -> No Sound 버튼이 선택됨
        # if self.selected_sound_path is None:
        #      return # 이미 No Sound가 선택된 상태일 수 있으므로 이 체크 제거
        
        logging.info("폼에서 선택된 사운드 제거됨.")
        self.selected_sound_path = None
        self.form_sound_button.setText("Sound 🔊") # 기본 텍스트로 복원
        # self.clear_sound_button.setEnabled(False) # Enabled 대신 Checked 사용
        self.clear_sound_button.setChecked(True) # No Sound 버튼 선택 상태로

# 테스트용 코드 (ui.py 직접 실행 시)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 테스트용 알람 데이터
    test_alarms = [
        Alarm(title="Morning Exercise", time_str="07:30", selected_days={0, 1, 2, 3, 4}), # 월~금
        Alarm(title="Weekend Jogging", time_str="09:00", selected_days={5, 6}), # 토, 일
        Alarm(title="Meeting", time_str="14:00", selected_days={2}, enabled=False) # 수요일, 비활성
    ]
    ex = AlarmApp(test_alarms)
    
    # 시그널 연결 (테스트용)
    def handle_update(alarms_list):
        print("--- Alarms Updated Signal Received ---")
        # print(alarms_list)
    def handle_delete(deleted_id):
        print(f"--- Alarm Deleted Signal Received: {deleted_id} ---")
        
    ex.alarms_updated.connect(handle_update)
    ex.alarm_deleted.connect(handle_delete)
    
    ex.show()
    sys.exit(app.exec_()) 