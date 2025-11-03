# QA Maker 기여 가이드
&nbsp;ISSUE 또는 PR 하기 전에 이 가이드를 읽어주세요

---
## Pull Request
&nbsp;&nbsp;1) 저장소를 fork하고 로컬에 clone 해주세요 <br><br>
&nbsp;&nbsp;2) 변경사항을 위한 새 feature 브랜치를 생성해주세요: <br>
&nbsp;&nbsp;&nbsp;&nbsp; ```git checkout -b feature/your-branch``` <br><br>
&nbsp;&nbsp;3) 변경사항을 적용하고 명확한 커밋 메시지로 커밋해주세요 <br>
&nbsp;&nbsp;&nbsp;&nbsp;**- PR 제목 형식**<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Conventional Commit](https://www.conventionalcommits.org/) 규칙을 따릅니다.<br>
| **타입** | **의미** | **사용 시점** |
| --- | --- | --- |
| **feat** | 새로운 기능 추가 (feature) | 앱이나 모듈에 새로운 동작, 클래스, API, 옵션 등을 추가할 때  |
| **fix** | 버그 수정  | 기존 코드에서 잘못된 동작, 에러, 예외 등을 수정했을 때  |
| **docs** | 문서 수정  | README, 주석, 문서화, API 문서 등을 고쳤을 때 (코드 로직에 영향 없음)  |
| **style** | 코드 스타일 변경  | 공백, 들여쓰기, 세미콜론, 변수명 통일 등 **로직에 영향 없는 형식 수정** |
| **refactor** | 리팩토링 (동작 변화 없음)  | 코드 구조나 로직을 개선했지만 기능은 그대로일 때  |
| **test** | 테스트 코드 관련  | 테스트 코드 추가, 수정, 제거 등 (프로덕션 코드 영향 없음)  |
| **chore** | 기타 잡무  | 빌드 스크립트, 설정 파일, 의존성 업데이트 등  |

&nbsp;&nbsp;&nbsp;&nbsp;**- PR 설명 작성**<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;주요 변경사항을 설명해주세요<br><br>
&nbsp;&nbsp;4) 브랜치를 자신의 fork에 push 해주세요: <br>
&nbsp;&nbsp;&nbsp;&nbsp;```git push origin feature/your-branch``` <br><br>
&nbsp;&nbsp;5)원본 저장소의 main 브랜치로 PR을 생성합니다 <br><br>

---
## 테스트
- PR 제출 전 테스트 실행하여 기존 기능이 깨지지 않도록 확인해주세요
```
cd backend
pytest
```
---
## ISSUE 규칙
- 제목에는 발생한 문제나 개선이 필요한 부분을 적어주세요.
- 문제 상황을 이해할 수 있도록 스크린샷, 로그, 또는 관련 코드를 함께 첨부해주세요.

---
<br>
<br>
<br>
<br>
<h2>IN ENGLISH </h2>
<br>
<br>
<br>
<br>

# QA Maker Contribution Guide
Please read this guide before opening an issue or submitting a PR.

---
## Pull Request

&nbsp;&nbsp;1) Fork the repository and clone it to your local machine. <br><br>
&nbsp;&nbsp;2) Create a new feature branch for your changes: <br>
&nbsp;&nbsp;&nbsp;&nbsp;```git checkout -b feature/your-branch```<br><br>
&nbsp;&nbsp;3) Make your changes and commit them with clear commit messages. <br>
&nbsp;&nbsp;&nbsp;&nbsp;**- PR Title Format**<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Follow the [Conventional Commit](https://www.conventionalcommits.org/) convention.<br>
&nbsp;&nbsp;&nbsp;&nbsp;**- PR Description**<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Provide a clear explanation of the main changes.<br><br>
&nbsp;&nbsp;4) Push your branch to your fork: <br>
&nbsp;&nbsp;&nbsp;&nbsp;```git push origin feature/your-branch``` <br><br>
&nbsp;&nbsp;5) Open a Pull Request to the main branch of the original repository. <br><br>

---

## Test
- Before submitting a PR, run tests to ensure existing functionality is not broken:
```
cd backend
pytest
```
---
## ISSUE Rules
- In the title, briefly describe the problem or the area that needs improvement.  
- Attach screenshots, logs, or relevant code to help others understand the issue.
