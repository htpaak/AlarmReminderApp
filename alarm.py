import uuid
from dataclasses import dataclass, field
from typing import Set

# RepeatSetting Enum 제거
# class RepeatSetting(Enum):
#     NONE = "None"
#     DAILY = "Daily"
#     WEEKLY = "Weekly"

# 요일 이름 (월요일 시작)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

@dataclass
class Alarm:
    title: str
    time_str: str # HH:MM 형식
    # repeat 필드 대신 selected_days 필드 추가 (월=0 ~ 일=6)
    selected_days: Set[int] = field(default_factory=set)
    enabled: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_repeat_str(self) -> str:
        """선택된 요일을 문자열로 반환합니다."""
        if not self.selected_days:
            return ""
        if len(self.selected_days) == 7:
            return "[Daily]"
        # 선택된 요일 번호를 요일 이름 약자로 변환하여 정렬
        sorted_days = sorted(list(self.selected_days))
        day_names = [WEEKDAYS[day] for day in sorted_days]
        return f"[{', '.join(day_names)}]"

    def __str__(self):
        # UI 목록 표시에 사용될 문자열 형식
        repeat_str = self.get_repeat_str()
        status_str = "🔔" if self.enabled else "🔕"
        # repeat_str이 비어있지 않으면 공백 추가
        return f"{status_str} {self.time_str} - {self.title}{' ' + repeat_str if repeat_str else ''}" 