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
msg["Subject"] = f"[11번가 뷰티 MD 인사이트 리포트] 일간 트렌드 및 브리프 ({time.strftime('%Y-%m-%d')})"
msg["From"] = GMAIL_USER
msg["To"] = TO_EMAIL

html_content = f"""
<div style="background-color:#f4f5f8; padding:24px 10px; font-family:'Apple SD Gothic Neo', -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;">
  <table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width:680px; margin:0 auto; background-color:#ffffff; border:1px solid #e2e4e8; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.04);">
    <!-- 상단 11번가 레드 헤더 배너 -->
    <tr>
      <td align="center" style="background-color:#FA2828; padding:28px 20px; color:#ffffff;">
        <div style="font-size:12px; font-weight:bold; letter-spacing:1px; opacity:0.9; margin-bottom:6px;">11ST BEAUTY MD BRIEF · DAILY REPORT</div>
        <h2 style="margin:0; font-size:22px; font-weight:bold; line-height:1.3;">11번가 뷰티 MD 인사이트 리포트</h2>
        <div style="font-size:13px; margin-top:8px; opacity:0.85;">{time.strftime('%Y년 %m월 %d일')}</div>
      </td>
    </tr>

    <!-- 본문 컨테이너 (라이트 그레이 배경) -->
    <tr>
      <td style="background-color:#f4f5f8; padding:20px 16px;">

        <!-- [01 / 05] -->
        <div style="background-color:#ffffff; border-radius:10px; padding:20px; margin-bottom:16px; border:1px solid #e5e7eb; border-left:4px solid #FA2828;">
          <div style="font-size:12px; color:#FA2828; font-weight:bold; margin-bottom:6px;">[01 / 05] 테크M · 유통</div>
          <div style="font-size:16px; font-weight:bold; color:#1f2937; margin-bottom:10px; line-height:1.4;">무신사·다이소 오프라인 출점 격돌… '올리브영 독점'에 정면 도전</div>
          <div style="font-size:13px; color:#4b5563; line-height:1.6; margin-bottom:12px;">
            • 성수·홍대 중심 무신사 뷰티 플래그십 출점과 다이소의 초저가 뷰티 매대 확장이 맞물리며 오프라인 독점 구도 균열.<br>
            • 온라인 인디 뷰티 발굴 플랫폼들이 오프라인 체험 거점을 공격적으로 늘리며 1020 유입 락인 가속.
          </div>
          <div style="background-color:#fef2f2; border-radius:6px; padding:12px; border-left:3px solid #FA2828; font-size:13px; line-height:1.5; color:#374151;">
            <b style="color:#FA2828;">💡 MD 인사이트:</b><br>
            • 오프라인 팝업 체험 후 앱 쿠폰으로 결제하는 '역쇼루밍' 락인 효과가 핵심 경쟁력으로 부상.<br>
            • 11번가 뷰티플러스 내 성수 핫플 입점 인디 브랜드 단독관 구성 및 1020 전용 쿠폰팩 연계 추천.
          </div>
          <div style="text-align:right; margin-top:12px;">
            <a href="https://www.techm.kr/news/articleView.html?idxno=155047" target="_blank" style="color:#6b7280; font-size:12px; text-decoration:none; font-weight:600;">🔗 기사 원문 보기 &gt;</a>
          </div>
        </div>

        <!-- [02 / 05] -->
        <div style="background-color:#ffffff; border-radius:10px; padding:20px; margin-bottom:16px; border:1px solid #e5e7eb; border-left:4px solid #FA2828;">
          <div style="font-size:12px; color:#FA2828; font-weight:bold; margin-bottom:6px;">[02 / 05] 메트로신문 · 데일리안</div>
          <div style="font-size:16px; font-weight:bold; color:#1f2937; margin-bottom:10px; line-height:1.4;">에이피알, 시총 14조 돌파… 아모레·LG생건 합산 시총 추월</div>
          <div style="font-size:13px; color:#4b5563; line-height:1.6; margin-bottom:12px;">
            • 뷰티 디바이스 '메디큐브 부스터프로' 글로벌 수출 돌풍으로 에이피알 시총 14조 원대 안착.<br>
            • 디바이스 판매에 그치지 않고 전용 PDRN·엑소좀 고기능성 스킨케어 앰플 라인의 반복 구매 선순환 구조 확립.
          </div>
          <div style="background-color:#fef2f2; border-radius:6px; padding:12px; border-left:3px solid #FA2828; font-size:13px; line-height:1.5; color:#374151;">
            <b style="color:#FA2828;">💡 MD 인사이트:</b><br>
            • 뷰티 디바이스와 고기능성 앰플의 결합이 글로벌 대세로 안착, 크로스셀링 객단가 상승 기회 입증.<br>
            • 기기 단품보다 전용 앰플을 묶은 '홈에스테틱 스타터 세트' 단독 물량 선확보 및 11절 편성 권장.
          </div>
          <div style="text-align:right; margin-top:12px;">
            <a href="https://www.metroseoul.co.kr/article/20260820500039" target="_blank" style="color:#6b7280; font-size:12px; text-decoration:none; font-weight:600;">🔗 기사 원문 보기 &gt;</a>
          </div>
        </div>

        <!-- [03 / 05] -->
        <div style="background-color:#ffffff; border-radius:10px; padding:20px; margin-bottom:16px; border:1px solid #e5e7eb; border-left:4px solid #FA2828;">
          <div style="font-size:12px; color:#FA2828; font-weight:bold; margin-bottom:6px;">[03 / 05] 식약처 · Bazzaal</div>
          <div style="font-size:16px; font-weight:bold; color:#1f2937; margin-bottom:10px; line-height:1.4;">상반기 화장품 수출 70억 달러 역대 최대… 미국 시장 1위 등극</div>
          <div style="font-size:13px; color:#4b5563; line-height:1.6; margin-bottom:12px;">
            • 2026년 상반기 화장품 수출이 전년 대비 27.3% 늘어난 70억 달러 기록, 대미 수출 사상 첫 1위 달성.<br>
            • 아마존과 틱톡숍을 중심으로 저자극 데일리 선케어 및 피부 진정 패드 카테고리 수요 폭증.
          </div>
          <div style="background-color:#fef2f2; border-radius:6px; padding:12px; border-left:3px solid #FA2828; font-size:13px; line-height:1.5; color:#374151;">
            <b style="color:#FA2828;">💡 MD 인사이트:</b><br>
            • 아마존·틱톡숍 상위 랭킹의 선케어·패드가 글로벌 역직구 핵심 효자 품목으로 정착.<br>
            • '해외 직구 검증 톱랭킹 뷰티' 테마 기획전을 통해 미국 완판 SKU를 역직구관 메인 구좌에 집중 노출 필요.
          </div>
          <div style="text-align:right; margin-top:12px;">
            <a href="https://www.bazzaal.com/ko/blog/us-k-beauty-market-h2-2026" target="_blank" style="color:#6b7280; font-size:12px; text-decoration:none; font-weight:600;">🔗 기사 원문 보기 &gt;</a>
          </div>
        </div>

        <!-- [04 / 05] -->
        <div style="background-color:#ffffff; border-radius:10px; padding:20px; margin-bottom:16px; border:1px solid #e5e7eb; border-left:4px solid #FA2828;">
          <div style="font-size:12px; color:#FA2828; font-weight:bold; margin-bottom:6px;">[04 / 05] 조선일보 · 마켓트렌드</div>
          <div style="font-size:16px; font-weight:bold; color:#1f2937; margin-bottom:10px; line-height:1.4;">올리브영·무신사, 외국인 관광객 소비 따라 지방 거점 매장 확대</div>
          <div style="font-size:13px; color:#4b5563; line-height:1.6; margin-bottom:12px;">
            • 명동·성수를 넘어 부산·제주·대구 등 지방 핵심 상권으로 외국인 K-뷰티 쇼핑 동선 확장.<br>
            • 휴대성 높은 소용량 미니 앰플, 멀티 듀얼 립 제품의 현장 픽업 및 즉시 구매 비중 대폭 증가.
          </div>
          <div style="background-color:#fef2f2; border-radius:6px; padding:12px; border-left:3px solid #FA2828; font-size:13px; line-height:1.5; color:#374151;">
            <b style="color:#FA2828;">💡 MD 인사이트:</b><br>
            • 본품 구매 전 테스트를 선호하는 Z세대와 여행객 특성상 '미니 사이즈·트래블 키트' 수요 급증.<br>
            • 1만 원 미만 균일가 소용량 체험팩 및 무료배송 혜택을 연계해 첫 구매 장벽을 낮추는 프로모션 적합.
          </div>
          <div style="text-align:right; margin-top:12px;">
            <a href="https://www.chosun.com/economy/market_trend/2026/09/09/YLK5UZIZXJAD5BRP23KHWWDOKU/" target="_blank" style="color:#6b7280; font-size:12px; text-decoration:none; font-weight:600;">🔗 기사 원문 보기 &gt;</a>
          </div>
        </div>

        <!-- [05 / 05] -->
        <div style="background-color:#ffffff; border-radius:10px; padding:20px; margin-bottom:6px; border:1px solid #e5e7eb; border-left:4px solid #FA2828;">
          <div style="font-size:12px; color:#FA2828; font-weight:bold; margin-bottom:6px;">[05 / 05] 리테일톡 · 트렌드</div>
          <div style="font-size:16px; font-weight:bold; color:#1f2937; margin-bottom:10px; line-height:1.4;">가을 환절기 더마 뷰티 격전… 고효능 PDRN·성분 중심 리페어 급부상</div>
          <div style="font-size:13px; color:#4b5563; line-height:1.6; margin-bottom:12px;">
            • 9월 환절기 진입으로 피부 장벽 회복과 고보습을 겨냥한 더마 코스메틱 매출 급상승.<br>
            • 브랜드 네임보다 PDRN, 판테놀, 세라마이드 등 유효 성분 함량이 구매 결정의 핵심 요인으로 대두.
          </div>
          <div style="background-color:#fef2f2; border-radius:6px; padding:12px; border-left:3px solid #FA2828; font-size:13px; line-height:1.5; color:#374151;">
            <b style="color:#FA2828;">💡 MD 인사이트:</b><br>
            • 환절기 기초 수요가 단순 수분에서 '피부 재생·장벽 리페어 고효능 더마'로 전환되는 골든타임.<br>
            • 추석 선물세트 및 환절기 대비 1+1 리페어 크림 프로모션 조기 편성 시 높은 전환율 견인.
          </div>
          <div style="text-align:right; margin-top:12px;">
            <a href="https://retailtalk.co.kr/Trend/?idx=173443001&bmode=view" target="_blank" style="color:#6b7280; font-size:12px; text-decoration:none; font-weight:600;">🔗 기사 원문 보기 &gt;</a>
          </div>
        </div>

      </td>
    </tr>

    <!-- 푸터 -->
    <tr>
      <td align="center" style="background-color:#ffffff; padding:18px; font-size:12px; color:#9ca3af; border-top:1px solid #e5e7eb;">
        본 리포트는 11번가 뷰티 MD를 위해 매일 오전 최신 시장 동향을 분석하여 작성됩니다.
      </td>
    </tr>
  </table>
</div>
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
        print(f"성공: [{folder}] 폴더에 5개 항목 리포트 초안이 정상 생성되었습니다.")
        success = True
        break

if not success:
    raise Exception("임시보관함 폴더를 찾지 못해 초안 생성에 실패했습니다.")

imap.logout()
