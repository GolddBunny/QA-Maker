# 저장된 URL 조회 엔드포인트
from flask import Blueprint, jsonify
from backend.utils.url_manager import URLManager

url_load_bp = Blueprint('url_load', __name__)
url_manager = URLManager()

@url_load_bp.route('/urlLoad', methods=['GET'])
def get_saved_urls():
    try:
        urls = url_manager.load_urls()
        print(f"저장된 URL 목록: {urls}")
        return jsonify({"status": "success", "urls": urls}), 200
    except Exception as e:
        print(f"URL 조회 중 오류 발생: {str(e)}")
        return jsonify({"status": "error", "message": f"URL 조회 중 오류 발생: {str(e)}"}), 500
