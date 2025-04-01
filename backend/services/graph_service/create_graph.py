import pandas as pd
import networkx as nx
import asyncio
import subprocess
import html
import os
import sys
import pathlib

# 상위 디렉토리 경로를 추가하여 utils 모듈을 import할 수 있도록 함
current_dir = pathlib.Path(__file__).parent.absolute()
backend_dir = current_dir.parent.parent
sys.path.append(str(backend_dir))

from utils.graphml2json import convert_graphml_to_json

# 엔티티와 관계 데이터를 기반으로 그래프를 생성하는 함수
def create_graph(entities_list, relationships_list, entities_file, nodes_file, relationships_file):
    G = nx.DiGraph()

    # Parquet 파일에서 데이터 읽기
    entities_df = pd.read_parquet(entities_file)
    nodes_df = pd.read_parquet(nodes_file)
    relationships_df = pd.read_parquet(relationships_file)

    # 추가할 엔티티 ID 세트 생성 (중복 방지)
    all_entity_ids = set(entities_list)
    
    # relationships_list에서 엔티티 추가
    for relationship_id in relationships_list:
        relationship_row = relationships_df[relationships_df["human_readable_id"] == relationship_id]
        if not relationship_row.empty:
            relationship_row = relationship_row.iloc[0]
            source_title = relationship_row["source"]
            target_title = relationship_row["target"]
            
            # source와 target의 엔티티 ID 찾기
            source_entity = entities_df[entities_df["title"] == source_title]
            target_entity = entities_df[entities_df["title"] == target_title]
            
            # source 엔티티가 있으면 ID 추가
            if not source_entity.empty:
                source_entity_human_id = source_entity.iloc[0]["human_readable_id"]
                all_entity_ids.add(source_entity_human_id)
            
            # target 엔티티가 있으면 ID 추가
            if not target_entity.empty:
                target_entity_human_id = target_entity.iloc[0]["human_readable_id"]
                all_entity_ids.add(target_entity_human_id)

    # Entities 데이터로 노드 추가
    for entity_id in all_entity_ids:
        # 엔티티 데이터 찾기 (human_readable_id로 비교)
        entity_row = entities_df[entities_df["human_readable_id"] == entity_id]
        
        if entity_row.empty:
            print(f"Warning: Entity with human_readable_id {entity_id} not found. Skipping.")
            continue

        # 엔티티가 존재하면 노드 추가
        entity_row = entity_row.iloc[0]
        entity_id = entity_row["id"]
        human_readable_id = entity_row["human_readable_id"]
        title = html.escape(entity_row["title"])
        description = entity_row["description"]
        entity_type = entity_row["type"]

        # `nodes.parquet`에서 같은 id의 노드 찾기
        node_match = nodes_df[nodes_df["id"] == entity_row["id"]]
        degree = int(node_match["degree"].values[0]) if not node_match.empty else 0
        level = int(node_match["level"].values[0]) if not node_match.empty else 0
        cluster = str(node_match["community"].values[0]) if not node_match.empty else "N/A"

        # 노드 추가
        G.add_node(title,
            human_readable_id=human_readable_id,
            degree=degree,
            level=level,
            cluster=cluster,
            source_id=entity_id,
            description=description,
            type=entity_type
        )

    # Relationships 데이터로 엣지 추가
    for relationship_id in relationships_list:
        # 관계를 human_readable_id로 비교하여 찾기
        relationship_row = relationships_df[relationships_df["human_readable_id"] == relationship_id]

        if relationship_row.empty:
            print(f"Warning: Relationship with ID {relationship_id} not found. Skipping.")
            continue 

        relationship_row = relationship_row.iloc[0] 
        source = html.escape(relationship_row["source"])
        target = html.escape(relationship_row["target"])
        description = relationship_row["description"]
        weight = relationship_row["weight"]

        # relationship graph - source와 target이 노드로 존재하는지 확인
        if source not in G.nodes or target not in G.nodes:
            # title을 기준으로 nodes_df에서 해당 엔티티 정보 찾기
            if source not in G.nodes:
                source_entity = entities_df[entities_df["title"] == source]
                if not source_entity.empty:
                    source_entity = source_entity.iloc[0]
                    source_id = source_entity["id"]
                    node_match = nodes_df[nodes_df["id"] == source_id]
                    degree = int(node_match["degree"].values[0]) if not node_match.empty else 0
                    level = int(node_match["level"].values[0]) if not node_match.empty else 0
                    cluster = str(node_match["community"].values[0]) if not node_match.empty else "N/A"
                    G.add_node(source,
                        human_readable_id=source_entity["human_readable_id"],
                        degree=degree,
                        level=level,
                        cluster=cluster,
                        source_id=source_id,
                        description=source_entity["description"],
                        type=source_entity["type"]
                    )
            
            if target not in G.nodes:
                target_entity = entities_df[entities_df["title"] == target]
                if not target_entity.empty:
                    target_entity = target_entity.iloc[0]
                    target_id = target_entity["id"]
                    node_match = nodes_df[nodes_df["id"] == target_id]
                    degree = int(node_match["degree"].values[0]) if not node_match.empty else 0
                    level = int(node_match["level"].values[0]) if not node_match.empty else 0
                    cluster = str(node_match["community"].values[0]) if not node_match.empty else "N/A"
                    G.add_node(target,
                        human_readable_id=target_entity["human_readable_id"],
                        degree=degree,
                        level=level,
                        cluster=cluster,
                        source_id=target_id,
                        description=target_entity["description"],
                        type=target_entity["type"]
                    )

        # 그래프에 엣지 추가
        if source in G.nodes and target in G.nodes:  # 양쪽 노드가 모두 존재하는 경우에만 엣지 추가
            G.add_edge(source, target, description=description, weight=weight)

    return G

