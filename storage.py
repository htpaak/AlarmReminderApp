import json
import os
from typing import List, Dict, Any
from alarm import Alarm, RepeatSetting

STORAGE_FILE = "alarms.json"

def load_alarms() -> List[Alarm]:
    """저장된 알람 목록을 파일에서 불러옵니다."""
    if not os.path.exists(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
            alarms_data = json.load(f)
        alarms = []
        for data in alarms_data:
            # JSON에서 읽은 데이터를 Alarm 객체로 변환
            # RepeatSetting 열거형 멤버를 이름으로 찾아 매핑
            data['repeat'] = RepeatSetting(data.get('repeat', RepeatSetting.NONE.value))
            alarms.append(Alarm(**data))
        return alarms
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"알람 로딩 오류: {e}. 빈 목록으로 시작합니다.")
        # 파일이 손상되었거나 형식이 맞지 않을 경우 빈 목록 반환
        return []

def save_alarms(alarms: List[Alarm]):
    """알람 목록을 파일에 저장합니다."""
    alarms_data = []
    for alarm in alarms:
        # Alarm 객체를 JSON으로 직렬화 가능한 딕셔너리로 변환
        data = {
            "id": alarm.id,
            "title": alarm.title,
            "time_str": alarm.time_str,
            "repeat": alarm.repeat.value, # 열거형 멤버의 값을 저장
            "enabled": alarm.enabled
        }
        alarms_data.append(data)

    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(alarms_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"알람 저장 오류: {e}") 