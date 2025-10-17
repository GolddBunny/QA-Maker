"""
실행 시간 추적 및 저장 서비스
각 단계별 실행 시간을 기록하고 JSON 파일로 저장
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ExecutionTimeTracker:
    """실행 시간 추적 및 저장 클래스"""
    
    def __init__(self, page_id: str):
        self.page_id = page_id
        self.execution_times = {}
        self.pipeline_start_time = None
        self.base_dir = Path(f"../data/input/{page_id}")
        self.base_dir.mkdir(exist_ok=True)
        self.file_path = self.base_dir / "execution_times.json"
        
        # 기존 데이터 로드 (있는 경우)
        self.load_existing_data()
    
    def load_existing_data(self):
        """기존 실행 시간 데이터 로드"""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.execution_times = json.load(f)
                logger.info(f"기존 실행 시간 데이터 로드: {self.page_id}")
        except Exception as e:
            logger.warning(f"기존 실행 시간 데이터 로드 실패: {e}")
            self.execution_times = {}
    
    def start_pipeline(self):
        """전체 파이프라인 시작 시간 기록"""
        self.pipeline_start_time = time.time()
        self.execution_times['pipeline_start'] = datetime.now().isoformat()
        logger.info(f"파이프라인 시작: {self.page_id}")
    
    def record_step(self, step_name: str, execution_time: float, additional_data: Optional[Dict] = None):
        """단계별 실행 시간 기록
        
        Args:
            step_name: 단계명 (예: 'url_crawling', 'web_structuring')
            execution_time: 실행 시간 (초)
            additional_data: 추가 데이터 (예: 처리된 URL 개수 등)
        """
        step_data = {
            'execution_time_seconds': execution_time,
            'execution_time_formatted': self._format_time(execution_time),
            'timestamp': datetime.now().isoformat(),
            'step_name': step_name
        }
        
        if additional_data:
            step_data.update(additional_data)
        
        self.execution_times[step_name] = step_data
        
        # 즉시 저장
        self.save_to_file()
        logger.info(f"단계 완료 기록: {step_name} - {execution_time:.2f}초")
    
    def finish_pipeline(self):
        """전체 파이프라인 완료 시간 기록"""
        if self.pipeline_start_time:
            total_time = time.time() - self.pipeline_start_time
            self.execution_times['pipeline_total'] = {
                'execution_time_seconds': total_time,
                'execution_time_formatted': self._format_time(total_time),
                'timestamp': datetime.now().isoformat(),
                'step_name': 'pipeline_total'
            }
            
            # 단계별 시간 합계 계산
            step_times_sum = sum(
                step.get('execution_time_seconds', 0) 
                for key, step in self.execution_times.items() 
                if isinstance(step, dict) and key not in ['pipeline_start', 'pipeline_total', 'summary']
            )
            
            # 요약 정보 추가
            self.execution_times['summary'] = {
                'total_pipeline_time': total_time,
                'total_step_times': step_times_sum,
                'overhead_time': total_time - step_times_sum,
                'steps_completed': len([k for k in self.execution_times.keys() if k not in ['pipeline_start', 'pipeline_total', 'summary']]),
                'completion_timestamp': datetime.now().isoformat()
            }
            
            self.save_to_file()
            logger.info(f"파이프라인 완료: {self.page_id} - 총 {total_time:.2f}초")
    
    def _format_time(self, seconds: float) -> str:
        """시간을 읽기 쉬운 형태로 포맷"""
        if seconds < 60:
            return f"{seconds:.2f}초"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}분 {secs:.1f}초"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}시간 {minutes}분 {secs:.1f}초"
    
    def save_to_file(self):
        """실행 시간 데이터를 JSON 파일로 저장"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.execution_times, f, ensure_ascii=False, indent=2)
            logger.debug(f"실행 시간 데이터 저장: {self.file_path}")
        except Exception as e:
            logger.error(f"실행 시간 데이터 저장 실패: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """실행 시간 요약 정보 반환"""
        return self.execution_times.get('summary', {})
    
    def get_all_times(self) -> Dict[str, Any]:
        """모든 실행 시간 데이터 반환"""
        return self.execution_times.copy()

# 전역 트래커 인스턴스 관리
_trackers: Dict[str, ExecutionTimeTracker] = {}

def get_tracker(page_id: str) -> ExecutionTimeTracker:
    """페이지별 실행 시간 트래커 인스턴스 반환"""
    if page_id not in _trackers:
        _trackers[page_id] = ExecutionTimeTracker(page_id)
    return _trackers[page_id]

def cleanup_tracker(page_id: str):
    """트래커 인스턴스 정리"""
    if page_id in _trackers:
        del _trackers[page_id] 