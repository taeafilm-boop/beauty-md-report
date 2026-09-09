import os
import imaplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_USER = "taeafilm@gmail.com"
GMAIL_PASS = (os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_PASS") or "").replace(" ", "")
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

# Gmail 계정의 실제 임시보관함(\Drafts) 폴더명 자동 탐색
draft_folder = None
typ, mailboxes = imap.list()
if typ == 'OK':
    for mb in mailboxes:
        if b'\\Drafts' in mb:
            draft_folder = mb.split(b' "/" ')[-1].strip().decode('latin1').strip('"')
            break

candidate_folders = [draft_folder, "[Gmail]/&x4TC3Lz0rQDVaA-", "[Gmail]/Drafts", "Drafts"]
success = False

for folder in candidate_folders:
    if not folder:
        continue
    status, _ = imap.append(folder, "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    if status == 'OK':
        print(f"성공: [{folder}] 폴더에 초안이 정상 생성되었습니다.")
        success = True
        break

if not success:
    raise Exception("임시보관함 폴더를 찾을 수 없어 초안 생성에 실패했습니다.")

imap.logout()
