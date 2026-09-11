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

# 2. 기사 페이지에서 실제 1~2줄 요약문(og:description) 추출 및 구글뉴스 문구 필터링
def fetch_article_summary(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            patterns = [
                r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']'
            ]
            for p in patterns:
                m = re.search(p, content, re.I)
                if m:
                    desc = html.unescape(m.group(1)).strip()
                    bad_words = ["Google News", "Comprehensive up-to-date", "aggregated from sources", "Google"]
                    if not any(b in desc for b in bad_words) and len(desc) > 15:
                        return desc
    except Exception:
        pass
    return ""

# 3. 실시간 구글 뉴스 RSS 크롤링 (최근 2일 이내 K-뷰티 핵심 뉴스)
def fetch_kbeauty_news():
    query = "K뷰티 OR 화장품 OR 올리브영 OR 무신사뷰티 OR 에이피알 when:2d"
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
                    
                # 중복 기사 제거
                if any(a["title"] == title for a in articles):
                    continue
                    
                # 실제 기사 본문 요약문 가져오기
                meta_desc = fetch_article_summary(link)
                
                articles.append({
                    "title": title,
                    "source": source_name or "언론사",
                    "link": link,
                    "desc": meta_desc
                })
                if len(articles) >= 5:
                    break
    except Exception as e:
        print(f"RSS 크롤링 오류: {e}")
        
    return articles

# 4. 중복 없는 요약 및 MD 인사이트 생성
def generate_insights(articles):
    # Gemini API가 설정되어 있는 경우 AI 자동 요약
    if GEMINI_API_KEY:
        try:
            prompt = """당신은 11번가 뷰티 카테고리 전문 MD입니다. 아래 K-뷰티 뉴스 5건의 제목을 분석하여 다음 규칙을 지켜 응답해주세요:
1) summary: 기사 핵심 내용 2줄 요약 (문장 앞에 • 포함, 줄바꿈은 <br>. 'Google News' 등 영문 시스템 문구 절대 제외)
2) insight: 11번가 뷰티 MD 관점의 실질적인 상품 소싱/프로모션/기획전 전략 2줄 (문장 앞에 • 포함, 줄바꿈은 <br>. 5개 기사 모두 내용이 겹치지 않게 작성)

반드시 아래 JSON 형식으로만 응답해주세요:
[
  {
    "index": 0,
    "summary": "• 요약문장1.<br>• 요약문장2.",
    "insight": "• 인사이트문장1.<br>• 인사이트문장2."
  }
]
뉴스 목록:
"""
            for i, a in enumerate(articles):
                prompt += f"\n[{i}] 제목: {a['title']} (출처: {a['source']})\n"
                
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
                return articles
        except Exception as e:
            print(f"AI 호출 오류: {e}, 규칙 기반 엔진으로 전환합니다.")

    # 규칙 기반 엔진: 인사이트 룰 목록
    RULES = [
        (
            ["홍대", "플래그십"],
            "• 오프라인 플래그십·팝업 체험 후 앱 결제로 이어지는 '역쇼루밍' 락인 효과 가속화.<br>• 11번가 뷰티플러스 내 성수·홍대 핫플 입점 인디 브랜드 단독관 구성 및 1020 전용 쿠폰팩 연계 추천."
        ),
        (
            ["성수", "다이소", "영토"],
            "• H&B 시장이 올리브영 독점에서 '무신사(트렌드) vs 다이소(초저가)' 양극 체제로 재편 중.<br>• 11번가 뷰티 카테고리도 1만 원 이하 초가성비 라인업과 프리미엄 큐레이션 이원화 전략 필요."
        ),
        (
            ["코스맥스", "제조", "플랫폼"],
            "• 신규 인디 브랜드의 론칭 리드타임이 단축되며 SNS 바이럴 트렌드 성분의 시장 진입 주기 초단기화.<br>• 코스맥스 제조 기반의 고효능 신생 브랜드를 발굴해 11번가 뷰티플러스 단독 선출시 구좌 유치 권장."
        ),
        (
            ["소비", "글로벌", "수출"],
            "• 서구권과 동남아 시장에서 브랜드 네임보다 PDRN, 비타민 등 '고함량 단일 성분' 신뢰도가 구매 결정.<br>• '글로벌 베스트셀러 고함량 성분 뷰티' 테마전을 기획하여 역직구관 및 특가 메인 배너로 집중 노출 필요."
        ),
        (
            ["ETF", "주가", "실적"],
            "• 화장품 대형주 및 핵심 ODM 기업들의 3분기 실적 모멘텀이 역대 최고치로 투자 심리 견인.<br>• 11절 및 연말 대형 프로모션 시즌에 맞춰 실적 우수 메이저 뷰티 브랜드와 대규모 단독 제휴 협의 적기."
        ),
        (
            ["헬로키티", "콜라보", "에디션", "디바이스", "테크"],
            "• 인기 캐릭터 협업 및 뷰티 디바이스 라인업 확장을 통한 MZ세대 소장 욕구 자극.<br>• 한정판 캐릭터 에디션 단독 물량 선확보 및 선물하기 테마 기획전 우선 편성 유효."
        ),
        (
            ["환절기", "더마", "스킨케어", "바쿠치올", "설화수"],
            "• 계절 전환기에 맞춘 피부 장벽 리페어 및 저자극 슬로우에이징 성분 수요 급증.<br>• 환절기 얼리버드 기획전 및 1+1 보습 리페어 번들 구성을 통한 장바구니 전환 극대화 필요."
        )
    ]
    
    used_insights = set()
    
    for idx, a in enumerate(articles):
        title = a["title"]
        desc = a["desc"]
        
        # 구글뉴스 기본 안내문구 필터링
        bad_phrases = ["Google News", "Comprehensive up-to-date", "aggregated from sources", "Google"]
        if any(b in desc for b in bad_phrases):
            desc = ""
            
        clean_title = re.sub(r'\[.*?\]', '', title)
        clean_title = re.sub(r'By\s+[A-Za-z0-9가-힣]+', '', clean_title).strip()
        
        # 1) 깔끔한 2줄 요약문 생성 (영문 문구 배제)
        if desc and len(desc) > 20:
            clean_s = [s.strip() for s in re.split(r'[.!?]', desc) if len(s.strip()) > 10 and not any(b in s for b in bad_phrases)]
            if len(clean_s) >= 2:
                a["summary"] = f"• {clean_s[0]}.<br>• {clean_s}."
            elif len(clean_s) == 1:
                a["summary"] = f"• {clean_title}.<br>• {clean_s[0]}."
            else:
                a["summary"] = f"• {clean_title}.<br>• 주요 유통 플랫폼별 판매 동향 및 소비자 반응 관측 필요."
        else:
            t_lower = (title + " " + a["source"]).lower()
            if "헬로키티" in t_lower or "에디션" in t_lower:
                a["summary"] = f"• {clean_title}.<br>• 글로벌 인기 캐릭터 협업 에디션 출시로 MZ세대 타깃 뷰티테크 신규 진입 촉진."
            elif "무신사" in t_lower and "올리브영" in t_lower:
                a["summary"] = f"• {clean_title}.<br>• 온·오프라인 뷰티 플랫폼 간 1020 영타깃 유입 및 핵심 상권 영토 확장 경쟁 본격화."
            elif "코스맥스" in t_lower:
                a["summary"] = f"• {clean_title}.<br>• 글로벌 인허가 및 수출 지원 인프라 확대로 파트너 인디 브랜드 동반 성장 견인."
            elif "다이소" in t_lower:
                a["summary"] = f"• {clean_title}.<br>• 성수 중심의 프리미엄 팝업과 다이소의 초가성비 균일가 매대로 양분되는 유통 트렌드."
            else:
                a["summary"] = f"• {clean_title}.<br>• 업계 최신 실적 모멘텀 및 온·오프라인 유통 채널 동향 주목."
            
        # 2) 인사이트 중복 방지 매칭
        assigned = False
        text = title + " " + desc
        
        for keywords, insight_text in RULES:
            if insight_text in used_insights:
                continue
            if any(k in text for k in keywords):
                a["insight"] = insight_text
                used_insights.add(insight_text)
                assigned = True
                break
                
        if not assigned:
            for _, insight_text in RULES:
                if insight_text not in used_insights:
                    a["insight"] = insight_text
                    used_insights.add(insight_text)
                    assigned = True
                    break
                    
        if not assigned:
            a["insight"] = (
                "• 시장 트렌드 변화에 따른 카테고리 선제적 큐레이션 및 시즌성 프로모션 선편성 필요.<br>"
                "• 라이징 유망 브랜드 대상 11번가 단독 특가 구좌 연계로 초기 유입 모멘텀 확보 권장."
            )

    return articles

# 5. 크롤링 및 분석 실행
articles = fetch_kbeauty_news()
if not articles:
    raise Exception("실시간 뉴스를 크롤링하지 못했습니다.")
articles = generate_insights(articles)

# 6. HTML 카드 생성 (완전한 화이트 배경 및 11번가 서체)
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

# 전체 HTML 조립
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

# 7. 메일 메시지 구성 및 Gmail 임시보관함 주입
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
        print(f"성공: [{folder}] 폴더에 구글 문구 없는 리포트 초안이 정상 생성되었습니다.")
        success = True
        break

if not success:
    raise Exception("임시보관함 폴더를 찾지 못해 초안 생성에 실패했습니다.")

imap.logout()
