import os
import re
import time
import subprocess
from flask import Blueprint, jsonify, request
from services.graph_service.create_graph import generate_and_save_graph

query_bp = Blueprint('query', __name__)


@query_bp.route('/run-query', methods=['POST'])
def run_query():

    # 기존 JSON 파일이 있다면 삭제
    json_path = '../frontend/public/json/answer_graphml_data.json'
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
            print(f"{json_path} 파일이 삭제되었습니다.")
        except Exception as e:
            print(f"파일 삭제 중 오류 발생: {e}")
    
    page_id = request.json.get('page_id', '')
    message = request.json.get('message', '')
    resMethod = request.json.get('resMethod', '')
    resType = request.json.get('resType', '')

    print(f'page_id: {page_id}')
    print(f'message: {message}')
    print(f'resMethod: {resMethod}')
    print(f'resType: {resType}')

    message += " '---Analyst Reports---'와 '---Goal---' 사이에 있는 {report_data}의 내용을 [ReportData: 내용] 형식으로 모두 빠짐없이 출력해주세요." \
    "영어로 답변하지 말고 반드시 한국어로 답변해주세요. 답변하고 그 다음 줄에 다음 형식으로 데이터를 모두 빠짐없이 출력해주세요: \n" \
            "질문과 직접 관련된 id부터 순서대로 출력해 주세요. 관련이 적은 id는 뒤쪽에 배치되도록 출력해주세요.\n" \
            "[Entities: id, id, ...]\n" \
            "[Relationships: id, id, ...]\n" \
            # "그리고 '---Analyst Reports---'와 '---Goal---' 사이에 있는 {report_data}의 내용을 [ReportData: 내용] 형식으로 모두 빠짐없이 출력해주세요."
            
    python_command = [
        'graphrag',
        'query',
        '--root',
        f'../data/input/{page_id}',
        '--response-type',
        resType,
        '--method',
        resMethod,
        '--query',
        message
    ]

    start_time = time.time()
    result = subprocess.run(
        python_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, 'LANG': 'ko_KR.UTF-8'},
        encoding='utf-8'
    )

    end_time = time.time()
    execution_time = end_time - start_time
    print(f'execution_time: {execution_time}')

    if result.returncode != 0:
        print(f'exec error: {result.stderr}')
        return jsonify({'error': result.stderr or 'Error occurred during execution'}), 500

    output = result.stdout
    print(output)

    #서버 답변 테스트
    # output = '''황기태 교수님의 이메일 주소는 calafk@hansung.ac.kr입니다.
    #             [Entities: 822, 420]
    #             [Relationships: 614, 293, 703, 706, 704, 705]
    #             [Communities: ]'''

    entities_match = re.search(r'Entities:\s*(?:\[(.*?)\]|([^\]]+))', output)
    relationships_match = re.search(r'Relationships:\s*(?:\[(.*?)\]|([^\]]+))', output)
    # {report_data} 추출
    # report_data_match = re.search(r'\[ReportData:\s*(.*?)\]', output, re.DOTALL)

    entities_list = []
    relationships_list = []
    report_data = ""

    if entities_match:
        entities_data = entities_match.group(1) if entities_match.group(1) else entities_match.group(2)
        entities_list = list(map(int, [e.strip() for e in entities_data.split(',') if e.strip() not in ('+more', '-')])) if entities_data.strip() else []

    if relationships_match:
        relationships_data = relationships_match.group(1) if relationships_match.group(1) else relationships_match.group(2)
        relationships_list = list(map(int, [r.strip() for r in relationships_data.split(',') if r.strip() not in ('+more', '-')])) if relationships_data.strip() else []

    # {report_data} 값 추출
    # if report_data_match:
    #     report_data = report_data_match.group(1).strip()
    #     print(f"추출된 report_data: {report_data}")

    answer = re.sub(r'.*SUCCESS: (Local|Global) Search Response:\s*', '', output, flags=re.DOTALL)
    answer = re.sub(r'\[\s*(Entities|Relationships|Communities)\s*\]', '', answer, flags=re.DOTALL)
    answer = re.sub(r'\[Entities:.*?\]', '', answer)  # Entities 부분 제거
    answer = re.sub(r'\[Relationships:.*?\]', '', answer)  # Relationships 부분 제거
    answer = re.sub(r'\[Communities:.*?\]', '', answer)  # Communities 부분 제거
    # answer = re.sub(r'\[ReportData:.*?\]', '', answer, flags=re.DOTALL)  # ReportData 부분 제거
    answer = re.sub(r'\[Data:.*?\]\s*|\[데이터:.*?\]\s*|\*.*?\*\s*|#', '', answer)  

    #기존 답변 반환
    #print("answer:", answer)
    #return jsonify({'result': answer})
    
    #서브 그래프 생성 시 필요한 것들 반환
    return jsonify({
        'result': answer,
        'entities': entities_list,
        'relationships': relationships_list,
        # 'report_data': report_data
    })


@query_bp.route('/generate-graph', methods=['POST'])
def generate_graph():
    entities_str = request.json.get('entities', '')
    relationships_str = request.json.get('relationships', '')
    page_id = request.json.get('page_id', '')
    
    try:
        entities_list = list(map(int, entities_str.split(',')))
        relationships_list = list(map(int, relationships_str.split(',')))
        
        # 서브 그래프 생성
        generate_and_save_graph(entities_list, relationships_list, page_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500 