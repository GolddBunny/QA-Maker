from flask import Blueprint, jsonify, request
from backend.utils.past.url_manager import URLManager

url_load_bp = Blueprint('url_load', __name__)
url_manager = URLManager()

@url_load_bp.route('/get-urls/<page_id>', methods=['GET'])
def get_saved_urls(page_id):
    try:
        urls = url_manager.load_urls(page_id)
        print(f"페이지 '{page_id}'의 저장된 URL 목록: {urls}")
        return jsonify({"success": True, "urls": urls}), 200
    except Exception as e:
        print(f"URL 조회 중 오류 발생: {str(e)}")
        return jsonify({"success": False, "error": f"URL 조회 중 오류 발생: {str(e)}"}), 500

@url_load_bp.route('/get-all-page-ids', methods=['GET'])
def get_all_page_ids():
    try:
        page_ids = url_manager.get_all_page_ids()
        print(f"저장된 모든 페이지 ID 목록: {page_ids}")
        return jsonify({"success": True, "page_ids": page_ids}), 200
    except Exception as e:
        print(f"페이지 ID 조회 중 오류 발생: {str(e)}")
        return jsonify({"success": False, "error": f"페이지 ID 조회 중 오류 발생: {str(e)}"}), 500