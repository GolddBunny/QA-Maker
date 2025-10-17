"""
실행 시간 관리 API 라우트
파이프라인 시작/완료 및 실행 시간 조회 기능
"""

from flask import Blueprint, jsonify, request
from services.execution_time_service import get_tracker, cleanup_tracker
import logging

logger = logging.getLogger(__name__)

execution_time_bp = Blueprint('execution_time', __name__)

@execution_time_bp.route('/start-pipeline/<page_id>', methods=['POST'])
def start_pipeline(page_id):
    """파이프라인 시작 시간 기록"""
    try:
        tracker = get_tracker(page_id)
        tracker.start_pipeline()
        
        return jsonify({
            'success': True,
            'message': f'파이프라인 시작 기록됨: {page_id}',
            'page_id': page_id
        }), 200
        
    except Exception as e:
        logger.error(f"파이프라인 시작 기록 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@execution_time_bp.route('/finish-pipeline/<page_id>', methods=['POST'])
def finish_pipeline(page_id):
    """파이프라인 완료 시간 기록"""
    try:
        tracker = get_tracker(page_id)
        tracker.finish_pipeline()
        
        summary = tracker.get_summary()
        
        return jsonify({
            'success': True,
            'message': f'파이프라인 완료 기록됨: {page_id}',
            'page_id': page_id,
            'summary': summary
        }), 200
        
    except Exception as e:
        logger.error(f"파이프라인 완료 기록 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@execution_time_bp.route('/get-times/<page_id>', methods=['GET'])
def get_execution_times(page_id):
    """페이지별 실행 시간 조회"""
    try:
        tracker = get_tracker(page_id)
        all_times = tracker.get_all_times()
        summary = tracker.get_summary()
        
        return jsonify({
            'success': True,
            'page_id': page_id,
            'execution_times': all_times,
            'summary': summary
        }), 200
        
    except Exception as e:
        logger.error(f"실행 시간 조회 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@execution_time_bp.route('/cleanup/<page_id>', methods=['DELETE'])
def cleanup_execution_tracker(page_id):
    """실행 시간 트래커 인스턴스 정리"""
    try:
        cleanup_tracker(page_id)
        
        return jsonify({
            'success': True,
            'message': f'트래커 정리됨: {page_id}',
            'page_id': page_id
        }), 200
        
    except Exception as e:
        logger.error(f"트래커 정리 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@execution_time_bp.route('/record-step/<page_id>', methods=['POST'])
def record_step_manually(page_id):
    """수동으로 단계별 실행 시간 기록 (디버깅/테스트용)"""
    try:
        data = request.get_json()
        step_name = data.get('step_name')
        execution_time = data.get('execution_time')
        additional_data = data.get('additional_data', {})
        
        if not step_name or execution_time is None:
            return jsonify({
                'success': False,
                'error': 'step_name과 execution_time이 필요합니다'
            }), 400
        
        tracker = get_tracker(page_id)
        tracker.record_step(step_name, execution_time, additional_data)
        
        return jsonify({
            'success': True,
            'message': f'단계 기록됨: {step_name}',
            'page_id': page_id,
            'step_name': step_name,
            'execution_time': execution_time
        }), 200
        
    except Exception as e:
        logger.error(f"수동 단계 기록 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 