import os
import re
import html
import time
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import imaplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 계정 및 환경변수 설정
GMAIL_USER = "taeafilm@gmail.com"
GMAIL_PASS = (os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_PASS") or "").replace(" ", "")
TO_EMAIL = "7467@11stcorp.com"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# 1. 날짜 및 한글 요일 계산
weekdays = ["월", "화", "수", "목", "금", "토", "일"]
now = time.localtime()
date_str = f"{now.tm_year}년 {now.tm_mon:02d}월 {now.tm_mday:02d}일 ({weekdays[now.tm_wday]})"

# 2. 실시간 구글 뉴스 RSS 크롤링 (최근 1일 이내 K-뷰티 핵심 뉴스)
def fetch_kbeauty_news():
    query = "K뷰티 OR 화장품 OR 올리브영 OR 무신사뷰티 OR 지그재그뷰티 OR 에이블리뷰티 OR 아모레퍼시픽 when:1d"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    req = urllib.request.Request(
        rss_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    
    articles = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tree = ET.fromstring(resp.read())
            items = tree.findall(".//item")
            for item in items:
                raw_title = (item.find("title").text or "").strip()
                link = (item.find("link").text or "").strip()
                source_elem = item.find("source")
                source_name = source_elem.text.strip() if source_elem is not None and source_elem.text else ""
                
                # "기사 제목 - 언론사" 분리
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    if not source_name:
                        source_name = parts.strip()
                else:
                    title = raw_title
                    
                desc = item.find("description").text or ""
                clean_desc = re.sub(r'<[^>]+>', '', html.unescape(desc)).strip()
                
                # 중복 제목 제거
                if any(a["title"] == title for a in articles):
                    continue
                    
                articles.append({
                    "title": title,
                    "source": source_name or "언론사",
                    "link": link,
                    "desc": clean_desc
                })
                if len(articles) >= 5:
                    break
    except Exception as e:
        print(f"RSS 크롤링 중 오류: {e}")
        
    return articles

# 3. 요약 및 11번가 MD 인사이트 자동 생성 함수
def generate_insights(articles):
    # (선택) Gemini API 키가 있는 경우 AI 기반 생성
    if GEMINI_API_KEY:
        try:
            prompt = """당신은 11번가 뷰티 카테고리 전문 MD입니다. 아래 K-뷰티 뉴스 5건의 제목과 내용을 분석하여 다음 JSON 형식으로만 응답해주세요:
[
  {
    "index": 0,
    "summary": "• 핵심요약 1줄.<br>• 핵심요약 2줄.",
    "insight": "• 11번가 MD 관점 실행 인사이트 1줄.<br>• 11번가 프로모션/소싱 전략 2줄."
  }
]
뉴스 목록:
"""
            for i, a in enumerate(articles):
                prompt += f"\n[{i}] 제목: {a['title']} (출처: {a['source']})\n내용: {a['desc'][:150]}\n"
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                parsed = json.loads(res_data["candidates"][0]["content"]["parts"][0]["text"])
                for p in parsed:
                    idx = p.get("index", 0)
                    if 0 <= idx < len(articles):
                        articles[idx]["summary"] = p.get("summary", "")
                        articles[idx]["insight"] = p.get("insight", "")
                print("Gemini AI 기반 분석 완료.")
                return articles
        except Exception as e:
            print(f"AI API 호출 오류: {e}, 규칙 기반 엔진으로 전환합니다.")

    # 기본 엔진: 키워드 기반 스마트 요약 & MD 인사이트
    for a in articles:
        title = a["title"]
        desc = a["desc"]
        sentences = [s.strip() for s in re.split(r'[.!?]', desc) if len(s.strip()) > 10]
        if len(sentences) >= 2:
            a["summary"] = f"• {sentences[0]}.<br>• {sentences}."
        elif len(sentences) == 1:
            a["summary"] = f"• {title}.<br>• {sentences[0]}."
        else:
            a["summary"] = f"• {title}.<br>• 뷰티 시장 최신 실적 및 유통 채널 동향 주목."

        # 키워드별 맞춤 MD 인사이트 매칭
        if any(k in title for k in ["디바이스", "테크", "기기", "에이피알"]):
            a["insight"] = "• 뷰티 디바이스와 고기능성 앰플의 번들 결합이 객단가 상승의 핵심 동력으로 안착.<br>• 기기 단품보다 전용 스킨케어를 묶은 '홈에스테틱 스타터 세트' 단독 물량 선확보 권장."
        elif any(k in title for k in ["플래그십", "매장", "홍대", "성수", "오프라인", "무신사", "올리브영"]):
            a["insight"] = "• 오프라인 팝업·매장 체험 후 앱 결제로 이어지는 '역쇼루밍' 락인 효과 가속화.<br>• 11번가 뷰티플러스 내 성수·홍대 핫플 인디 브랜드 단독관 구성 및 1020 전용 쿠폰팩 연계 추천."
        elif any(k in title for k in ["수출", "글로벌", "미국", "일본", "동남아", "아마존"]):
            a["insight"] = "• 글로벌 이커머스에서 검증된 톱랭킹 K-뷰티 SKU의 국내외 역직구 수요 지속 확대.<br>• '해외 완판 검증 뷰티' 테마 기획전을 통해 베스트셀러 상품 집중 노출 전략 주효."
        elif any(k in title for k in ["환절기", "더마", "스킨케어", "바쿠치올", "PDRN", "성분"]):
            a["insight"] = "• 계절 전환기에 맞춘 피부 장벽 리페어 및 저자극 슬로우에이징 성분 수요 급증.<br>• 환절기 얼리버드 기획전 및 1+1 보습 리페어 번들 구성을 통한 장바구니 전환 극대화 필요."
        else:
            a["insight"] = "• 시장 트렌드 변화에 따른 카테고리 선제적 큐레이션 및 시즌성 프로모션 선편성 필요.<br>• 라이징 유망 브랜드 대상 11번가 단독 특가 구좌 연계로 초기 유입 모멘텀 확보 권장."

    return articles

# 4. 크롤링 및 분석 실행
articles = fetch_kbeauty_news()
if not articles:
    raise Exception("실시간 뉴스를 크롤링하지 못했습니다.")
articles = generate_insights(articles)

# 5. HTML 카드 생성 (순백색 화이트 배경)
cards_html = ""
for idx, a in enumerate(articles):
    num_str = f"[{idx+1:02d} / {len(articles):02d}]"
    is_last = (idx == len(articles) - 1)
    border_style = "padding-bottom:10px;" if is_last else "padding-bottom:22px; margin-bottom:22px; border-bottom:1px solid #eeeeee;"
    
    cards_html += f"""
        <div style="{border_style}">
          <div style="font-size:13px; color:#FA2828; font-weight:800; margin-bottom:6px; letter-spacing:0.3px;">{num_str} {a['source']}</div>
          <div style="font-size:18px; font-weight:800; color:#111111; margin-bottom:12px; line-height:1.42; letter-spacing:-0.4px;">{a['title']}</div>
          <div style="font-size:13px; color:#444444; line-height:1.65; margin-bottom:14px;">
            {a['summary']}
          </div>
          <div style="background-color:#fff5f5; border-radius:8px; padding:13px 15px; border-left:3px solid #FA2828; font-size:13px; line-height:1.55; color:#222222; margin-bottom:12px;">
            <b style="color:#FA2828;">💡 MD 인사이트:</b><br>
            {a['insight']}
          </div>
          <div style="text-align:right;">
            <a href="{a['link']}" target="_blank" style="color:#666666; font-size:12px; text-decoration:none; font-weight:700;">🔗 기사 원문 보기 &gt;</a>
          </div>
        </div>
    """

# 전체 HTML 조합
html_content = f"""
<div style="background-color:#ffffff; padding:20px 10px; font-family:'11StreetGothic', '11STREET Gothic', '11번가 고딕', 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;">
  <table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width:680px; margin:0 auto; background-color:#ffffff; border:1px solid #eaeaea; border-radius:12px; overflow:hidden;">
    <!-- 상단 11번가 레드 헤더 배너 -->
    <tr>
      <td align="center" style="background-color:#FA2828; padding:28px 20px; color:#ffffff;">
        <div style="font-size:12px; font-weight:bold; letter-spacing:1px; opacity:0.9; margin-bottom:6px;">11ST BEAUTY MD BRIEF · DAILY REPORT</div>
        <h2 style="margin:0; font-size:23px; font-weight:800; line-height:1.3; letter-spacing:-0.5px;">11번가 뷰티 MD 인사이트 리포트</h2>
        <div style="font-size:13px; margin-top:8px; font-weight:600; opacity:0.95;">{date_str}</div>
      </td>
    </tr>

    <!-- 본문 영역 (완전한 화이트 배경) -->
    <tr>
      <td style="padding:24px 20px; background-color:#ffffff;">
        {cards_html}
      </td>
    </tr>

    <!-- 푸터 -->
    <tr>
      <td align="center" style="background-color:#ffffff; padding:18px; font-size:12px; color:#999999; border-top:1px solid #eeeeee;">
        본 리포트는 11번가 뷰티 MD를 위해 매일 오전 최신 시장 동향을 자동 분석하여 작성됩니다.
      </td>
    </tr>
  </table>
</div>
"""

# 6. 메일 메시지 구성 및 Gmail 임시보관함 주입
msg = MIMEMultipart("alternative")
msg["Subject"] = f"[11번가 뷰티 MD 인사이트 리포트] 일간 트렌드 및 브리프 ({now.tm_year}-{now.tm_mon:02d}-{now.tm_mday:02d})"
msg["From"] = GMAIL_USER
msg["To"] = TO_EMAIL
msg.attach(MIMEText(html_content, "html"))

imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(GMAIL_USER, GMAIL_PASS)

# 실제 임시보관함 폴더명 탐색
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
        print(f"성공: [{folder}] 폴더에 실시간 크롤링 리포트 초안이 정상 생성되었습니다.")
        success = True
        break

if not success:
    raise Exception("임시보관함 폴더를 찾지 못해 초안 생성에 실패했습니다.")

imap.logout()
