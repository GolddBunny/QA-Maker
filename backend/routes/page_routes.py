import os
import shutil
import subprocess
import time
from flask import Blueprint, jsonify, request

page_bp = Blueprint('page', __name__)

# 페이지 관련 디렉토리 확인 및 생성
def ensure_page_directory(page_id):
    """
    페이지별 필요한 폴더 생성
    - input: 문서 입력 파일 저장
    - upload: 프론트엔드에서 접근할 수 있는 경로
    """

    base_path = f'../data/input/{page_id}'
    input_path = os.path.join(base_path, 'input')
    upload_path = f'../frontend/public/data/{page_id}/input'
    
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(input_path, exist_ok=True)
    os.makedirs(upload_path, exist_ok=True)
    
    return base_path, input_path, upload_path

# settings.yaml 파일 복사
def update_settings_yaml(page_id):
    settings_path = f'../data/input/{page_id}/settings.yaml'
    settings_source_path = '../data/parquet/settings.yaml'
    shutil.copy2(settings_source_path, settings_path)

# .env 파일 복사
def create_env_file(page_id):
    env_source_path = '../data/parquet/.env'
    env_dest_path = f'../data/input/{page_id}/.env'
    
    if os.path.exists(env_source_path):
        shutil.copy(env_source_path, env_dest_path)
        print(f"Copied .env file from parquet to page {page_id}")
    else:
        print("Source .env file not found in ../data/parquet/.env")

# 프롬프트 파일 복사
def update_prompts(page_id, prompt_type='doc'):
    # prompt_type: doc / url / change
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

    print(f"타입: {prompt_type}, 소스: {prompt_src}, 대상: {prompt_dest}")
    
    if not os.path.exists(prompt_src):
        print(f"프롬프트 소스 없음: {prompt_src}")
        return

    try:
        # 기존 폴더 삭제 후 새로 복사
        if os.path.exists(prompt_dest):
            shutil.rmtree(prompt_dest)
            print(f"기존 폴더 삭제: {prompt_dest}")

        # 폴더 전체 복사
        shutil.copytree(prompt_src, prompt_dest)
        print(f"프롬프트 복사 완료: {prompt_src} -> {prompt_dest}")
        
        # 복사 결과 검증
        if os.path.exists(prompt_dest):
            file_count = len(os.listdir(prompt_dest))
            print(f"{file_count}개 파일 복사됨")
        else:
            print(f"대상 폴더가 생성되지 않음: {prompt_dest}")
            
    except Exception as e:
        print(f"{prompt_type} 복사 실패: {e}")

# 페이지 초기화 API
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
        
        # 초기화 후 설정 파일 및 프롬프트 복사
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

# 페이지 삭제 API
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

# 안전하게 디렉토리 복사
def safe_copy_tree(src, dest):
    """파일 단위로 존재 여부 확인하며 복사"""
    if os.path.exists(src):
        os.makedirs(dest, exist_ok=True)
        for filename in os.listdir(src):
            src_file = os.path.join(src, filename)
            dest_file = os.path.join(dest, filename)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dest_file)
    else:
        print(f"디렉토리 없음: {src}")

