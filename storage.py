import json
import os
import logging
from typing import List, Dict, Any
from alarm import Alarm
import uuid

# 저장될 앱 이름 및 파일 이름 정의
APP_NAME = "AlarmReminderPAAK"
FILE_NAME = "alarms.json"

# 데이터 저장 경로 설정
APP_DATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), APP_NAME)
ALARMS_FILE = os.path.join(APP_DATA_DIR, FILE_NAME)

def get_storage_path() -> str:
    """로컬 AppData 디렉토리에 있는 저장 파일의 전체 경로를 반환합니다."""
    # %LOCALAPPDATA% 환경 변수 사용
    local_appdata = os.environ.get('LOCALAPPDATA')
    if not local_appdata:
        # 환경 변수가 없는 경우 (매우 드문 경우), 현재 디렉토리 사용
        print("경고: LOCALAPPDATA 환경 변수를 찾을 수 없습니다. 현재 디렉토리에 저장합니다.")
        return FILE_NAME 
        
    # 앱 데이터 폴더 경로 생성
    app_data_dir = os.path.join(local_appdata, APP_NAME)
    
    # 파일 경로 반환
    return os.path.join(app_data_dir, FILE_NAME)

# STORAGE_FILE 변수를 함수 호출 결과로 대체
# STORAGE_FILE = "alarms.json"

def _ensure_dir_exists():
    """데이터 저장 디렉토리가 없으면 생성합니다."""
    if not os.path.exists(APP_DATA_DIR):
        try:
            os.makedirs(APP_DATA_DIR)
            logging.info(f"데이터 디렉토리 생성됨: {APP_DATA_DIR}")
        except OSError as e:
            logging.error(f"데이터 디렉토리 생성 실패: {e}")
            # 여기서 오류를 다시 발생시키거나, 기본 경로를 사용하도록 처리할 수 있음
            raise # 일단 오류 발생시켜서 문제 인지하도록 함

def load_alarms() -> List[Alarm]:
    """저장된 알람 목록을 파일에서 불러옵니다."""
    logging.info(f"알람 로딩 시도 경로: {ALARMS_FILE}") # 로그 메시지 명확화
    if not os.path.exists(ALARMS_FILE):
        logging.warning(f"알람 파일({ALARMS_FILE})을 찾을 수 없습니다. 빈 목록을 반환합니다.")
        return []
    try:
        # 파일 내용 읽기 및 로깅
        with open(ALARMS_FILE, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            logging.debug(f"읽어온 파일 내용 (raw): {raw_content}") # raw 내용 로그 추가
            # 파일이 비어있는 경우 처리
            if not raw_content.strip():
                logging.warning(f"알람 파일({ALARMS_FILE})이 비어 있습니다. 빈 목록을 반환합니다.")
                return []
            alarms_data = json.loads(raw_content) # raw_content 사용
            logging.debug(f"JSON 파싱 완료 데이터: {alarms_data}") # 파싱된 데이터 로그 추가
            
        alarms = []
        logging.debug("Alarm 객체 변환 시작...") # 변환 시작 로그
        for i, data in enumerate(alarms_data):
            logging.debug(f"  변환 시도 데이터 [{i}]: {data}") # 각 데이터 항목 로그
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
                
            # 이전 버전과의 호환성을 위해 get 사용 및 기본값 None 처리
            alarm = Alarm(
                id=data.get('id', ''), # 이전 버전에 id가 없을 수 있음
                title=data.get('title', 'Untitled Alarm'),
                time_str=data.get('time_str', '00:00'),
                selected_days=data['selected_days'],
                enabled=data.get('enabled', True),
                sound_path=data.get('sound_path', None) # sound_path 로드 추가
            )
            logging.debug(f"  -> 변환된 Alarm 객체 [{i}]: {alarm}") # 변환된 객체 로그
            # id가 없는 경우 새로 생성 (이전 버전 데이터 처리)
            if not alarm.id:
                 alarm.id = str(uuid.uuid4()) # uuid 임포트 필요 -> alarm.py에서 처리
                 logging.warning(f"알람 데이터에 ID가 없어 새로 생성: {alarm.title} -> {alarm.id}")
            alarms.append(alarm)
        logging.info(f"최종 변환된 알람 개수: {len(alarms)}") # 최종 개수 로그 명확화
        return alarms
    except json.JSONDecodeError as e:
        logging.error(f"알람 파일({ALARMS_FILE}) JSON 파싱 오류: {e}. 빈 목록을 반환합니다.")
        return []
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"알람 데이터 처리 중 오류 ({ALARMS_FILE}): {e}. 빈 목록을 반환합니다.", exc_info=True) # 상세 오류 로깅 추가
        return []
    except Exception as e:
        logging.error(f"알람 로딩 중 예기치 않은 오류 발생 ({ALARMS_FILE}): {e}. 빈 목록을 반환합니다.", exc_info=True)
        return []

def save_alarms(alarms: List[Alarm]):
    """알람 목록을 파일에 저장합니다."""
    _ensure_dir_exists() # 저장 전에 디렉토리 확인/생성
    logging.info(f"알람 저장 경로: {ALARMS_FILE}")
    try:
        # Alarm 객체 리스트를 JSON 직렬화 가능한 리스트로 변환
        alarms_data = [
            {
                'id': alarm.id,
                'title': alarm.title,
                'time_str': alarm.time_str,
                'selected_days': list(alarm.selected_days), # set을 list로 변환
                'enabled': alarm.enabled,
                'sound_path': alarm.sound_path # sound_path 저장 추가
            }
            for alarm in alarms
        ]
        with open(ALARMS_FILE, 'w', encoding='utf-8') as f:
            json.dump(alarms_data, f, indent=4, ensure_ascii=False)
        logging.info(f"{len(alarms)}개의 알람 저장 완료.")
    except IOError as e:
        logging.error(f"알람 저장 실패: {e}")
    except Exception as e:
        logging.error(f"알람 데이터 직렬화 또는 저장 중 예외 발생: {e}", exc_info=True)

# 예제 사용
if __name__ == "__main__":
    # 알람 목록 로드
    alarms = load_alarms()
    print(f"로드된 알람 목록: {alarms}")

    # 알람 목록 저장
    save_alarms(alarms)
    print("알람 목록이 성공적으로 저장되었습니다.") 