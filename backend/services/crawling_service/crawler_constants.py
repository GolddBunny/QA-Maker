"""
크롤링 서비스 상수 정의
웹 크롤링에 필요한 모든 상수들을 중앙 집중식으로 관리
"""

from pathlib import Path

# 기본 디렉토리 설정
BASE_DIR = Path(__file__).parent / "urlCrawling_CSE"

# 유저 에이전트 정의
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
]

# 문서 파일 확장자 패턴
DOC_EXTENSIONS = ['.pdf', '.docx', '.doc', '.hwp', '.txt', '.hwpx', 'word']

# 제외할 url 패턴
EXCLUDE_PATTERNS = [
    '/login', '/logout', '/search?', 'javascript:', '#', 'mailto:', 'tel:',
    '/api/', '/rss/', 'comment', 'print.do', 'popup', 'redirect', 'captcha', 'admin', 
    'synapview.do?', '/synapview.do?', '/synap', '/synap/view.do', '/synap/view.do?', 
    'artclpasswordchckview.do', 'schdulexcel.do', '.php',
    '/hansung/8390', 'book.hansung.ac.kr/review-type/', 'https://book.hansung.ac.kr/', 'https://cms.hansung.ac.kr/em/'
]

# 게시판 목록 페이지 패턴 (URL 목록에서 제외하되 링크는 추출)
LIST_PAGE_PATTERNS = [
    'artcllist.do', 'rsslist.do'
]

# 제외할 파일 확장자
EXCLUDE_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tif', '.tiff', '.ico', '.webp', 
    '.html', '.htm', '.css', '.js', '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', 
    '.mkv', '.tmp', '.zip', '.xls', '.xlsx', '.wma', '.wav', '.rar', '.7z'  # xls, wma 등 추가
]

# 페이지네이션 감지를 위한 CSS 식별자
PAGINATION_SELECTORS = [
    ".pagination", "nav.pagination", "ul.pagination", ".paging", "._paging", "_totPage",
    ".page-navigation", ".paginate", "ul.page-numbers", ".pagenavigation", ".page-nav",
    "[class*='paging']", "[class*='pagination']", "[class*='page_navi']", ".board_paging",
    ".paginator", ".navigator", ".list_page", "#paging", "#pagination", ".page-list",
    ".board-paging", ".pager", ".pages", ".page-selector", ".pagenate"
]

# 페이지 번호 링크 감지를 위한 XPath 패턴: XML 문서의 요소와 속성을 탐색하기 위한 쿼리 언어
PAGE_NUMBER_PATTERNS = [
    "//a[contains(@href, 'page=')]", "//a[contains(@href, 'pageIndex=')]", 
    "//a[contains(@href, 'pageNo=')]", "//a[contains(@class, 'page-link')]",
    "//a[contains(@class, 'page-')]", "//a[contains(text(), '다음')]",
    "//a[contains(@class, 'next')]", "//a[contains(text(), '다음 페이지')]",
    "//a[contains(text(), '다음 페이지')]", "//a[contains(text(), 'Next')]"
]

# 첨부파일 클래스 식별자
ATTACHMENT_CLASSES = [
    'attachment', 'attachments', 'file-download', 'download-file', 
    'document-link', 'file-list', 'view-file', 'board-file',
    'filearea', 'file-area', 'download-area', 'download-box', 'download'
]

# 다운로드 URL 패턴 (우선순위: .do 파일들이 더 명확한 다운로드 신호)
DOWNLOAD_PATTERNS = [
    '/download', '/file', '/attach', 'fileDown', 'getFile', 
    'downloadFile', 'downFile', 'fileview', 'download', 'download.do', 'fileDown.do', 'downloadFile.do'
]

# 명확한 다운로드 패턴 (.do 파일들 - 높은 우선순위)
EXPLICIT_DOWNLOAD_PATTERNS = [
    'download.do', 'filedown.do', 'getfile.do', 'downloadfile.do', 'downfile.do', 'fileview.do'
]

# 다양한 오류 메시지 패턴 확인
ERROR_PATTERNS = [
    'alert 404', 'alert 500', 'alert 403', 'alert 400', 'error', '404', '500', '403', 'alert', 'Alert 500', 'Alert 404', 'Alert 403', 'Alert 400',
    '관리모드 > 알림메세지', '관리모드'
] 