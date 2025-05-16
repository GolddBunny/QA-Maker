from flask import app, jsonify, Blueprint
import pandas as pd
import os

parquet_bp = Blueprint('parquet', __name__)

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/input"))

@parquet_bp.route("/api/entity/<page_id>", methods=["GET"])

def get_entities(page_id):
    try:
        path = os.path.join(BASE_PATH, page_id, "output", "entities.parquet")
        df = pd.read_parquet(path)

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
        path = os.path.join(BASE_PATH, page_id, "output", "relationships.parquet")
        df = pd.read_parquet(path)

        filtered = df[["human_readable_id", "source", "target", "description"]].rename(columns={
            "human_readable_id": "id",
            "source": "source",
            "target": "target",
            "description": "description"
        })

        return jsonify(filtered.to_dict(orient="records"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
