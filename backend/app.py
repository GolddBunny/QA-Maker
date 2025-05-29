from flask import Flask
from flask_cors import CORS
import atexit

from routes.query_routes import query_bp
from routes.document_routes import document_bp
from routes.page_routes import page_bp
from routes.crawling_routes import crawling_bp
from routes.urlLoad_routes import url_load_bp
from routes.documentSource_routes import source_bp
from routes.answerSources_routes import url_source_bp
from routes.parquet import parquet_bp
from routes.questionGeneration_routes import question_bp
from routes.generate_routes import generate_bp
from routes.accuracy_routes import accuracy_bp

def create_app():
    """Flask 애플리케이션 생성 및 설정"""
    app = Flask(__name__)
    CORS(app)  # CORS 설정

    # 블루프린트 등록
    app.register_blueprint(query_bp, url_prefix='/flask')
    app.register_blueprint(document_bp, url_prefix='/flask')
    app.register_blueprint(page_bp, url_prefix='/flask')
    app.register_blueprint(crawling_bp, url_prefix='/flask')
    app.register_blueprint(url_load_bp, url_prefix='/flask')
    app.register_blueprint(source_bp, url_prefix='/flask')
    app.register_blueprint(url_source_bp, url_prefix='/flask')
    app.register_blueprint(parquet_bp, url_prefix='/flask')
    app.register_blueprint(question_bp, url_prefix='/flask')
    app.register_blueprint(generate_bp, url_prefix='/flask')
    app.register_blueprint(accuracy_bp, url_prefix='/flask')
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)