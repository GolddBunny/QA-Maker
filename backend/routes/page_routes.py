import os
import shutil
import subprocess
import time
from flask import Blueprint, jsonify, request

page_bp = Blueprint('page', __name__)

def ensure_page_directory(page_id):
    """
    Create necessary directories for a new page
    """
    base_path = f'../data/input/{page_id}'
    input_path = os.path.join(base_path, 'input')
    upload_path = f'../frontend/public/data/{page_id}/input'
    
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(input_path, exist_ok=True)
    os.makedirs(upload_path, exist_ok=True)
    
    return base_path, input_path, upload_path

def update_settings_yaml(page_id):
    settings_path = f'../data/input/{page_id}/settings.yaml'
    settings_source_path = '../data/parquet/settings.yaml'
    shutil.copy2(settings_source_path, settings_path)

def create_env_file(page_id):
    env_source_path = '../data/parquet/.env'
    env_dest_path = f'../data/input/{page_id}/.env'
    
    if os.path.exists(env_source_path):
        shutil.copy(env_source_path, env_dest_path)
        print(f"Copied .env file from parquet to page {page_id}")
    else:
        print("Source .env file not found in ../data/parquet/.env")

def update_prompts(page_id, prompt_type='doc'):
    if prompt_type == 'doc':
        prompt_src = '../data/parquet/prompts'
        prompt_dest = f'../data/input/{page_id}/prompts'
    elif prompt_type == 'url':
        prompt_src = '../data/parquet/url_prompts'
        prompt_dest = f'../data/input/{page_id}/prompts'
    elif prompt_type == 'change':
        page_url_id = f'{page_id}_url'
        prompt_src = f'../data/input/{page_url_id}/prompts'
        prompt_dest = f'../data/input/{page_id}/prompts'
    else:
        raise ValueError(f"지원하지 않는 prompt_type: {prompt_type}")

    if not os.path.exists(prompt_src):
        print(f"[경고] 프롬프트 소스 없음: {prompt_src}")
        return

    # 폴더가 이미 존재하면 먼저 삭제
    if os.path.exists(prompt_dest):
        shutil.rmtree(prompt_dest)

    # 폴더 전체 복사
    shutil.copytree(prompt_src, prompt_dest)
    print(f"프롬프트 복사 완료: {prompt_src} -> {prompt_dest}")

@page_bp.route('/init/<page_id>', methods=['POST'])
def init_page(page_id):
    try:
        base_path, input_path, upload_path = ensure_page_directory(page_id)

        #graphrag init --root ./src/data/{page_id} 명령어 실행
        init_command = [
            'graphrag', 'init', '--root', base_path
        ]

        start_time = time.time()
        init_result = subprocess.run(
            init_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        end_time = time.time()
        execution_time = end_time - start_time
        
        if init_result.returncode != 0:
            return jsonify({
                'success': False,
                'error': init_result.stderr,
                'execution_time': execution_time
            }), 500
        
        # 초기화 후 설정 파일 업데이트
        update_settings_yaml(page_id)
        create_env_file(page_id)
        update_prompts(page_id)

        return jsonify({
            'success': True,
            'execution_time': execution_time
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@page_bp.route('/delete-page/<page_id>', methods=['DELETE', 'POST'])
def delete_page(page_id):
    try:
        base_path = f'../data/input/{page_id}'
        public_path = f'../frontend/public/data/{page_id}'
        
        # src/page/<page_id> 폴더 삭제
        if os.path.exists(base_path):
            shutil.rmtree(base_path)
            print(f"Deleted {base_path}")
            
        # public/page/<page_id> 폴더 삭제
        if os.path.exists(public_path):
            shutil.rmtree(public_path)
            print(f"Deleted {public_path}")
            
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting page {page_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 
    
def safe_copy_tree(src, dest):
    """디렉토리 트리 복사 (존재하지 않으면 생성)"""
    if os.path.exists(src):
        os.makedirs(dest, exist_ok=True)
        for filename in os.listdir(src):
            src_file = os.path.join(src, filename)
            dest_file = os.path.join(dest, filename)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dest_file)
    else:
        print(f"[경고] 디렉토리 없음: {src}")

@page_bp.route('/init_doc_url/<page_id>', methods=['POST'])
def init_doc_url(page_id):
    try:
        # 1. URL용 디렉토리 생성
        url_page_id = f"{page_id}_url"
        url_base_path = f'../data/input/{url_page_id}'
        url_input_path = os.path.join(url_base_path, 'input')
        os.makedirs(url_input_path, exist_ok=True)

        # 설정, 프롬프트, 환경변수 생성
        update_settings_yaml(url_page_id)
        create_env_file(url_page_id)
        update_prompts(url_page_id, prompt_type='url')

        # 2. 문서용 디렉토리 생성
        doc_base_path = f'../data/input/{page_id}'
        doc_input_path = os.path.join(doc_base_path, 'input')
        os.makedirs(doc_input_path, exist_ok=True)

        # 설정, 프롬프트, 환경변수 생성
        update_settings_yaml(page_id)
        create_env_file(page_id)
        update_prompts(page_id, prompt_type='doc')

        return jsonify({
            'success': True,
            'message': f'초기화 완료: {url_page_id} 및 {page_id} 디렉토리 설정 완료'
        }), 200

    except Exception as e:
        print(f"[InitDocUrl 오류] page_id={page_id}, 에러: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500