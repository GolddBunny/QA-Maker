# QA Maker 기여 가이드
&nbsp;issue 또는 PR 하기 전에 이 가이드를 읽어주세요

---
## 기여 방법
&nbsp;&nbsp;1) 저장소를 fork하고 로컬에 clone 해주세요 <br>
&nbsp;&nbsp;2) 변경사항을 위한 새 feature 브랜치를 생성해주세요: <br>
&nbsp;&nbsp;&nbsp;&nbsp; ```git checkout -b feature/your-branch``` <br>
&nbsp;&nbsp;3) 변경사항을 적용하고 명확한 커밋 메시지로 커밋해주세요 <br>
&nbsp;&nbsp4) 브랜치를 자신의 fork에 push 해주세요 <br>
;&nbsp;&nbsp;;&nbsp;&nbsp;```git push origin feature/your-branch``` <br>
&nbsp;&nbsp;5)원본 저장소의 main 브랜치로 PR을 생성합니다 <br>

---
## 테스트
- PR 제출 전 테스트 실행하여 기존 기능이 깨지지 않도록 확인해주세요
```
cd backend
pytest
```
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
## How to Contribute

&nbsp;&nbsp;1) Fork the repository and clone it to your local machine. <br>
&nbsp;&nbsp;2) Create a new feature branch for your changes: <br>
&nbsp;&nbsp;&nbsp;&nbsp;```git checkout -b feature/your-branch```<br>
&nbsp;&nbsp;3) Make your changes and commit them with clear commit messages. <br>
&nbsp;&nbsp;4) Push your branch to your fork: <br>
&nbsp;&nbsp;&nbsp;&nbsp;```git push origin feature/your-branch``` <br>
&nbsp;&nbsp;5) Open a Pull Request to the main branch of the original repository. <br>

---

## Testing
- Before submitting a PR, run tests to ensure existing functionality is not broken:
```
cd backend
pytest
```

