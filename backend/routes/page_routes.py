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

def update_prompts(page_id):
    prompts_source_dir = '../data/parquet/prompts'
    prompts_dest_dir = f'../data/input/{page_id}/prompts'
    
    if os.path.exists(prompts_source_dir):
        if not os.path.exists(prompts_dest_dir):
            os.makedirs(prompts_dest_dir)
        
        for file_name in os.listdir(prompts_source_dir):
            source_file = os.path.join(prompts_source_dir, file_name)
            dest_file = os.path.join(prompts_dest_dir, file_name)
            
            if os.path.isfile(source_file):
                shutil.copy(source_file, dest_file)
        
        print(f"Updated prompts for page {page_id} by copying from parquet")
    else:
        print(f"Source prompts directory not found in {prompts_source_dir}")

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

# await fetch(`${BASE_URL}/init_doc_url/${pageId}`);
@page_bp.route('/init_doc_url/<page_id>', methods=['GET'])
def init_doc_url(page_id):
    try:
        # 1. URL용 디렉토리 생성
        url_base_path = f'../data/input/{page_id}_url'  
        url_input_path = os.path.join(url_base_path, 'input') # 나중에 indexing 할 때 이 폴더 안에 있는 파일들을 doc_input_path로 옮겨야함
        os.makedirs(url_input_path, exist_ok=True)

        # URL prompts, .env, settings.yaml 복사
        safe_copy_tree('../data/input/parquet/url_prompts', os.path.join(url_base_path, 'prompts'))  # parquet/url_prompts에 url 프롬프트 넣어주기
        shutil.copy2('../data/input/parquet/.env', os.path.join(url_base_path, '.env'))
        shutil.copy2('../data/input/parquet/settings.yaml', os.path.join(url_base_path, 'settings.yaml'))

        # 2. 문서용 디렉토리 생성
        doc_base_path = f'../data/input/{page_id}'
        doc_input_path = os.path.join(doc_base_path, 'input')
        os.makedirs(doc_input_path, exist_ok=True)

        # doc prompts, .env, settings.yaml 복사
        safe_copy_tree('../data/input/parquet/doc_prompts', os.path.join(doc_base_path, 'prompts'))
        # TODO: 같은 방식으로 url_증분 업데이트할 때, url_prompts 폴더 안에 있는 파일들을 옮겨줘야함.
        # TODO: 증분 인덱싱 할 때, input 폴더 안에 url_input 폴더 안에 있는 파일들을 옮겨줘야함.
        shutil.copy2('../data/input/parquet/.env', os.path.join(doc_base_path, '.env'))
        shutil.copy2('../data/input/parquet/settings.yaml', os.path.join(doc_base_path, 'settings.yaml'))

        return jsonify({
            'success': True,
            'message': f'초기화 완료: {page_id}_url 및 {page_id} 디렉토리 설정 완료'
        }), 200

    except Exception as e:
        print(f"[InitDocUrl 오류] page_id={page_id}, 에러: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500