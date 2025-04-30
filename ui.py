import sys
import logging
import os # os 모듈 임포트
from typing import List, Callable, Optional, Set
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QComboBox, QPushButton, QListWidget, 
    QMessageBox, QListWidgetItem, QFrame, QSizePolicy, QDesktopWidget, QButtonGroup,
    QListView, QFileDialog, QSystemTrayIcon
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QUrl, QTime
from PyQt5.QtGui import QColor, QFont, QIcon, QDesktopServices
from PyQt5.QtMultimedia import QSoundEffect

from alarm import Alarm, WEEKDAYS

# main.py 에서 resource_path 함수 가져오기
# 순환 참조를 피하기 위해 함수 정의를 복사하거나 별도 모듈로 분리하는 것이 더 좋을 수 있음
# 여기서는 임시로 main을 import 시도 (실행 시점에 main 모듈이 이미 로드되어 있어야 함)
# try:
#     from __main__ import resource_path # 패키징 시 main이 __main__으로 실행될 수 있음
# except ImportError:
#     # 개발 환경 또는 다른 방식으로 실행될 경우 직접 정의 (main.py의 함수와 동일)

# 함수 정의를 직접 포함 (main.py와 동일하게 수정)
import os
import sys
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running in development mode: Use the directory of the current file (__file__)
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class AlarmApp(QWidget):
    # 알람 목록 변경 시 메인 로직에 알리기 위한 시그널
    alarms_updated = pyqtSignal(list)
    alarm_deleted = pyqtSignal(str) # 삭제된 알람 ID 전달

    def __init__(self, alarms: List[Alarm], tray_icon: QSystemTrayIcon, parent=None):
        super().__init__(parent)
        self.alarms = alarms
        self.selected_alarm: Optional[Alarm] = None
        self.edit_mode = False
        self.day_buttons: List[QPushButton] = [] # 요일 버튼 리스트
        self.selected_sound_path: Optional[str] = None # UI 임시 저장용 경로 다시 추가
        self.tray_icon = tray_icon # 트레이 아이콘 저장

        self.initUI()
        self.update_alarm_listwidget()

    def initUI(self):
        self.setWindowTitle("") # 띄어쓰기 제거
        self.resize(600, 700) # 너비와 높이 증가 (높이 700으로 수정)
        self.setMinimumSize(600, 700) # 최소 너비와 높이 설정 (높이 700으로 수정)
        self.center() # 화면 중앙으로 이동시키는 메서드 호출
        
        # --- 창 아이콘 설정 --- 
        # app_icon = QIcon("assets/icon.svg") # 기존 SVG 사용 코드
        app_icon_path = resource_path("assets/icon.ico") # .ico 파일 및 절대 경로 사용
        app_icon = QIcon(app_icon_path)
        if not app_icon.isNull():
             self.setWindowIcon(app_icon)
             # print("애플리케이션 아이콘 설정 완료: ", app_icon_path)
        else:
             # print(f"경고: {app_icon_path} 파일을 찾을 수 없거나 유효하지 않습니다.")
             pass # 최종본에서는 출력 제거
        # ---------------------

        self.setStyleSheet("""
            /* === 기본 위젯 스타일 === */
            QWidget { 
                background-color: #f8f9fa; /* 더 밝은 배경색 */
                font-family: "Segoe UI", Frutiger, "Frutiger Linotype", Univers, Calibri, "Gill Sans", "Gill Sans MT", "Myriad Pro", Myriad, "DejaVu Sans Condensed", "Liberation Sans", "Nimbus Sans L", Tahoma, Geneva, "Helvetica Neue", Helvetica, Arial, sans-serif; /* 선호 폰트 지정 */
                font-size: 10pt; 
                color: #343a40; /* 기본 텍스트 색상 */
            }
            QLabel { 
                background-color: transparent; 
                padding: 2px; /* 레이블 여백 약간 추가 */
            }

            /* === 입력 필드 및 콤보박스 === */
            QLineEdit, QComboBox { 
                padding: 6px 8px; /* 패딩 조정 */
                border: 1px solid #ced4da; /* 연한 테두리 */
                border-radius: 6px; /* 더 둥근 모서리 */
                background-color: #ffffff;
                min-width: 45px; /* 최소 너비 약간 증가 */
                font-size: 10pt;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #80bdff; /* 포커스 시 테두리 색상 */
                /* box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25); /* 부트스트랩 스타일 그림자 (Qt에서는 직접 지원 어려움) */
            }
            QComboBox::drop-down {
                border-left: 1px solid #ced4da;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                width: 20px; /* 드롭다운 버튼 너비 */
            }
            QComboBox::down-arrow {
                /* 이미지 사용 가능: image: url(path/to/arrow.png); */
                 width: 10px; height: 10px; /* 기본 화살표 크기 조정 가능 */
            }
            QComboBox QAbstractItemView { /* 드롭다운 목록 스타일 */
                border: 1px solid #ced4da;
                background-color: white;
                selection-background-color: #e9ecef; /* 선택 항목 배경색 */
                selection-color: #343a40; /* 선택 항목 텍스트 색상 */
                padding: 4px;
            }


            /* === 기본 버튼 === */
            QPushButton { 
                padding: 8px 12px; /* 버튼 패딩 증가 */
                border: 1px solid #adb5bd; /* 버튼 테두리 */
                border-radius: 6px; /* 더 둥근 모서리 */
                background-color: #e9ecef; /* 버튼 기본 배경색 */
                color: #343a40; /* 버튼 텍스트 색상 */
                font-weight: 500; /* 약간 굵게 */
            }
            QPushButton:hover { 
                background-color: #dee2e6; /* 밝은 회색 */
                border-color: #adb5bd;
            }
            QPushButton:pressed { 
                background-color: #ced4da; /* 더 진한 회색 */
                border-color: #adb5bd;
            }
            QPushButton:disabled { 
                background-color: #f1f3f5; 
                color: #adb5bd; 
                border-color: #dee2e6;
            }

            /* === 리스트 위젯 === */
            QListWidget { 
                border: 1px solid #dee2e6; /* 더 연한 테두리 */
                border-radius: 6px; 
                background-color: white;
                font-family: Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace; /* 고정폭 폰트 유지 */
                font-size: 10pt;
                padding: 5px; /* 내부 여백 추가 */
            }
            QListWidget::item {
                padding: 5px 3px; /* 아이템 간 상하 여백 */
                margin: 1px 0; /* 아이템 간 좌우 마진 (선택 시 테두리 보일 공간) */
                border-radius: 4px; /* 아이템 모서리 약간 둥글게 */
            }
            QListWidget::item:selected { 
                background-color: #cfe2ff; /* 부드러운 파란색 */
                color: #0a3678; 
                border: 1px solid #b6d4fe; /* 선택 시 테두리 */
            }
            QListWidget::item:!enabled { /* 비활성화 아이템 */
                 color: #adb5bd;
                 /* background-color: #f8f9fa; /* 약간 다른 배경색 줄 수도 있음 */
            }

            /* === 프레임 스타일 === */
            QFrame#formFrame, QFrame#listFrame { 
                border: 1px solid #e9ecef; /* 매우 연한 테두리 */
                border-radius: 8px; /* 프레임 모서리 둥글게 */
                padding: 15px; /* 프레임 내부 여백 증가 */
                margin-bottom: 15px; /* 프레임 간 간격 증가 */
                background-color: #ffffff; /* 프레임 배경 흰색으로 구분 */
            }
            QLabel#frameTitle { 
                font-weight: 600; /* 제목 굵기 증가 */
                font-size: 12pt; /* 제목 크기 증가 */
                margin-bottom: 10px; /* 제목과 내용 간 간격 증가 */
                color: #495057; /* 제목 색상 약간 변경 */
                border-bottom: 1px solid #dee2e6; /* 제목 아래 구분선 */
                padding-bottom: 5px; /* 구분선과의 간격 */
            }

            /* === 요일 버튼 스타일 === */
            QPushButton#dayButton { 
                padding: 6px 9px; /* 요일 버튼 패딩 */
                font-size: 9pt;
                min-width: 45px; 
                background-color: #f8f9fa; /* 기본 배경 */
                border: 1px solid #ced4da; /* 기본 테두리 */
            }
            QPushButton#dayButton:checked { 
                background-color: #d1e7dd; /* 선택 시 연한 녹색 */
                border-color: #a3cfbb; 
                color: #0a3622;
                font-weight: 600;
            }
            QPushButton#dayButton:hover:!checked { /* 선택 안됐을때 hover */
                 background-color: #e9ecef;
            }

            /* === 사운드 옵션 버튼 스타일 === */
            QPushButton#soundOptionButton { 
                padding: 6px 9px;
                font-size: 9pt;
                border: 1px solid #ced4da;
            }
            QPushButton#soundOptionButton:checked { 
                background-color: #cfe2ff; /* 선택 시 연한 파랑 */
                border-color: #a6c8ff;
                color: #052c65;
                font-weight: 600;
            }
            QPushButton#soundOptionButton:!checked { /* 선택 안된 버튼 */
                 background-color: #f8f9fa;
                 color: #495057;
            }
             QPushButton#soundOptionButton:hover:!checked { /* 선택 안됐을때 hover */
                 background-color: #e9ecef;
            }

            /* === 저장/업데이트 버튼 (Primary) === */
            QPushButton#saveButton {
                background-color: #0d6efd; /* 부트스트랩 파란색 */
                color: white; 
                border: 1px solid #0d6efd;
                font-weight: 600; /* 텍스트 강조 */
            }
            QPushButton#saveButton:hover {
                background-color: #0b5ed7; 
                border-color: #0a58ca;
            }
            QPushButton#saveButton:pressed {
                background-color: #0a58ca; 
                border-color: #0a53be;
            }
            QPushButton#saveButton:disabled { 
                 background-color: #6ea8fe;
                 border-color: #6ea8fe;
                 color: #e7f1ff;
            }
            
            /* === 취소 버튼 (Secondary) === */
            QPushButton#cancelButton { /* cancel_button 객체 이름 설정 필요 */
                background-color: #6c757d; /* 회색 계열 */
                color: white;
                border-color: #6c757d;
            }
             QPushButton#cancelButton:hover {
                 background-color: #5c636a;
                 border-color: #565e64;
             }
             QPushButton#cancelButton:pressed {
                 background-color: #565e64;
                 border-color: #51585e;
             }

            /* === 목록 조작 버튼 (Edit, Delete, Toggle) === */
            QPushButton#editButton, QPushButton#deleteButton, QPushButton#toggleButton, QPushButton#feedbackButton { /* 각 버튼 객체 이름 설정 필요 + feedbackButton 추가 */
                 font-size: 9pt;
                 padding: 5px 8px; /* 동일한 패딩 적용 */
            }
            QPushButton#editButton {
                /* 필요시 개별 스타일 */
            }
             QPushButton#deleteButton {
                 background-color: #f8d7da; /* 연한 빨강 배경 */
                 color: #58151c;
                 border-color: #f1aeb5;
             }
             QPushButton#deleteButton:hover {
                 background-color: #f1aeb5;
                 border-color: #ee959e;
                 color: #411015;
             }
            QPushButton#toggleButton {
                /* 필요시 개별 스타일 */
            }
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
        self.form_sound_button.setMinimumWidth(120) # 최소 너비 설정 추가
        # 수평 크기 정책 설정 제거
        # self.form_sound_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.form_sound_button.clicked.connect(self.select_sound_file)
        
        self.clear_sound_button = QPushButton("No Sound 🔇") # 텍스트 변경
        self.clear_sound_button.setObjectName("soundOptionButton") # 객체 이름 설정
        self.clear_sound_button.setCheckable(True) # Checkable 설정
        # 크기 정책 설정 제거
        # self.clear_sound_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed) 
        self.clear_sound_button.setMinimumWidth(120) # 최소 너비 120으로 증가
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
        sound_layout.addStretch(1) # 스트레치 다시 활성화
        form_layout.addRow("Sound:", sound_layout)
        # ---------------------------------------
        
        form_layout_wrapper.addLayout(form_layout)

        # 저장/취소 버튼
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Alarm")
        self.save_button.setObjectName("saveButton")
        self.save_button.clicked.connect(self.save_alarm)
        self.cancel_button = QPushButton("Cancel Edit")
        self.cancel_button.setObjectName("cancelButton")
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

        # 목록 조작 버튼
        list_button_layout = QHBoxLayout()
        self.edit_button = QPushButton("Edit ✏️")
        self.edit_button.setObjectName("editButton")
        self.edit_button.clicked.connect(self.edit_alarm)
        self.edit_button.setEnabled(False)
        self.delete_button = QPushButton("Delete 🗑️")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.clicked.connect(self.delete_alarm)
        self.delete_button.setEnabled(False)
        self.toggle_button = QPushButton("Toggle 🔔/🔕")
        self.toggle_button.setObjectName("toggleButton")
        self.toggle_button.clicked.connect(self.toggle_alarm_enabled)
        self.toggle_button.setEnabled(False)
        list_button_layout.addWidget(self.edit_button)
        list_button_layout.addWidget(self.delete_button)
        list_button_layout.addWidget(self.toggle_button)
        list_button_layout.addStretch(1) # 기존 버튼과 새 버튼 사이에 공간 추가

        # --- 피드백 버튼 추가 ---
        self.feedback_button = QPushButton("💬") # 이모지 사용
        self.feedback_button.setObjectName("feedbackButton") # 객체 이름 설정
        self.feedback_button.setToolTip("Send Feedback") # 툴팁 설정
        # 버튼 크기 고정 (선택 사항, 너무 커지지 않도록)
        # self.feedback_button.setFixedSize(QSize(40, 40)) # 예시 크기 -> 주석 처리하여 높이 맞춤
        # self.feedback_button.setStyleSheet("font-size: 14pt;") # 이모지 크기 조절
        self.feedback_button.clicked.connect(self.open_feedback_link) # 클릭 시그널 연결
        list_button_layout.addWidget(self.feedback_button)
        # -----------------------

        list_layout_wrapper.addLayout(list_button_layout)

        main_layout.addWidget(list_frame)

        # --- 스트레치 비율 설정 --- 
        main_layout.setStretchFactor(form_frame, 1) # Add Alarm 섹션 비율
        main_layout.setStretchFactor(list_frame, 2) # Registered Alarms 섹션 비율 (더 크게)
        # ---------------------------

        self.setLayout(main_layout)
        self.setWindowTitle('Alarm Reminder App')
        # self.setWindowIcon(QIcon('assets/icon.svg')) # 윈도우 아이콘 설정 (중복 제거: initUI 시작 부분에서 .ico로 이미 설정함)
        # self.setGeometry(300, 300, 600, 400) # 창 크기 및 위치 설정 (center() 호출 후 실행되어 중앙 정렬 무시함)

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
        """창 닫기 버튼 클릭 시 트레이로 최소화"""
        logging.info("Close button clicked. Hiding window to tray.")
        event.ignore()  # 창 닫기 이벤트를 무시
        self.hide()     # 창 숨기기
        # 트레이 아이콘 메시지 표시 (정보, 제목, 내용, 아이콘, 시간(ms))
        self.tray_icon.showMessage(
            "Application Minimized",
            "AlarmReminderPAAK is running in the background.",
            QSystemTrayIcon.Information, # 메시지 아이콘 타입
            2000 # 2초 동안 표시
        )

    def select_sound_file(self):
        """사운드 파일 선택 다이얼로그를 열고 선택된 파일 경로를 저장합니다."""
        # 기본 폴더 설정 (예: 현재 작업 디렉토리)
        # 또는 마지막으로 사용했던 폴더 등으로 설정할 수 있습니다.
        default_dir = os.getcwd() 
        
        # 파일 필터 (wav, mp3 지원 예시)
        file_filter = "Sound Files (*.wav *.mp3);;All Files (*)"
        
        # 파일 선택 다이얼로그 열기
        fileName, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Sound File", 
            default_dir, 
            file_filter
        )
        
        if fileName: # 파일이 선택된 경우
            logging.debug(f"사운드 파일 선택됨: {fileName}")
            self.selected_sound_path = fileName
            # 버튼 텍스트에 파일명 표시 (경로는 제외하고 파일명만)
            self.form_sound_button.setText(f"🔊 {os.path.basename(fileName)}")
            self.form_sound_button.setChecked(True) # 사운드 버튼 선택 상태로
        else: # 파일 선택이 취소된 경우
            logging.debug("사운드 파일 선택 취소됨.")
            # '취소' 시 'No Sound' 상태로 되돌림
            # 이전에 선택된 사운드가 있었는지 여부와 관계없이 No Sound로 설정
            self.clear_selected_sound() # clear_selected_sound 호출

    def clear_selected_sound(self):
        """선택된 사운드 파일 경로를 초기화하고 버튼 상태를 업데이트합니다."""
        logging.debug("선택된 사운드 초기화 요청.")
        self.selected_sound_path = None
        self.form_sound_button.setText("Sound 🔊") # 버튼 텍스트 원래대로 복구
        # self.form_sound_button.setChecked(False) # 그룹 관리로 불필요
        self.clear_sound_button.setChecked(True) # No Sound 버튼을 선택 상태로 변경

    def open_feedback_link(self):
        """피드백 링크(GitHub Discussions)를 기본 웹 브라우저에서 엽니다."""
        feedback_url = QUrl("https://github.com/htpaak/AlarmReminderPAAK/discussions")
        if not QDesktopServices.openUrl(feedback_url):
            logging.error(f"피드백 링크 열기 실패: {feedback_url.toString()}")
            # 사용자에게 링크 열기 실패 메시지 표시 (선택 사항)
            QMessageBox.warning(self, "Link Error", f"Could not open the feedback page:\n{feedback_url.toString()}\nPlease open it manually in your browser.")

# 테스트용 코드 (ui.py 직접 실행 시)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 테스트용 알람 데이터
    test_alarms = [
        Alarm(title="Morning Exercise", time_str="07:30", selected_days={0, 1, 2, 3, 4}), # 월~금
        Alarm(title="Weekend Jogging", time_str="09:00", selected_days={5, 6}), # 토, 일
        Alarm(title="Meeting", time_str="14:00", selected_days={2}, enabled=False) # 수요일, 비활성
    ]
    tray_icon = QSystemTrayIcon()
    ex = AlarmApp(test_alarms, tray_icon)
    
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