def snapshot_graphml(input_graph: nx.Graph, name: str):
    """Graph를 GraphML 형식으로 저장"""
    graphml = "\n".join(nx.generate_graphml(input_graph))

    # `.graphml` 확장자가 없으면 추가
    if not name.endswith(".graphml"):
        name += ".graphml"
    
    # 파일 저장
    with open(name, "w", encoding="utf-8") as file:
        file.write(graphml)

# 생성된 그래프를 GraphML로 저장하는 함수
# graphml_path, json_path 어디서 지정 해줘야할까? 
def generate_and_save_graph(entities_list, relationships_list, 
                            graphml_path=None, 
                            json_path=None):
    
    # 기본 경로 설정
    if graphml_path is None:
        graphml_path = os.path.join(backend_dir, "..", "data", "graphs", "answer_graph.graphml")
    
    if json_path is None:
        json_path = os.path.join(backend_dir, "..", "frontend", "public", "json", "answer_graphml_data.json")
    
    # .json 파일이 이미 존재하면 삭제
    if os.path.exists(json_path):
        os.remove(json_path)
        print(f"기존의 .json 파일 {json_path} 삭제됨.")

    # update_output 폴더 확인
    update_output_folder = os.path.join(backend_dir, "..", "data", "parquet", "update_output")
    base_output_folder = os.path.join(backend_dir, "..", "data", "parquet", "output")

    
    if os.path.exists(update_output_folder):
        print("update_output 폴더가 존재함. 업데이트된 데이터를 사용합니다.")
        entities_file = os.path.join(update_output_folder, "create_final_entities.parquet")
        nodes_file = os.path.join(update_output_folder, "create_final_nodes.parquet")
        relationships_file = os.path.join(update_output_folder, "create_final_relationships.parquet")
    else:
        print("update_output 폴더가 없음. 기존 데이터를 사용합니다.")
        entities_file = os.path.join(base_output_folder, "create_final_entities.parquet")
        nodes_file = os.path.join(base_output_folder, "create_final_nodes.parquet")
        relationships_file = os.path.join(base_output_folder, "create_final_relationships.parquet")


    graph = create_graph(entities_list, relationships_list, 
                         entities_file, nodes_file, relationships_file)

    snapshot_graphml(graph, graphml_path)
    
    # graphml2json.py 실행
    convert_graphml_to_json(graphml_path, json_path)

# 테스트
# if __name__ == "__main__":
#     ### 서버돌릴 때 여기 지우기 ###
#     entities_list=[208, 199, 1003, 1005, 796, 193, 1472, 898, 218, 984, 907, 219, 534, 968, 908, 205, 58, 1006, 1007, 726]
#     relationships_list=[1178, 112, 15, 64, 49, 50, 271, 307, 624, 839, 494, 976, 1039, 498, 473, 499, 437, 769, 988, 448, 330]
#     generate_and_save_graph(entities_list, relationships_list)
