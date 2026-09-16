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

# 2. 기사 페이지에서 실제 1~2줄 요약문(og:description) 추출 및 구글뉴스 안내문 필터링
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

# 3. 실시간 국내 주요 코스메틱 브랜드 및 상품 중심 크롤링
def fetch_cosmetic_news():
    # 국내 주요 브랜드군 (대기업 메이저 + 톱 인디/색조/더마)
    brands = (
        "설화수 OR 라네즈 OR 에스트라 OR 헤라 OR 아모레퍼시픽 OR "
        "더후 OR CNP OR 피지오겔 OR LG생활건강 OR "
        "메디큐브 OR 달바 OR 클리오 OR 롬앤 OR 토리든 OR "
        "넘버즈인 OR 마녀공장 OR 닥터지 OR 라운드랩 OR 아누아"
    )
    # 상품성 키워드 (신제품, 출시, 완판, 주요 카테고리)
    product_keywords = "신제품 OR 출시 OR 신상 OR 완판 OR 랭킹 OR 쿠션 OR 앰플 OR 세럼 OR 크림 OR 립"
    
    # K-뷰티 거시 담론(수출, 증시 등)을 배제하고 브랜드/상품 중심 결합
    query = f"({brands}) ({product_keywords}) when:2d"
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

# 4. 상품 중심 요약 및 11번가 MD 인사이트 생성
def generate_insights(articles):
    # Gemini API가 설정되어 있는 경우 AI 자동 요약
    if GEMINI_API_KEY:
        try:
            prompt = """당신은 11번가 뷰티 카테고리 전문 MD입니다. 아래 국내 주요 코스메틱 브랜드 및 상품 뉴스 5건을 분석하여 다음 규칙을 엄격히 지켜 응답해주세요:
1) summary: 브랜드 및 상품명, 핵심 스펙/효능 중심의 2줄 요약 (문장 앞에 • 포함, 줄바꿈은 <br>. 'Google News' 등 영문 시스템 문구 절대 제외)
2) insight: 11번가 뷰티 MD 관점의 실질적인 상품 소싱/단독 구성/프로모션/크로스셀링 전략 2줄 (문장 앞에 • 포함, 줄바꿈은 <br>. 브랜드 및 상품에 맞추어 5개 기사 모두 내용이 겹치지 않게 작성)

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

    # 규칙 기반 엔진: 국내 주요 브랜드 및 상품 중심 룰 목록
    RULES = [
        (
            ["설화수", "더후", "헤라", "프리미엄", "럭셔리", "안티에이징"],
            "• 명절/선물 시즌 및 가을 환절기 대비 프리미엄 고기능성 스킨케어 선물세트 수요 집중.<br>• 11번가 단독 보자기 포장 패키지 및 고가 사은품 결합 프로모션을 통한 객단가 극대화 권장."
        ),
        (
            ["에스트라", "CNP", "닥터지", "피지오겔", "더마", "장벽", "보습"],
            "• 환절기 피부 장벽 리페어 및 저자극 더마 크림·앰플의 정기 교체 수요 급증 구간.<br>• 본품+미니 앰플/크림 증정의 11번가 단독 대용량 기획 번들 구성 및 얼리버드 특가 편성 필요."
        ),
        (
            ["메디큐브", "에이지알", "부스터", "디바이스", "테크"],
            "• 홈 뷰티 디바이스와 전용 PDRN/글루타치온 앰플의 크로스셀링이 이커머스 핵심 매출 견인.<br>• 기기 단품보다 앰플을 묶은 '홈에스테틱 스타터 세트' 단독 물량 선확보 및 라이브11 우선 편성 추천."
        ),
        (
            ["클리오", "롬앤", "쿠션", "립", "틴트", "색조"],
            "• F/W 시즌 신상 립/쿠션 등 1020 영타깃 인기 컬러 SKU의 선제적 단독 물량 확보가 핵심.<br>• 신규 셰이드 론칭 기념 11번가 단독 1+1 기획 및 뷰티플러스 전용 쿠폰팩 연계 시 높은 전환 기대."
        ),
        (
            ["달바", "토리든", "넘버즈인", "마녀공장", "라운드랩", "아누아", "세럼", "패드"],
            "• 뷰티 어워즈 및 랭킹 상위권 스테디셀러(수분 세럼, 토너 패드)의 반복 재구매 사이클 형성.<br>• '올리브영 1위 뷰티템' 테마 기획전 및 묶음 배송 단독 할인 구좌 배치를 통한 장바구니 확대 유효."
        ),
        (
            ["콜라보", "에디션", "한정판", "캐릭터"],
            "• 인기 캐릭터 협업 및 리미티드 에디션을 통한 신규 고객 유입 및 소장 욕구 자극.<br>• 오픈 당일 한정 수량 단독 선착순 특가 및 선물하기 탭 집중 노출로 초기 완판 모멘텀 확보 권장."
        ),
        (
            ["신제품", "출시", "신상", "론칭"],
            "• 신규 론칭 상품의 초기 인지도 확산을 위한 11번가 뷰티 메인 배너 및 단독 기획전 선편성.<br>• 구매 고객 대상 정품 용량 체험단 이벤트 연계로 포토 리뷰 및 구매 전환율 가속화 필요."
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
        
        # 1) 상품성 중심 2줄 요약문 생성
        if desc and len(desc) > 20:
            clean_s = [s.strip() for s in re.split(r'[.!?]', desc) if len(s.strip()) > 10 and not any(b in s for b in bad_phrases)]
            if len(clean_s) >= 2:
                a["summary"] = f"• {clean_s[0]}.<br>• {clean_s}."
            elif len(clean_s) == 1:
                a["summary"] = f"• {clean_title}.<br>• {clean_s[0]}."
            else:
                a["summary"] = f"• {clean_title}.<br>• 주요 뷰티 유통 플랫폼별 판매 순위 및 실시간 소비자 반응 관측 필요."
        else:
            t_lower = (title + " " + a["source"]).lower()
            if any(k in t_lower for k in ["에디션", "콜라보", "한정판"]):
                a["summary"] = f"• {clean_title}.<br>• 한정판 기획 에디션 출시로 희소성 및 소장 가치를 앞세운 타깃 공략 본격화."
            elif any(k in t_lower for k in ["쿠션", "파운데이션", "베이스", "메이크업"]):
                a["summary"] = f"• {clean_title}.<br>• 가을 시즌 맞춤형 밀착·보습 베이스 신제품으로 메이크업 교체 수요 공략."
            elif any(k in t_lower for k in ["앰플", "세럼", "크림", "더마", "스킨케어"]):
                a["summary"] = f"• {clean_title}.<br>• 환절기 보습 및 피부 장벽 강화를 겨냥한 고효능 스킨케어 주력 라인업 강화."
            elif any(k in t_lower for k in ["디바이스", "메디큐브", "기기"]):
                a["summary"] = f"• {clean_title}.<br>• 홈케어 뷰티 디바이스와 전용 기능성 앰플 결합을 통한 안티에이징 수요 선점."
            elif any(k in t_lower for k in ["립", "틴트"]):
                a["summary"] = f"• {clean_title}.<br>• 가을 트렌드 컬러를 반영한 립 신제품 라인업 확대로 1020 색조 소비 견인."
            else:
                a["summary"] = f"• {clean_title}.<br>• 국내 주요 코스메틱 브랜드의 주력 신상품 출시 및 온·오프라인 마케팅 본격화."
            
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
                "• 시즌 트렌드 변화에 따른 카테고리 선제적 큐레이션 및 프로모션 선편성 필요.<br>"
                "• 라이징 인기 브랜드 대상 11번가 단독 특가 구좌 연계로 초기 유입 모멘텀 확보 권장."
            )

    return articles

# 5. 크롤링 및 분석 실행
articles = fetch_cosmetic_news()
if not articles:
    raise Exception("국내 브랜드 뉴스를 크롤링하지 못했습니다.")
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
        print(f"성공: [{folder}] 폴더에 국내 브랜드 중심 리포트 초안이 정상 생성되었습니다.")
        success = True
        break

if not success:
    raise Exception("임시보관함 폴더를 찾지 못해 초안 생성에 실패했습니다.")

imap.logout()
