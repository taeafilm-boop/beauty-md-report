name: Daily Beauty MD Report Draft

on:
  schedule:
    - cron: '30 22 * * 0-4'
  workflow_dispatch:

env:
  TZ: Asia/Seoul # 시스템 시간대를 한국 시간으로 강제 설정

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # 파이썬 환경 세팅
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      # 💡 에러 원인 해결: 뷰티풀숩(bs4) 라이브러리 설치
      - name: 라이브러리 설치
        run: pip install beautifulsoup4

      - name: Run Draft Creator
        env:
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          GMAIL_PASS: ${{ secrets.GMAIL_APP_PASSWORD }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }} # AI 요약을 위한 API 키 추가
        run: python3 create_draft.py