# 문서용 및 URL용 페이지 초기화
@page_bp.route('/init_doc_url/<page_id>', methods=['POST'])
def init_doc_url(page_id):
    try:
        print(f"[InitDocUrl 시작] page_id: {page_id}")
        
        # URL용 디렉토리 생성
        url_page_id = f"{page_id}_url"
        url_base_path = f'../data/input/{url_page_id}'
        url_input_path = os.path.join(url_base_path, 'input')
        
        print(f"[InitDocUrl] URL 디렉토리 생성: {url_base_path}")
        os.makedirs(url_input_path, exist_ok=True)

        # URL용 설정 파일들 복사
        print(f"[InitDocUrl] URL용 설정 파일 복사 시작")
        
        # settings.yaml 복사
        try:
            settings_source = '../data/parquet/settings.yaml'
            settings_dest = os.path.join(url_base_path, 'settings.yaml')
            if os.path.exists(settings_source):
                shutil.copy2(settings_source, settings_dest)
                print(f"[InitDocUrl] settings.yaml 복사 완료: {settings_dest}")
            else:
                print(f"[InitDocUrl 경고] settings.yaml 소스 없음: {settings_source}")
        except Exception as e:
            print(f"[InitDocUrl 오류] settings.yaml 복사 실패: {e}")

        # .env 파일 복사
        try:
            env_source = '../data/parquet/.env'
            env_dest = os.path.join(url_base_path, '.env')
            if os.path.exists(env_source):
                shutil.copy2(env_source, env_dest)
                print(f"[InitDocUrl] .env 복사 완료: {env_dest}")
            else:
                print(f"[InitDocUrl 경고] .env 소스 없음: {env_source}")
        except Exception as e:
            print(f"[InitDocUrl 오류] .env 복사 실패: {e}")

        # URL 프롬프트 복사
        try:
            prompt_source = '../data/parquet/url_prompts'
            prompt_dest = os.path.join(url_base_path, 'prompts')
            if os.path.exists(prompt_source):
                if os.path.exists(prompt_dest):
                    shutil.rmtree(prompt_dest)
                shutil.copytree(prompt_source, prompt_dest)
                print(f"[InitDocUrl] URL 프롬프트 복사 완료: {prompt_dest}")
            else:
                print(f"[InitDocUrl 경고] URL 프롬프트 소스 없음: {prompt_source}")
        except Exception as e:
            print(f"[InitDocUrl 오류] URL 프롬프트 복사 실패: {e}")

        # 문서용 디렉토리 생성
        doc_base_path = f'../data/input/{page_id}'
        doc_input_path = os.path.join(doc_base_path, 'input')
        
        print(f"[InitDocUrl] 문서 디렉토리 생성: {doc_base_path}")
        os.makedirs(doc_input_path, exist_ok=True)

        # 문서용 설정 파일들 복사
        print(f"[InitDocUrl] 문서용 설정 파일 복사 시작")
        
        # settings.yaml 복사
        try:
            settings_source = '../data/parquet/settings.yaml'
            settings_dest = os.path.join(doc_base_path, 'settings.yaml')
            if os.path.exists(settings_source):
                shutil.copy2(settings_source, settings_dest)
                print(f"[InitDocUrl] 문서 settings.yaml 복사 완료: {settings_dest}")
        except Exception as e:
            print(f"[InitDocUrl 오류] 문서 settings.yaml 복사 실패: {e}")

        # .env 파일 복사
        try:
            env_source = '../data/parquet/.env'
            env_dest = os.path.join(doc_base_path, '.env')
            if os.path.exists(env_source):
                shutil.copy2(env_source, env_dest)
                print(f"[InitDocUrl] 문서 .env 복사 완료: {env_dest}")
        except Exception as e:
            print(f"[InitDocUrl 오류] 문서 .env 복사 실패: {e}")

        # 문서 프롬프트 복사
        try:
            prompt_source = '../data/parquet/prompts'
            prompt_dest = os.path.join(doc_base_path, 'prompts')
            if os.path.exists(prompt_source):
                if os.path.exists(prompt_dest):
                    shutil.rmtree(prompt_dest)
                shutil.copytree(prompt_source, prompt_dest)
                print(f"[InitDocUrl] 문서 프롬프트 복사 완료: {prompt_dest}")
            else:
                print(f"[InitDocUrl 경고] 문서 프롬프트 소스 없음: {prompt_source}")
        except Exception as e:
            print(f"[InitDocUrl 오류] 문서 프롬프트 복사 실패: {e}")

        print(f"[InitDocUrl 완료] URL: {url_page_id}, 문서: {page_id}")
        
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