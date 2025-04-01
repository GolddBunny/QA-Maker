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
    upload_path = f'../frontend/public/page/{page_id}/input'
    
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

        #graphrag init --root ./src/page/{page_id} 명령어 실행
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
            'succes': False,
            'error': str(e)
        }), 500


@page_bp.route('/delete-page/<page_id>', methods=['DELETE', 'POST'])
def delete_page(page_id):
    try:
        base_path = f'../data/input/{page_id}'
        public_path = f'../frontend/public/page/{page_id}'
        
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