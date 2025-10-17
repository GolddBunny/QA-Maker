from flask import app, jsonify, Blueprint
import pandas as pd
import os
import tempfile
from firebase_config import bucket

parquet_bp = Blueprint('parquet', __name__)

# Firebase에서 parquet 파일 다운로드 후 DataFrame 반환
def download_parquet_from_firebase(firebase_path):
    """
    Firebase Storage에 있는 parquet 파일을 임시 파일로 다운로드하고
    pandas DataFrame으로 읽어 반환
    """
    blob = bucket.blob(firebase_path)
    if not blob.exists():
        raise FileNotFoundError(f"Firebase에 {firebase_path} 경로가 존재하지 않음")

    # 임시 파일에 다운로드 후 읽기
    with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_file:
        blob.download_to_filename(temp_file.name)
        df = pd.read_parquet(temp_file.name)
    return df

# Entity 데이터 반환 API
@parquet_bp.route("/api/entity/<page_id>", methods=["GET"])
def get_entities(page_id):
    """
    페이지 ID를 받아 해당 페이지의 entities.parquet를 가져와
    필요한 컬럼만 필터링 후 JSON 형태로 반환
    """
    try:
        firebase_path = f"pages/{page_id}/results/entities.parquet"
        df = download_parquet_from_firebase(firebase_path)

        # 필요한 컬럼만 선택하고 컬럼명 변경
        filtered = df[["human_readable_id", "title", "description"]].rename(columns={
            "human_readable_id": "id",
            "title": "title",
            "description": "description"
        })

        return jsonify(filtered.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Relationship 데이터 반환 API
@parquet_bp.route("/api/relationship/<page_id>", methods=["GET"])
def get_relationships(page_id):
    """
    페이지 ID를 받아 해당 페이지의 relationships.parquet를 가져와
    필요한 컬럼만 필터링 후 JSON 형태로 반환
    """
    try:
        firebase_path = f"pages/{page_id}/results/relationships.parquet"
        df = download_parquet_from_firebase(firebase_path)

        filtered = df[["human_readable_id", "source", "target", "description"]].rename(columns={
            "human_readable_id": "id",
            "source": "source",
            "target": "target",
            "description": "description"
        })

        return jsonify(filtered.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
