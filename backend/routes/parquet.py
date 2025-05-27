from flask import app, jsonify, Blueprint
import pandas as pd
import os
import tempfile
from firebase_config import bucket

parquet_bp = Blueprint('parquet', __name__)

#BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/input"))

def download_parquet_from_firebase(firebase_path):
    """
    Firebase Storage에 있는 parquet 파일을 임시 파일로 다운로드하여 pandas DataFrame으로 반환
    """
    blob = bucket.blob(firebase_path)
    if not blob.exists():
        raise FileNotFoundError(f"Firebase에 {firebase_path} 경로가 존재하지 않음")

    with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_file:
        blob.download_to_filename(temp_file.name)
        df = pd.read_parquet(temp_file.name)
    return df

@parquet_bp.route("/api/entity/<page_id>", methods=["GET"])
def get_entities(page_id):
    try:
        firebase_path = f"pages/{page_id}/results/entities.parquet"
        df = download_parquet_from_firebase(firebase_path)

        filtered = df[["human_readable_id", "title", "description"]].rename(columns={
            "human_readable_id": "id",
            "title": "title",
            "description": "description"
        })

        return jsonify(filtered.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@parquet_bp.route("/api/relationship/<page_id>", methods=["GET"])
def get_relationships(page_id):
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
