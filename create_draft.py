import os
import imaplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_USER = "taeafilm@gmail.com"
# GitHub Actions의 env: GMAIL_APP_PASSWORD 값을 읽어옵니다.
GMAIL_PASS = (os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_PASS") or "").replace(" ", "")
TO_EMAIL = "7467@11stcorp.com"

# 이메일 메시지 규격 구성
msg = MIMEMultipart("alternative")
msg["Subject"] = f"[11번가 뷰티 MD 리포트] 일간 트렌드 및 브리프 ({time.strftime('%Y-%m-%d')})"
msg["From"] = GMAIL_USER
msg["To"] = TO_EMAIL
# ... (이하 동일)
