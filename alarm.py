import uuid
from dataclasses import dataclass, field
from enum import Enum

class RepeatSetting(Enum):
    NONE = "None"
    DAILY = "Daily"
    WEEKLY = "Weekly"

@dataclass
class Alarm:
    title: str
    time_str: str # HH:MM 형식
    repeat: RepeatSetting = RepeatSetting.NONE
    enabled: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __str__(self):
        # UI 목록 표시에 사용될 문자열 형식
        repeat_str = f"[{self.repeat.value}]" if self.repeat != RepeatSetting.NONE else ""
        status_str = "🔔" if self.enabled else "🔕"
        return f"{status_str} {self.time_str} - {self.title} {repeat_str}" 