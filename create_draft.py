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

weekdays = ["월", "화", "수", "목", "금", "토", "일"]
now = time.localtime()
date_str = f"{now.tm_year}년 {now.tm_mon:02d}월 {now.tm_mday:02d}일 ({weekdays[now.tm_wday]})"

# ══════════════════════════════════════════════════════
# ▶ 2. 뉴스 데이터 수집 (최근 8시간 이내, 브랜드 무관 뷰티 전체)
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
    # 💡 특정 브랜드명을 제외하고, 뷰티 카테고리를 포괄하는 키워드로 폭넓게 탐색
    category_keywords = "화장품 OR 뷰티 OR 스킨케어 OR 메이크업 OR 코스메틱 OR 더마 OR 선케어 OR 클렌징 OR 향수"
    action_keywords = "신제품 OR 출시 OR 신상 OR 론칭 OR 팝업 OR 콜라보 OR 앰배서더 OR 완판 OR 랭킹 OR 돌파"
    
    # 💡 when:8h (최근 8시간 이내) 옵션으로 가장 최신 이슈만 추출
    query = f"({category_keywords}) ({action_keywords}) when:8h"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    
    articles = []
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tree = ET.fromstring(resp.read())
            items = tree.findall(".//item")
            for item in items:
                raw_title = (item.find("title").text or "").strip()
                link = (item.find("link").text or "").strip()
                source_elem = item.find("source")
                source_name = source_elem.text.strip() if source_elem is not None and source_elem.text else "뷰티매체"
                
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    if not source_name or source_name == "뷰티매체":
                        source_name = parts[1].strip()
                else:
                    title = raw_title
                    
                # 💡 보도자료 복붙 기사 방지 (제목 앞 12글자 유사도 필터링)
                title_prefix = title.replace(" ", "")[:12]
                if any(a["title"].replace(" ", "")[:12] == title_prefix for a in articles):
                    continue
                    
                meta_desc = fetch_article_summary(link)
                
                articles.append({
                    "title": title,
                    "source": source_name,
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
            prompt = """당신은 11번가 뷰티 카테고리 전문 MD입니다. 스킨케어, 메이크업, 남성화장품 등 뷰티 전반을 담당합니다. 
아래 주요 뷰티 뉴스 5건을 분석하여 다음 규칙을 엄격히 지켜 응답해주세요:

1) summary: 기사 내용을 바탕으로 론칭 브랜드명 및 핵심 스펙 중심의 2줄 요약 (문장 앞에 • 포함, 줄바꿈은 <br>. 'Google News' 등 영문 시스템 문구 절대 제외)
2) insight: 11번가 MD 관점에서 경쟁사(쿠팡/네이버쇼핑 등) 대비 우위를 점할 수 있는 실질적인 소싱, 가격 전략, 셀러 협상, 기획전 전략 2줄 (문장 앞에 • 포함, 줄바꿈은 <br>).
*핵심 주의사항*: 5개 기사의 insight 내용이 절대 겹치지 않아야 합니다. (예: 1번은 신규 브랜드 입점 제안, 2번은 단독 굿즈 확보, 3번은 타겟팅 쿠폰 활용 등 각각 다른 각도의 전략 제시)

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

    # AI 호출 실패 시 적용될 범용 규칙
    RULES = [
        (["남성", "맨즈", "포맨", "옴므"], "• 맨즈 뷰티 성장세에 맞춰 남성 전용 올인원/메이크업 기획전 메인 구좌 편성.<br>• 그루밍족 타겟을 위한 11번가 단독 트래블 키트 증정 협상으로 객단가 상승 도모."),
        (["선크림", "선쿠션", "선케어", "자외선"], "• 시즌 리스 아이템화 된 선케어 특성을 반영하여 대용량 1+1 묶음 구성 셀러와 가격 협상.<br>• 타 플랫폼 대비 가격 우위 선점을 위한 뷰티 단독 쿠폰 적극 연계."),
        (["패드", "클렌징", "토너", "모공"], "• 스킨케어 및 클렌징 루틴의 필수품인 토너패드/클렌징오일 대용량 기획전 11절 타겟팅.<br>• 소모 주기가 짧은 품목 특성상 장바구니 쿠폰 연계로 락인 효과 극대화."),
        (["진정", "장벽", "더마", "민감성"], "• 민감성/트러블 케어 수요를 겨냥한 더마 코스메틱 위크 기획 및 단독 굿즈 결합.<br>• 상세페이지 내 11번가 고객 우수 리뷰 최상단 노출 세팅으로 전환율 견인."),
        (["색조", "립", "틴트", "쿠션", "팔레트"], "• 시즌 신규 컬러 론칭 시점에 맞춘 선오픈 특가 및 11번가 단독 증정품 기획.<br>• 1020 타겟 유입을 위한 인플루언서 콜라보 마케팅 및 선물하기 서비스 적극 연동.")
    ]
    
    DEFAULT_INSIGHTS = [
        "• 주요 이커머스 베스트셀러의 11번가 내 가격 경쟁력 상시 모니터링 및 셀러 단가 협상.<br>• 리뷰 평점이 높은 라이징 상품을 발굴하여 뷰티 탭 메인 배너 노출로 초기 트래픽 집중 지원.",
        "• 신규 론칭 브랜드의 빠른 플랫폼 안착을 위한 프로모션 구좌 제안 및 단독 혜택 기획.<br>• 화제성 높은 뷰티 신상품의 11번가 선론칭을 타진하여 트래픽 선점 효과 극대화.",
        "• 뷰티 고관여 고객 확대를 위한 단독 구성(본품+미니어처 다수) 소싱으로 가심비 공략.<br>• 충성 고객 대상 추가 적립 혜택을 부여하여 타사 대비 체감 혜택 극대화 및 충성도 제고."
    ]
    
    used_insights = set()
    default_insight_index = 0

    for idx, a in enumerate(articles):
        title = a["title"]
        desc = a["desc"]
        clean_title = re.sub(r'\[.*?\]', '', title).strip()
        
        if desc and len(desc) > 20:
            clean_s = [s.strip() for s in re.split(r'[.!?]', desc) if len(s.strip()) > 10]
            if len(clean_s) >= 2: a["summary"] = f"• {clean_s[0]}.<br>• {clean_s[1]}."
            elif len(clean_s) == 1: a["summary"] = f"• {clean_title}.<br>• {clean_s[0]}."
            else: a["summary"] = f"• {clean_title}.<br>• H&B 및 온라인 뷰티 채널 내 신제품 론칭 트렌드 모니터링."
        else:
            a["summary"] = f"• {clean_title}.<br>• 라이징 뷰티 브랜드 주력 신상품 론칭 및 마케팅 프로모션 전개."
            
        assigned = False
        text = title + " " + desc
        for keywords, insight_text in RULES:
            if insight_text in used_insights: continue
            if any(k in text for k in keywords):
                a["insight"] = insight_text
                used_insights.add(insight_text)
                assigned = True
                break
        
        if not assigned:
            a["insight"] = DEFAULT_INSIGHTS[default_insight_index % len(DEFAULT_INSIGHTS)]
            default_insight_index += 1

    return articles

# ══════════════════════════════════════════════════════
# ▶ 4. 실행 및 HTML 리포트 생성 (11번가 레드 배너)
# ══════════════════════════════════════════════════════
print("🔍 뷰티 최신 뉴스 크롤링 시작...")
articles = fetch_cosmetic_news()

# 💡 8시간 내 기사가 없을 경우를 대비한 유연한 예외 처리
if not articles:
    print("⚠️ 최근 8시간 내 매칭되는 신규 기사가 없어 기본 트렌드 리포트를 생성합니다.")
    articles = [{
        "title": "최근 8시간 내 주요 뷰티 신제품 론칭 보도자료 없음",
        "source": "11ST MD System",
        "link": "#",
        "desc": "금일 오전 기준 뷰티 카테고리 공식 보도자료 및 신제품 이슈가 없습니다. 상시 기획전 구좌 점검 및 기존 베스트셀러 가격 모니터링에 집중하시기 바랍니다.",
        "summary": "• 최근 8시간 내 뷰티 브랜드 공식 보도자료 및 신제품 론칭 이슈 없음.<br>• 11번가 내 주요 셀러 기획전 현황 점검 및 단가 경쟁력 확보 집중.",
        "insight": "• 뷰티 메인 구좌 체류 시간 증대를 위한 시즈널 기획전 배너 카피라이팅 최적화.<br>• 트래픽 비수기 방어를 위해 타사 베스트 랭킹 교차 검증 후 장바구니 혜택 강화."
    }]
else:
    articles = generate_insights(articles)

cards_html = ""
for idx, a in enumerate(articles):
    num_str = f"[{idx+1:02d} / {len(articles):02d}]"
    is_last = (idx == len(articles) - 1)
    border_style = "padding-bottom:10px;" if is_last else "padding-bottom:30px; margin-bottom:30px; border-bottom:1px solid #E5E5E5;"
    
    cards_html += f"""
        <div style="{border_style}">
          <div style="font-size:14px; color:#FA2828; font-weight:900; margin-bottom:8px; letter-spacing:0.5px;">{num_str} <span style="color:#555555; background-color:#F4F4F4; padding:2px 8px; border-radius:4px; margin-left:4px; font-size:12px;">{a['source']}</span></div>
          <div style="font-size:20px; font-weight:800; color:#111111; margin-bottom:16px; line-height:1.4; letter-spacing:-0.5px;">
             {a['title']}
          </div>
          <div style="font-size:15px; color:#444444; line-height:1.7; margin-bottom:20px; letter-spacing:-0.3px;">
            {a['summary']}
          </div>
          <div style="background-color:#FFF5F5; border-radius:10px; padding:18px 20px; border-left:4px solid #FA2828; font-size:14px; line-height:1.65; color:#222222; margin-bottom:16px; letter-spacing:-0.2px;">
            <b style="color:#FA2828; display:block; margin-bottom:6px; font-size:15px;">💡 MD 인사이트:</b>
            {a['insight']}
          </div>
          <div style="text-align:right;">
            <a href="{a['link']}" target="_blank" style="display:inline-block; border:1px solid #FA2828; color:#FA2828; padding:8px 16px; border-radius:6px; font-size:13px; text-decoration:none; font-weight:800; letter-spacing:-0.2px;">기사 원문 보기 &gt;</a>
          </div>
        </div>
    """

html_content = f"""
<div style="background-color:#F7F8F9; padding:40px 10px; font-family:'11STREET Gothic', '11번가 고딕', 'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;">
  <table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width:720px; margin:0 auto; background-color:#ffffff; border:1px solid #DDDDDD; border-radius:16px; overflow:hidden;">
    <tr>
      <td align="center" style="background-color:#FA2828; padding:35px 20px; color:#ffffff;">
        <div style="font-size:13px; font-weight:800; letter-spacing:1px; opacity:0.9; margin-bottom:8px;">11ST BEAUTY MD BRIEF · DAILY REPORT</div>
        <h2 style="margin:0; font-size:26px; font-weight:900; line-height:1.35; letter-spacing:-0.5px; color:#ffffff;">11번가 뷰티 MD 인사이트 리포트</h2>
        <div style="font-size:14px; margin-top:10px; font-weight:700; opacity:0.9; letter-spacing:-0.2px;">{date_str} 발행</div>
      </td>
    </tr>
    <tr>
      <td style="padding:40px 30px; background-color:#ffffff;">
        {cards_html}
      </td>
    </tr>
    <tr>
      <td align="center" style="background-color:#F9F9F9; padding:25px; font-size:12px; color:#888888; border-top:1px solid #EEEEEE; line-height:1.6; letter-spacing:-0.3px;">
        본 리포트는 11번가 뷰티 MD를 위해<br>최근 8시간 내 등록된 뷰티 신제품 및 트렌드 기사를 자동 분석하여 작성됩니다.
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
msg["Subject"] = f"[11번가 뷰티 MD 인사이트 리포트] 최신 뷰티 트렌드 브리프 ({now.tm_year}-{now.tm_mon:02d}-{now.tm_mday:02d})"
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
