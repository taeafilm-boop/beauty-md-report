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

# ══════════════════════════════════════════════════════
# ▶ 1. 계정 및 환경변수 설정
# ══════════════════════════════════════════════════════
GMAIL_USER = "taeafilm@gmail.com"
GMAIL_PASS = (os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_PASS") or "").replace(" ", "")
TO_EMAIL = "7467@11stcorp.com"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# 날짜 및 한글 요일 계산
weekdays = ["월", "화", "수", "목", "금", "토", "일"]
now = time.localtime()
date_str = f"{now.tm_year}년 {now.tm_mon:02d}월 {now.tm_mday:02d}일 ({weekdays[now.tm_wday]})"

# ══════════════════════════════════════════════════════
# ▶ 2. 뉴스 데이터 수집 함수
# ══════════════════════════════════════════════════════
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

def fetch_cosmetic_news():
    # 💡 올리브영 기준 최신/대세 브랜드군으로 전면 개편
    brands = (
        "메디힐 OR 라운드랩 OR 토리든 OR 에스트라 OR 넘버즈인 OR 아누아 OR "
        "바이오던스 OR 닥터지 OR 아이소이 OR 일소 OR 비레디 OR 오브제 OR "
        "클리오 OR 롬앤 OR 웨이크메이크 OR 퓌 OR VT OR 구달 OR 달바 OR 스킨푸드"
    )
    product_keywords = "신제품 OR 출시 OR 신상 OR 완판 OR 랭킹 OR 쿠션 OR 앰플 OR 세럼 OR 크림 OR 립 OR 패드 OR 클렌징 OR 선크림"
    
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
                
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    if not source_name:
                        source_name = parts[1].strip()
                else:
                    title = raw_title
                    
                if any(a["title"] == title for a in articles):
                    continue
                    
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
        print(f"❌ RSS 크롤링 오류: {e}")
        
    return articles

# ══════════════════════════════════════════════════════
# ▶ 3. Gemini AI 기반 요약 및 인사이트 생성
# ══════════════════════════════════════════════════════
def generate_insights(articles):
    if GEMINI_API_KEY:
        print("💡 Gemini AI를 사용하여 기사 요약 및 인사이트를 생성합니다...")
        try:
            # 💡 프롬프트 고도화: MD 관점 추가 및 중복 방지 제약조건 강화
            prompt = """당신은 11번가 뷰티 카테고리 전문 MD입니다. 주로 스킨케어, 클렌징, 남성화장품, 선케어를 담당합니다. 
아래 주요 브랜드/상품 뉴스 5건을 분석하여 다음 규칙을 엄격히 지켜 응답해주세요:

1) summary: 기사 내용을 바탕으로 브랜드명 및 핵심 스펙 중심의 2줄 요약 (문장 앞에 • 포함, 줄바꿈은 <br>. 'Google News' 등 영문 시스템 문구 절대 제외)
2) insight: 11번가 MD 관점에서 경쟁사(쿠팡/네이버쇼핑 등) 대비 우위를 점할 수 있는 실질적인 소싱, 가격 전략, 셀러 협상, 기획전 전략 2줄 (문장 앞에 • 포함, 줄바꿈은 <br>).
*핵심 주의사항*: 5개 기사의 insight 내용이 절대 겹치지 않아야 합니다. (예: 1번은 묶음상품 단가 협상, 2번은 남성 타겟 확장, 3번은 라이브 방송 기획, 4번은 뷰티플러스 쿠폰 활용 등 각각 다른 각도의 전략 제시)

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
            
            with urllib.request.urlopen(req, timeout=20) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                parsed = json.loads(res_data["candidates"][0]["content"]["parts"][0]["text"])
                for p in parsed:
                    idx = p.get("index", 0)
                    if 0 <= idx < len(articles):
                        articles[idx]["summary"] = p.get("summary", "")
                        articles[idx]["insight"] = p.get("insight", "")
                return articles
        except Exception as e:
            print(f"⚠️ AI 호출 오류: {e}. 규칙 기반 엔진으로 전환합니다.")

    # 💡 규칙 기반 엔진 고도화: 담당 카테고리(스킨, 선케어, 남성, 클렌징) 중심의 구체적 전략 세분화
    RULES = [
        (["비레디", "오브제", "남성", "맨즈", "포맨"], "• 맨즈 뷰티 카테고리 성장세에 맞춰 남성 전용 올인원/메이크업 기획전 메인 구좌 편성.<br>• 그루밍족 타겟을 위한 11번가 단독 트래블 키트 증정 협상으로 객단가 상승 도모."),
        (["선크림", "선쿠션", "선케어", "자외선", "달바"], "• 시즌 리스 아이템화 된 선케어 특성을 반영하여 대용량 1+1 묶음 구성 셀러와 가격 협상.<br>• 타 플랫폼 대비 가격 우위 선점을 위한 뷰티 단독 쿠폰 적극 연계."),
        (["메디힐", "토리든", "스킨푸드", "패드", "클렌징", "일소"], "• 스킨케어 및 클렌징 루틴의 필수품인 토너패드/클렌징오일 대용량 기획전 11절 타겟팅.<br>• 소모 주기가 짧은 품목 특성상 장바구니 쿠폰 연계로 락인 효과 극대화."),
        (["에스트라", "닥터지", "아누아", "진정", "장벽"], "• 민감성/트러블 케어 수요를 겨냥한 더마 코스메틱 위크 기획 및 단독 굿즈 결합.<br>• 상세페이지 내 11번가 고객 우수 리뷰 최상단 노출 세팅으로 전환율 견인."),
        (["바이오던스", "마스크팩", "슬리핑", "모공"], "• 홈케어/슬로에이징 트렌드에 부합하는 고기능성 팩류 단독 선론칭 물량 확보 필수.<br>• 시연 위주 숏폼 콘텐츠 기획으로 초기 구매 전환율 및 바이럴 촉진."),
        (["롬앤", "클리오", "웨이크메이크", "퓌", "색조"], "• 시즌 신규 컬러 론칭 시점에 맞춘 선오픈 특가 및 11번가 단독 증정품 기획.<br>• 1020 타겟 유입을 위한 인플루언서 콜라보 마케팅 및 선물하기 서비스 적극 연동.")
    ]
    
    DEFAULT_INSIGHTS = [
        "• 주요 이커머스 베스트셀러의 11번가 내 가격 경쟁력 상시 모니터링 및 셀러 단가 협상.<br>• 리뷰 평점이 높은 라이징 상품을 발굴하여 뷰티 탭 메인 배너 노출로 초기 트래픽 집중 지원.",
        "• 핵심 타겟층의 검색 키워드 트렌드를 반영한 기획전 타이틀 도출 및 연관 상품 크로스셀링 유도.<br>• 시즌 오프 및 리뉴얼 이슈가 있는 상품군의 클리어런스 세일 기획으로 단기 매출 볼륨 확대.",
        "• 뷰티 고관여 고객 확대를 위한 단독 구성(본품+미니어처 다수) 소싱으로 가심비 공략.<br>• 충성 고객 대상 추가 적립 혜택을 부여하여 타사 대비 체감 혜택 극대화 및 충성도 제고."
    ]
    
    used_insights = set()
    default_insight_index = 0

    for idx, a in enumerate(articles):
        title = a["title"]
        desc = a["desc"]
        bad_phrases = ["Google News", "Comprehensive up-to-date", "aggregated from sources", "Google"]
        if any(b in desc for b in bad_phrases): desc = ""
        clean_title = re.sub(r'\[.*?\]', '', title)
        clean_title = re.sub(r'By\s+[A-Za-z0-9가-힣]+', '', clean_title).strip()
        
        if desc and len(desc) > 20:
            clean_s = [s.strip() for s in re.split(r'[.!?]', desc) if len(s.strip()) > 10 and not any(b in s for b in bad_phrases)]
            if len(clean_s) >= 2: a["summary"] = f"• {clean_s[0]}.<br>• {clean_s[1]}."
            elif len(clean_s) == 1: a["summary"] = f"• {clean_title}.<br>• {clean_s[0]}."
            else: a["summary"] = f"• {clean_title}.<br>• H&B 및 온라인 뷰티 채널 내 주요 트렌드 실시간 모니터링 필요."
        else:
            t_lower = (title + " " + a["source"]).lower()
            if any(k in t_lower for k in ["에디션", "콜라보", "한정판"]): a["summary"] = f"• {clean_title}.<br>• 한정판 기획 에디션 출시로 희소성 및 소장 가치를 앞세운 타깃 공략 본격화."
            elif any(k in t_lower for k in ["쿠션", "파운데이션", "베이스"]): a["summary"] = f"• {clean_title}.<br>• 밀착력과 지속력을 강화한 베이스 신제품으로 메이크업 교체 수요 공략."
            elif any(k in t_lower for k in ["앰플", "세럼", "크림", "더마"]): a["summary"] = f"• {clean_title}.<br>• 스킨케어 핵심 라인업 강화를 통한 기초화장품 매출 견인 및 고객 확보."
            elif any(k in t_lower for k in ["선크림", "선쿠션", "자외선"]): a["summary"] = f"• {clean_title}.<br>• 데일리 선케어 수요 증가에 맞춘 기능성 자외선 차단제 라인업 확장."
            elif any(k in t_lower for k in ["클렌징", "세안", "오일"]): a["summary"] = f"• {clean_title}.<br>• 저자극 및 딥클렌징 트렌드를 반영한 페이셜 클렌저 신제품 출시."
            elif any(k in t_lower for k in ["남성", "포맨", "올인원"]): a["summary"] = f"• {clean_title}.<br>• 세분화되는 맨즈 뷰티 니즈에 맞춘 남성 전용 스킨케어/메이크업 라인 출시."
            else: a["summary"] = f"• {clean_title}.<br>• 브랜드 주력 신상품 온·오프라인 론칭 및 전략적 마케팅 프로모션 전개."
            
        assigned = False
        text = title + " " + desc
        # 1차: 키워드 매칭 (중복 피하기)
        for keywords, insight_text in RULES:
            if insight_text in used_insights: continue
            if any(k in text for k in keywords):
                a["insight"] = insight_text
                used_insights.add(insight_text)
                assigned = True
                break
        
        # 2차: 강제 할당 (키워드 매칭 실패 시 사용하지 않은 규칙 중에서)
        if not assigned:
            for _, insight_text in RULES:
                if insight_text not in used_insights:
                    a["insight"] = insight_text
                    used_insights.add(insight_text)
                    assigned = True
                    break
        
        # 3차: 예비 인사이트 순차 할당 (규칙 초과 시)
        if not assigned:
            a["insight"] = DEFAULT_INSIGHTS[default_insight_index % len(DEFAULT_INSIGHTS)]
            default_insight_index += 1

    return articles

# ══════════════════════════════════════════════════════
# ▶ 4. 실행 및 HTML 리포트 생성
# ══════════════════════════════════════════════════════
print("🔍 구글 뉴스 크롤링 시작...")
articles = fetch_cosmetic_news()
if not articles:
    raise Exception("국내 브랜드 뉴스를 크롤링하지 못했습니다.")

articles = generate_insights(articles)

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

html_content = f"""
<div style="background-color:#ffffff; padding:20px 10px; font-family:'11StreetGothic', '11STREET Gothic', '11번가 고딕', 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;">
  <table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width:680px; margin:0 auto; background-color:#ffffff; border:1px solid #eaeaea; border-radius:12px; overflow:hidden;">
    <tr>
      <td align="center" style="background-color:#FA2828; padding:28px 20px; color:#ffffff;">
        <div style="font-size:12px; font-weight:bold; letter-spacing:1px; opacity:0.9; margin-bottom:6px;">11ST BEAUTY MD BRIEF · DAILY REPORT</div>
        <h2 style="margin:0; font-size:23px; font-weight:800; line-height:1.3; letter-spacing:-0.5px;">11번가 뷰티 MD 인사이트 리포트</h2>
        <div style="font-size:13px; margin-top:8px; font-weight:600; opacity:0.95;">{date_str}</div>
      </td>
    </tr>
    <tr>
      <td style="padding:24px 20px; background-color:#ffffff;">
        {cards_html}
      </td>
    </tr>
    <tr>
      <td align="center" style="background-color:#ffffff; padding:18px; font-size:12px; color:#999999; border-top:1px solid #eeeeee;">
        본 리포트는 11번가 뷰티 MD를 위해 매일 오전 최신 시장 동향을 자동 분석하여 작성됩니다.
      </td>
    </tr>
  </table>
</div>
"""

# ══════════════════════════════════════════════════════
# ▶ 5. 이메일 구성 및 Gmail 임시보관함 적재
# ══════════════════════════════════════════════════════
print("📩 Gmail 임시보관함에 저장 중...")
msg = MIMEMultipart("alternative")
msg["Subject"] = f"[11번가 뷰티 MD 인사이트 리포트] 일간 트렌드 및 브리프 ({now.tm_year}-{now.tm_mon:02d}-{now.tm_mday:02d})"
msg["From"] = GMAIL_USER
msg["To"] = TO_EMAIL
msg.attach(MIMEText(html_content, "html"))

if not GMAIL_PASS:
    raise ValueError("GMAIL_APP_PASSWORD가 설정되지 않았습니다.")

imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(GMAIL_USER, GMAIL_PASS)

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
        print(f"✅ 성공: [{folder}] 폴더에 MD 리포트 초안이 정상 생성되었습니다.")
        success = True
        break

if not success:
    raise Exception("임시보관함 폴더를 찾지 못해 초안 생성에 실패했습니다.")

imap.logout()
