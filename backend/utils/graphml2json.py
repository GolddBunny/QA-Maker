import os
import networkx as nx
import json
import sys

# GraphML 파일을 읽어서 JSON 형식으로 변환 후 저장하는 함수
def convert_graphml_to_json(graphml_path, json_path):
    try:
        # GraphML 파일 로드
        print(f"GraphML 파일 로드 중: {graphml_path}")
        graph = nx.read_graphml(graphml_path)
        print(f"노드 수: {graph.number_of_nodes()}, 엣지 수: {graph.number_of_edges()}")

        # 그래프 데이터를 담을 딕셔너리 초기화
        graph_data = {
            "nodes": [],
            "edges": []
        }

        # 모든 노드 정보를 딕셔너리 형태로 변환
        for node, attributes in graph.nodes(data=True):
            node_data = {
                "id": node,
                "level": attributes.get("level", None),
                "human_readable_id": attributes.get("human_readable_id", None),
                "source_id": attributes.get("source_id", None),
                "description": attributes.get("description", None),
                "weight": attributes.get("weight", None),
                "cluster": attributes.get("cluster", None),
                "entity_type": attributes.get("entity_type", None),
                "degree": attributes.get("degree", None),
                "type": attributes.get("type", None)
            }
            graph_data["nodes"].append(node_data)

        # 모든 엣지 정보를 딕셔너리 형태로 변환
        for source, target, attributes in graph.edges(data=True):
            edge_data = {
                "source": source,
                "target": target,
                "level": attributes.get("level", None),
                "human_readable_id": attributes.get("human_readable_id", None),
                "id": attributes.get("id", None),
                "source_id": attributes.get("source_id", None),
                "description": attributes.get("description", None),
                "weight": attributes.get("weight", None)
            }
            graph_data["edges"].append(edge_data)   # 변환한 엣지 정보 추가

        # 출력 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        # JSON 파일로 저장
        with open(json_path, "w") as f:
            json.dump(graph_data, f, indent=4)

        print(f"GraphML 파일이 JSON 형식으로 변환되었습니다. 저장 위치: {json_path}")
    
    except Exception as e:
        # 변환 중 오류 발생 시 출력 후 예외 다시 던지기
        print(f"오류 발생: {e}")
        raise 
