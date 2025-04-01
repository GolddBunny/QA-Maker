import networkx as nx
import json
import sys

def convert_graphml_to_json(graphml_path, json_path):
    try:
        # .graphml 파일을 읽어들입니다.
        print(f"📌 GraphML 파일 로드 중: {graphml_path}")
        graph = nx.read_graphml(graphml_path)
        print(f"✅ 로드 완료! 노드 수: {graph.number_of_nodes()}, 엣지 수: {graph.number_of_edges()}")

        # 그래프의 노드와 엣지 정보를 딕셔너리로 변환합니다.
        graph_data = {
            "nodes": [],
            "edges": []
        }

        # 노드 정보 추가
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

        # 엣지 정보 추가
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
            graph_data["edges"].append(edge_data)

        # JSON 파일로 저장
        with open(json_path, "w") as f:
            json.dump(graph_data, f, indent=4)

        print(f"GraphML 파일이 JSON 형식으로 변환되었습니다. 저장 위치: {json_path}")
    
    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")
        raise  # 예외를 다시 던져서 확인할 수 있도록 함

# 실행 시 인자로 파일 경로를 받을 수 있도록 설정
# if __name__ == "__main__":
#     if len(sys.argv) != 3:
#         print("사용법: python graphml2json.py <graphml_path> <json_path>")
#         sys.exit(1)

#     graphml_path = sys.argv[1]  # 첫 번째 인자로 GraphML 파일 경로 받기
#     json_path = sys.argv[2]  # 두 번째 인자로 JSON 파일 경로 받기

#     print(f"GraphML 파일: {graphml_path}, JSON 파일: {json_path}")
#     convert_graphml_to_json(graphml_path, json_path)