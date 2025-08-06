import json
import os
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import networkx as nx

# TODO: 게시물 이름 "한성대학교" 또는 "페이지"로 나오는 오류 해결 필요.

logger = logging.getLogger(__name__)

# 폰트 설정 - macOS 호환 한국어 폰트
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['AppleGothic', 'Nanum Gothic', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


class SimpleTreeVisualizer:
    """웹사이트 트리 시각화 클래스 (그래프 1개 생성)"""
    
    def __init__(self):
        self.max_display_depth = 10  # 표시할 최대 깊이
        self.max_nodes_per_level = 30  # 레벨당 최대 노드 수
        
        # 페이지 타입별 색상 정의
        self.node_colors = {
            'main': '#FF6B6B',      # 빨간색 - 메인 페이지
            'board': '#4ECDC4',     # 청록색 - 게시판
            'document': '#45B7D1',  # 파란색 - 문서; 테스트용
            'general': '#FFA726',   # 주황색 - 일반 페이지
            'placeholder': '#CCCCCC' # 회색 - 생략된 페이지
        }
        
        # 노드 크기 정의
        self.node_sizes = {
            'main': 3000,
            'board': 2000,
            'document': 1500,
            'general': 1200,
            'placeholder': 800
        }
    
    def generate_single_graph(self, root_node, output_dir: str, base_name: str = "website_structure") -> str:
        """단일 그래프 시각화 생성 (PNG 형식)"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # NetworkX 그래프 생성
            G = nx.DiGraph()
            node_data = {}
            
            # 트리를 그래프로 변환
            self._build_graph(root_node, G, node_data, depth=0)
            
            if len(G.nodes()) == 0:
                logger.warning("그래프에 노드가 없습니다.")
                return ""
            
            # 계층적 레이아웃 생성
            pos = self._create_hierarchical_layout(G, node_data)
            
            # 그래프 그리기
            fig, ax = plt.subplots(1, 1, figsize=(16, 12))
            title = f"웹사이트 구조"
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            
            # 노드별 색상과 크기 설정
            node_colors = [self.node_colors.get(node_data[node]['type'], '#CCCCCC') for node in G.nodes()]
            node_sizes = [self.node_sizes.get(node_data[node]['type'], 1000) for node in G.nodes()]
            
            # 엣지 그리기 (화살표)
            nx.draw_networkx_edges(G, pos, edge_color='#666666', arrows=True, 
                                arrowsize=20, arrowstyle='->', width=2, alpha=0.7)
            
            # 노드 그리기
            nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                                node_size=node_sizes, alpha=0.8, 
                                edgecolors='#333333', linewidths=2)
            
            # 노드 라벨 그리기 (페이지 제목 사용)
            labels = {node: node_data[node]['name'] for node in G.nodes()}
            
            nx.draw_networkx_labels(G, pos, labels, 
                                font_size=9,
                                font_weight='bold',
                                font_color='black',
                                bbox=dict(boxstyle="round,pad=0.3", 
                                facecolor='white', 
                                alpha=0.9,
                                edgecolor='gray'))
            
            # 범례 추가
            self._add_legend(ax)
            
            # 축 설정
            ax.set_axis_off()
            plt.tight_layout()
            
            # 파일 저장
            graph_file = os.path.join(output_dir, f"{base_name}_graph.png")
            plt.savefig(graph_file, dpi=300, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"그래프 시각화 생성 완료: {os.path.basename(graph_file)}")
            return graph_file
            
        except Exception as e:
            logger.error(f"그래프 시각화 생성 중 오류 발생: {e}")
            plt.close()
            return ""
    
    def _build_graph(self, node, G: nx.DiGraph, node_data: Dict, visited_urls: Set[str] = None, depth: int = 0):
        """트리 노드를 NetworkX 그래프로 변환"""
        if visited_urls is None:
            visited_urls = set()
        
        # 순환 참조 방지 및 깊이 제한
        if node.url in visited_urls or depth > self.max_display_depth:
            return
        
        visited_urls.add(node.url)
        
        # 노드 ID 생성
        node_id = self._sanitize_id(node.url)
        
        # 페이지 제목 우선 사용, 없으면 URL에서 추출
        if hasattr(node, 'page_title') and node.page_title:
            node_name = self._clean_title(node.page_title)
        else:
            node_name = self._extract_page_name(node.url)
        
        node_type = getattr(node, 'page_type', 'general')
        
        # 그래프에 노드 추가
        G.add_node(node_id)
        node_data[node_id] = {
            'name': node_name,
            'type': node_type,
            'url': node.url,
            'depth': depth,
            'title': getattr(node, 'page_title', '')  # 원본 제목 보관
        }
        
        # 자식 노드 처리 (개수 제한)
        child_count = 0
        children_to_process = node.children[:self.max_nodes_per_level]
        
        for child in children_to_process:
            if child_count >= self.max_nodes_per_level:
                break
                
            child_id = self._sanitize_id(child.url)
            
            # 자식 노드를 그래프에 추가 (재귀)
            self._build_graph(child, G, node_data, visited_urls.copy(), depth + 1)
            
            # 부모-자식 관계를 엣지로 추가
            if child_id in G.nodes():
                G.add_edge(node_id, child_id)
            
            child_count += 1
        
        # 더 많은 자식이 있는 경우 placeholder 노드 추가
        if len(node.children) > self.max_nodes_per_level:
            placeholder_id = f"more_{node_id}"
            placeholder_name = f"... 그 외 {len(node.children) - self.max_nodes_per_level}개"
            
            G.add_node(placeholder_id)
            node_data[placeholder_id] = {
                'name': placeholder_name,
                'type': 'placeholder',
                'url': '#',
                'depth': depth + 1
            }
            G.add_edge(node_id, placeholder_id)
    
    def _create_hierarchical_layout(self, G: nx.DiGraph, node_data: Dict) -> Dict:
        """계층적 레이아웃 생성"""
        try:
            # 깊이별로 노드 그룹화
            depth_groups = {}
            for node_id, data in node_data.items():
                depth = data['depth']
                if depth not in depth_groups:
                    depth_groups[depth] = []
                depth_groups[depth].append(node_id)
            
            pos = {}
            y_spacing = 3.0  # 레벨 간 수직 간격
            
            for depth, nodes in depth_groups.items():
                y = -depth * y_spacing  # 위에서 아래로
                x_spacing = 8.0 / max(1, len(nodes))  # 노드 수에 따라 수평 간격 조정
                
                for i, node_id in enumerate(nodes):
                    x = (i - len(nodes) / 2) * x_spacing
                    pos[node_id] = (x, y)
            
            return pos
            
        except Exception as e:
            logger.error(f"계층적 레이아웃 생성 중 오류: {e}")
            # 기본 spring 레이아웃 사용
            return nx.spring_layout(G, k=3, iterations=50)
    
    def _add_legend(self, ax):
        """범례 추가"""
        legend_elements = []
        for page_type, color in self.node_colors.items():
            if page_type == 'placeholder':
                continue
            
            # 한글 라벨
            type_labels = {
                'main': '메인 페이지',
                'board': '게시판',
                'document': '문서',
                'general': '일반 페이지'
            }
            
            label = type_labels.get(page_type, page_type)
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                            markerfacecolor=color, markersize=12, label=label))
        
        ax.legend(handles=legend_elements, loc='upper right', fontsize=12)
    
    def _sanitize_id(self, url: str) -> str:
        """URL을 유효한 ID로 변환"""
        import re
        # URL에서 특수문자 제거하고 언더스코어로 대체
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', url)
        # 연속된 언더스코어 하나로 통합
        sanitized = re.sub(r'_+', '_', sanitized)
        # 앞뒤 언더스코어 제거
        sanitized = sanitized.strip('_')
        # 최대 50자로 제한
        return sanitized[:50] if sanitized else f"node_{hash(url) % 10000}"
    
    def _clean_title(self, title: str) -> str:
        """페이지 제목을 시각화에 적합하게 정리"""
        if not title or title.strip() == "":
            return "무제"
        
        # 제목 길이 제한 및 정리
        cleaned = title.strip()
        
        # 길이 제한 (노드에 표시하기 적합한 크기)
        if len(cleaned) > 15:
            # 한국어와 영어 단어 단위로 자르기
            words = cleaned.split()
            if len(words) > 2:
                cleaned = ' '.join(words[:2]) + '...'
            else:
                cleaned = cleaned[:15] + '...'
        
        return cleaned if cleaned else "페이지"
    
    def _extract_page_name(self, url: str) -> str:
        """URL에서 페이지 이름 추출"""
        try:
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            
            # 경로에서 파일명 추출
            path = parsed.path.strip('/')
            if path:
                parts = path.split('/')
                
                # 애매한 파일명들 정의 (의미없는 파일명들)
                meaningless_files = ['list', 'view', 'detail', 'index', 'main', 'home', 'page']
                
                # 마지막 부분이 의미있는 이름인지 확인
                last_part = parts[-1]
                if last_part and last_part != 'index.do':
                    # 파일 확장자 제거
                    name = last_part.split('.')[0]
                    # URL 디코딩
                    name = unquote(name)
                    
                    # 의미없는 파일명이면 상위 디렉토리 사용
                    if name.lower() in meaningless_files and len(parts) > 1:
                        return unquote(parts[-2])
                    elif name:
                        return name
                
                # 상위 디렉토리 이름 사용
                if len(parts) > 1:
                    return unquote(parts[-2])
                elif len(parts) == 1:
                    return unquote(parts[0])
            
            # 쿼리 파라미터에서 이름 추출 시도
            if parsed.query:
                from urllib.parse import parse_qs
                params = parse_qs(parsed.query)
                if 'title' in params:
                    return params['title'][0]
                if 'name' in params:
                    return params['name'][0]
            
            # 도메인 사용
            return parsed.netloc or "홈페이지"
            
        except Exception:
            return "페이지" 