import os
import imaplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_USER = "MD_REPORT"
GMAIL_PASS = os.environ.get("oihd zryl hiec wmsk")
TO_EMAIL = "7467@11stcorp.com"

# 이메일 메시지 규격 구성
msg = MIMEMultipart("alternative")
msg["Subject"] = f"[11번가 뷰티 MD 리포트] 일간 트렌드 및 브리프 ({time.strftime('%Y-%m-%d')})"
msg["From"] = GMAIL_USER
msg["To"] = TO_EMAIL

html_content = """
<table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width:680px; margin:0 auto; font-family:sans-serif; border:1px solid #eee; border-radius:10px; overflow:hidden;">
  <tr>
    <td align="center" style="background-color:#FA2828; padding:24px; color:#ffffff;">
      <h2 style="margin:0;">[11번가 뷰티 MD 인사이트 리포트]</h2>
    </td>
  </tr>
  <tr>
    <td style="padding:20px;">
      <p><b>[01] 환절기 스킨케어·더마 중심 K-뷰티 수요 확대</b></p>
      <p>• 요약: 서구권 스킨케어 호조 및 PDRN/장벽 리페어 앰플 라인 강세.<br>
         • 💡 MD 인사이트: 가을 환절기 더마 기획전 조기 편성 및 1+1 번들 소싱 권장.</p>
    </td>
  </tr>
</table>
"""
msg.attach(MIMEText(html_content, "html"))

# Gmail IMAP 접속 후 [임시보관함]에 초안 주입
imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(GMAIL_USER, GMAIL_PASS)

# 한글 환경: '[Gmail]/임시보관함', 영문 환경: '[Gmail]/Drafts'
try:
    imap.append("[Gmail]/Drafts", "", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
except Exception:
    imap.append("[Gmail]/임시보관함", "", imaplib.Time2Internaldate(time.time()), msg.as_bytes())

imap.logout()
print("Gmail 임시보관함에 초안이 성공적으로 생성되었습니다.")
