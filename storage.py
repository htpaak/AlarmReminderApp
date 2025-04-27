import json
import os
from typing import List, Dict, Any
from alarm import Alarm

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
            # 'repeat' 대신 'selected_days' 처리
            # 저장된 리스트를 set으로 변환
            data['selected_days'] = set(data.get('selected_days', []))
            # 이전 버전 호환성: 'repeat' 필드가 있으면 변환 시도
            if 'repeat' in data:
                if data['repeat'] == 'Daily':
                    data['selected_days'] = set(range(7))
                elif data['repeat'] == 'Weekly':
                    # 이전 'Weekly'는 단순화되었으므로, 특정 요일 지정 불가
                    # 여기서는 일단 비워두거나, 기본값(e.g., 월요일) 설정 가능
                    # data['selected_days'] = {0} # 예: 월요일로 설정
                    pass # 또는 이전 데이터 무시
                del data['repeat'] # 변환 후 이전 필드 제거
                
            alarms.append(Alarm(**data))
        return alarms
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        print(f"알람 로딩 오류: {e}. 빈 목록으로 시작합니다.")
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
            # 'repeat' 대신 'selected_days' 저장 (set을 list로 변환)
            "selected_days": sorted(list(alarm.selected_days)),
            "enabled": alarm.enabled
        }
        alarms_data.append(data)

    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(alarms_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"알람 저장 오류: {e}") 