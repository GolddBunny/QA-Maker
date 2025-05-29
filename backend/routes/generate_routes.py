import os
import shutil
import subprocess
import time
import sys
from datetime import datetime
from flask import Blueprint, jsonify, request, make_response
from services.document_service.convert2txt import convert2txt
from firebase_config import bucket

generate_bp = Blueprint('generate', __name__)

@generate_bp.route('/apply/<page_id>', methods=['POST'])
def apply_documents(page_id):
    """GraphRAG 인덱싱 처리"""
    print(f"[서버 로그] 요청 메서드: {request.method}, 경로: /apply/{page_id}")

    try:
        base_path, input_path, upload_path = ensure_page_directory(page_id)
        
        # 프롬프트 폴더 복사 (GraphRAG 인덱싱 전에 필요)
        prompt_src = '../data/parquet/prompts'
        prompt_dest = os.path.join(base_path, 'prompts')
        
        if os.path.exists(prompt_src):
            # 기존 prompts 폴더가 있으면 삭제 후 복사
            if os.path.exists(prompt_dest):
                shutil.rmtree(prompt_dest)
            shutil.copytree(prompt_src, prompt_dest)
            print(f"프롬프트 복사 완료: {prompt_src} -> {prompt_dest}")
        else:
            print(f"[경고] 프롬프트 소스 폴더 없음: {prompt_src}")
            return jsonify({
                'success': False,
                'error': f'프롬프트 폴더를 찾을 수 없습니다: {prompt_src}'
            }), 500

        output_path = os.path.join(base_path, 'output')

        #여기서 base_path/input 폴더에 txt 파일이 하나라도 없으면 밑에 명령어 실행하지 않고 그냥 리턴
        txt_files = [f for f in os.listdir(input_path) if f.endswith('.txt')]
        if not txt_files:
            print(f"[{page_id}] input 폴더에 .txt 파일이 없습니다. 문서 인덱싱 건너뜀.")
            return jsonify({
                'success': True,
                'execution_time': 0
            })


        # graphrag index 명령어 실행
        start_time = time.time()
        print(f"GraphRAG 인덱싱 시작: {base_path}")
        
        # 실시간 로그 출력을 위해 Popen 사용
        process = subprocess.Popen(
            ['graphrag', 'index', '--root', base_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 실시간 로그 출력
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                sys.stdout.flush()
        
        process.wait()
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"GraphRAG 인덱싱 실행 시간: {execution_time}초")
        
        # 인덱싱 실패 시 오류 반환
        if process.returncode != 0:
            error_msg = f"GraphRAG 인덱싱 실패 (코드: {process.returncode})"
            print(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500

        # output 폴더 내부 파일 Firebase로 업로드
        uploaded_files = []
        if os.path.exists(output_path):
            for filename in os.listdir(output_path):
                file_path = os.path.join(output_path, filename)

                if os.path.isfile(file_path):
                    # Firebase Storage에 업로드 경로
                    firebase_path = f'pages/{page_id}/results/{filename}'

                    blob = bucket.blob(firebase_path)
                    blob.upload_from_filename(file_path)
                    blob.make_public()

                    print(f"Uploaded {filename} → {firebase_path}")
                    uploaded_files.append(firebase_path)

                    # 업로드 후 파일 삭제
                    os.remove(file_path)
                    print(f"Deleted local file: {file_path}")

        return jsonify({
            'success': True,
            'execution_time': execution_time
        })

    except Exception as e:
        print("Flask 서버 오류:", str(e))
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@generate_bp.route('/update/<page_id>', methods=['POST'])
def update(page_id):
    """증분 인덱싱"""
    try:
        base_path, input_path, upload_path = ensure_page_directory(page_id)
        output_path = os.path.join(base_path, 'output')

        downloaded = download_output_files_from_firebase(page_id, output_path)
        if not downloaded:
            print("⚠ 기존 결과 파일이 Firebase에 존재하지 않습니다.")

        # input 폴더와 prompts 폴더 _url에서 복사해오기
        url_page_id = f"{page_id}_url"
        url_base_path = f'../data/input/{url_page_id}'
        
        # input 폴더 복사
        url_input_path = os.path.join(url_base_path, 'input')
        if os.path.exists(url_input_path):
            # 📌 .txt 파일이 하나라도 없으면 종료
            txt_files = [f for f in os.listdir(url_input_path) if f.lower().endswith('.txt')]
            if not txt_files:
                print(f"[중단] {url_input_path} 폴더에 .txt 파일이 없습니다.")
                return jsonify({
                    'success': True,
                    'execution_time': 0
                })
            
        if os.path.exists(url_input_path):
            # 기존 input 폴더가 있으면 삭제 후 복사
            if os.path.exists(input_path):
                shutil.rmtree(input_path)
            shutil.copytree(url_input_path, input_path)
            print(f"Input 폴더 복사 완료: {url_input_path} -> {input_path}")
        else:
            print(f"[경고] URL input 폴더 없음: {url_input_path}")
        
        # prompts 폴더 복사
        url_prompts_path = os.path.join(url_base_path, 'prompts')
        dest_prompts_path = os.path.join(base_path, 'prompts')
        if os.path.exists(url_prompts_path):
            # 기존 prompts 폴더가 있으면 삭제 후 복사
            if os.path.exists(dest_prompts_path):
                shutil.rmtree(dest_prompts_path)
            shutil.copytree(url_prompts_path, dest_prompts_path)
            print(f"프롬프트 복사 완료: {url_prompts_path} -> {dest_prompts_path}")
        else:
            print(f"[경고] URL prompts 폴더 없음: {url_prompts_path}")
        
        start_time = time.time()
        if not downloaded:
            print("🔄 'graphrag index' 명령어 실행 중...")
            process = subprocess.run(['graphrag', 'index', '--root', base_path])
        else:
            print("🔁 'graphrag update' 명령어 실행 중...")
            process = subprocess.run(['graphrag', 'update', '--root', base_path])
            
        end_time = time.time()
        execution_time = end_time - start_time
        print(f'GraphRAG 업데이트 실행 시간: {execution_time}초')
        
        # 업데이트 실패 시 오류 반환
        if process.returncode != 0:
            error_msg = f"GraphRAG 업데이트 실패 (코드: {process.returncode})"
            print(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500

        # output 폴더 내부 파일 Firebase로 업로드
        uploaded_files = []
        if os.path.exists(output_path):
            for filename in os.listdir(output_path):
                file_path = os.path.join(output_path, filename)

                if os.path.isfile(file_path):
                    # Firebase Storage에 업로드 경로
                    firebase_path = f'pages/{page_id}/results/{filename}'

                    blob = bucket.blob(firebase_path)
                    blob.upload_from_filename(file_path)
                    blob.make_public()

                    print(f"Uploaded {filename} → {firebase_path}")
                    uploaded_files.append(firebase_path)

                    # 업로드 후 파일 삭제
                    os.remove(file_path)
                    print(f"Deleted local file: {file_path}")

        return jsonify({
            'success': True,
            'execution_time': execution_time
        })
    
    except Exception as e:
        print("Flask update 오류: ", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
# 공통 디렉토리 유틸리티 함수
def ensure_page_directory(page_id):
    """페이지 디렉토리 확인"""
    base_path = f'../data/input/{page_id}'
    input_path = os.path.join(base_path, 'input')
    upload_path = f'../frontend/public/data/{page_id}/input'
    
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(input_path, exist_ok=True)
    os.makedirs(upload_path, exist_ok=True)
    
    return base_path, input_path, upload_path 


def download_output_files_from_firebase(page_id, output_path):
    prefix = f'pages/{page_id}/results/'
    blobs = bucket.list_blobs(prefix=prefix)

    os.makedirs(output_path, exist_ok=True)
    
    found = False
    for blob in blobs:
        if blob.name.endswith("/"):  # 디렉토리인 경우 무시
            continue

        filename = os.path.basename(blob.name)
        local_path = os.path.join(output_path, filename)

        blob.download_to_filename(local_path)
        print(f"Downloaded {blob.name} → {local_path}")
        found = True
    
    return found