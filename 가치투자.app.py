import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import urllib.parse

st.set_page_config(page_title="AGIE", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.main {background-color: #0d1117; color: #c9d1d9;}
h1, h2, h3 {color: #58a6ff;}
.box {background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d;}
.guru-quote {font-style: italic; color: #8b949e; border-left: 3px solid #e3b341; padding-left: 10px; margin-bottom: 10px;}
.highlight {color: #da3633; font-weight: bold;}
.good {color: #3fb950; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

def tr(txt):
    if not txt: return txt
    try:
        return GoogleTranslator(source='en', target='ko').translate(txt[:1000])
    except:
        return txt

def get_nv(cd):
    url = "https://finance.naver.com/item/main.naver?code=" + cd
    h = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=h)
        s = BeautifulSoup(r.text, 'html.parser')
        i = {}
        t = s.select_one('.wrap_company h2 a')
        if t: i['name'] = t.text
        t = s.select_one('#_per')
        if t: i['pe'] = float(t.text.replace(',',''))
        t = s.select_one('#_pbr')
        if t: i['pbr'] = float(t.text.replace(',',''))
        t = s.select_one('#_cns_per')
        if t: i['fpe'] = float(t.text.replace(',',''))
        t = s.select_one('#_dvr')
        if t: i['div'] = float(t.text.replace(',',''))/100
        t = s.select_one('.summary_info p')
        if t: i['sum'] = t.text
        return i
    except:
        return None

def get_data(tk):
    if "." not in tk: tk = tk.upper()
    kr = tk.endswith('.KS') or tk.endswith('.KQ')
    cd = tk.split('.')[0] if kr else tk
    stk = yf.Ticker(tk)
    p, i = None, {}
    for _ in range(3):
        try:
            p = stk.fast_info['lastPrice']
            i = stk.info
            if not isinstance(i, dict): i = {}
            break
        except:
            time.sleep(1)
    if kr and p:
        nv = get_nv(cd)
        if nv:
            if 'name' in nv: i['shortName'] = nv['name']
            if 'pe' in nv: i['trailingPE'] = nv['pe']
            if 'fpe' in nv: i['forwardPE'] = nv['fpe']
            if 'pbr' in nv: i['priceToBook'] = nv['pbr']
            if 'div' in nv: i['dividendYield'] = nv['div']
            if 'sum' in nv: i['kr_sum'] = nv['sum']
    return stk, p, i, kr

# 실시간 CEO 리스크 구글 뉴스 파싱 함수
def get_ceo_news(ceo, kr):
    if not ceo or ceo == '누락': return []
    try:
        if kr:
            q = urllib.parse.quote(f'"{ceo}" 횡령 OR 배임 OR 사기 OR 논란')
            url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        else:
            q = urllib.parse.quote(f'"{ceo}" fraud OR scandal OR embezzlement')
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        
        h = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=h, timeout=3)
        s = BeautifulSoup(r.text, 'html.parser')
        items = s.find_all('item')[:3]
        res = []
        for item in items:
            t = item.title.text if item.title else ''
            if t: res.append(t)
        return res
    except:
        return []

def run_dcf(stk, i, p, ty):
    try:
        fcf_s = None
        cf = stk.cash_flow
        
        if cf is not None and not cf.empty:
            if 'Free Cash Flow' in cf.index:
                fcf_s = cf.loc['Free Cash Flow'].dropna()
            elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                fcf_s = (cf.loc['Operating Cash Flow'] + cf.loc['Capital Expenditure']).dropna()
                
        fcf = fcf_s.iloc[0] if (fcf_s is not None and not fcf_s.empty) else i.get('freeCashflow')
        if not fcf or fcf <= 0: return 0, 0, "주주이익(FCF) 적자", 0
        
        sh = i.get('sharesOutstanding')
        if not sh: return 0, 0, "주식수 누락", 0
        
        g = 0.05
        if fcf_s is not None and len(fcf_s) >= 2:
            c = fcf_s.iloc[0]
            o = fcf_s.iloc[-1]
            y_cnt = len(fcf_s) - 1
            if c > 0 and o > 0:
                g = (c / o) ** (1 / y_cnt) - 1
        else:
            eg = i.get('earningsGrowth')
            if eg: g = eg
            
        g = max(0.02, min(g, 0.15))
        dr = max(ty / 100, 0.09)
        cv = fcf
        fut = []
        
        for y in range(1, 11):
            cv *= (1 + g)
            fut.append(cv / ((1 + dr) ** y))
            
        tv = (cv * 1.02) / (dr - 0.02)
        dtv = tv / ((1 + dr) ** 10)
        
        iv = (sum(fut) + dtv) / sh
        mos = ((iv - p) / iv) * 100
        return iv, mos, None, g
    except:
        return 0, 0, "DCF 연산 에러", 0

st.title("⚡ AGIE Value Terminal")
st.error("🚨 시클리컬 기업 주의: 본 모델은 경제적 해자(Moat)를 갖춘 기업에 최적화되어 있습니다.")

# 바로가기용 사전일 뿐, 여기에 없는 티커(예: OXY, INTC 등)도 입력하면 모두 검색됩니다.
tmap = {
    "제이피모건":"JPM", "JP모건":"JPM", "애플":"AAPL", "구글":"GOOGL",
    "알파벳":"GOOGL", "마이크로소프트":"MSFT", "마소":"MSFT", "아마존":"AMZN",
    "테슬라":"TSLA", "엔비디아":"NVDA", "메타":"META", "페이스북":"META",
    "크록스":"CROX", "디어":"DE", "존디어":"DE", "캐터필러":"CAT", "캐타필러":"CAT",
    "TSMC":"TSM", "ASML":"ASML", "AMD":"AMD", "인텔":"INTC", "퀄컴":"QCOM",
    "일라이릴리":"LLY", "노보노디스크":"NVO", "유나이티드헬스":"UNH",
    "존슨앤존슨":"JNJ", "P&G":"PG", "월마트":"WMT", "코스트코":"COST",
    "홈디포":"HD", "비자":"V", "마스터카드":"MA", "무디스":"MCO",
    "코카콜라":"KO", "펩시":"PEP", "맥도날드":"MCD", "스타벅스":"SBUX",
    "넷플릭스":"NFLX", "디즈니":"DIS", "버크셔":"BRK-B", "보잉":"BA",
    "록히드마틴":"LMT", "GE":"GE", "브로드컴":"AVGO",
    "삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "현대차":"005380.KS",
    "기아":"000270.KS", "KB금융":"105560.KS", "신한지주":"055550.KS",
    "하나금융지주":"086790.KS", "메리츠금융지주":"138040.KS",
    "네이버":"035420.KS", "카카오":"035720.KS", "에코프로":"086520.KQ",
    "에코프로비엠":"247540.KQ", "셀트리온":"068270.KS",
    "LG엔솔":"373220.KS", "포스코홀딩스":"005490.KS", "삼성바이오로직스":"207940.KS"
}

ui = st.text_input("종목명 또는 티커 입력:", placeholder="아무 종목의 티커나 이름을 입력하세요 (예: AAPL, 구글, 005930.KS)")
if st.button("가치 분석 심층 스캔", type="primary"):
    if ui:
        with st.spinner("데이터 스캔 및 실시간 뉴스 파싱 중..."):
            q = ui.replace(" ", "").upper()
            tk = tmap.get(q, q)
            stk, p, i, kr = get_data(tk)
            
            if p:
                try:
                    ty = yf.Ticker("^TNX").fast_info['lastPrice']
                except:
                    ty = 4.4
                    
                name = i.get('shortName', tk)
                st.success(f"🏢 {name} ({tk}) 분석 완료")
                
                c1, c2 = st.columns(2)
                
                t_pe = i.get('trailingPE', 0)
                f_pe = i.get('forwardPE', 0)
                pbr = i.get('priceToBook', 0)
                div = i.get('dividendYield', 0) * 100
                roe = i.get('returnOnEquity', 0) * 100
                
                a_pe = i.get('fiveYearAvgPE')
                if not a_pe: a_pe = t_pe * 1.1 if t_pe > 0 else 15.0
                
                pmos = 0
                if f_pe > 0 and a_pe > 0:
                    pmos = ((a_pe - f_pe) / a_pe) * 100
                    
                ey = (1 / f_pe * 100) if f_pe > 0 else 0
                iv, mos, err, g_rate = run_dcf(stk, i, p, ty)
                
                with c1:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("📊 1. 밸류에이션 & 안전마진")
                    st.write(f"**현재 주가:** {p:,.2f}")
                    st.write(f"**배당 수익률:** {div:.2f}%")
                    
                    st.markdown("---")
                    st.write("**[상대 가치: PER & PBR]**")
                    st.write(f"- **현재 PER:** {t_pe:.2f}배")
                    st.write(f"- **Fwd PER:** {f_pe:.2f}배")
                    st.write(f"- **5~10년 평균 PER:** {a_pe:.2f}배")
                    
                    if pmos > 0:
                        st.markdown(f"▶ **PER 안전마진:** <span class='good'>+{pmos:.1f}%</span>", unsafe_allow_html=True)
                    elif pmos < 0:
                        st.markdown(f"▶ **PER 안전마진:** <span class='highlight'>{pmos:.1f}%</span>", unsafe_allow_html=True)
                    
                    st.write(f"- **PBR:** {pbr:.2f}배 (한국 주식은 PBR 위주)") if kr else st.write(f"- **PBR:** {pbr:.2f}배")
                    st.write(f"- **ROIC(ROE대체):** {roe:.2f}%")
                    st.caption("※ 확인이 필요한 부분: PER, EPS, PBR 지속 상승 추세 및 배당 일관성 여부")
                    
                    st.markdown("---")
                    st.write("**[이익수익률 vs 10년물 국채]**")
                    st.write(f"- 10년물 미국채 금리: {ty:.2f}%")
                    st.write(f"- 예상 이익수익률: {ey:.2f}%")
                    
                    st.markdown("---")
                    st.write("**[버핏식 주주이익(Owner Earnings) 10-Year DCF]**")
                    if iv:
                        st.write(f"- **적용된 FCF 연평균 성장률:** {g_rate*100:.1f}% (재무제표 기반)")
                        st.write(f"**추정 적정가:** {iv:,.2f}")
                        if mos > 0:
                            st.markdown(f"▶ **DCF 안전마진:** <span class='good'>+{mos:.1f}% (저평가)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"▶ **DCF 안전마진:** <span class='highlight'>{mos:.1f}% (고평가)</span>", unsafe_allow_html=True)
                    else:
                        st.error(f"⚠️ {err} (확인이 필요한 부분입니다)")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                with c2:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("🕵️‍♂️ 2. 질적 분석")
                    off = i.get('companyOfficers', [])
                    ceo = off[0].get('name') if off else '누락'
                    
                    st.markdown(f"- **CEO:** <span class='good'>{tr(ceo)}</span>", unsafe_allow_html=True)
                    
                    # 💡 실시간 구글 뉴스 파싱 요약 적용
                    st.markdown("**[🚨 실시간 경영진 리스크 뉴스 점검]**")
                    ceo_news = get_ceo_news(ceo, kr)
                    if ceo_news:
                        for news in ceo_news:
                            headline = news if kr else tr(news)
                            st.markdown(f"> - {headline}")
                        st.caption("※ 구글 뉴스 자동 검색 결과입니다. 정확하지 않은 정보일 수 있으니 팩트 체크가 필수인 부분입니다.")
                    else:
                        st.write("> 현재 구글 뉴스에 노출된 주요 횡령/사기/논란 헤드라인이 없습니다.")
                        st.caption("※ 정보 누락일 수 있으니, 직접 교차 검증은 필수입니다.")
                    
                    st.markdown("---")
                    sum_t = i.get('kr_sum', i.get('longBusinessSummary',''))
                    st.markdown(f"- **비즈니스 요약:**\n> {tr(sum_t)[:350]}...")
                    st.caption("※ 모든 판단은 사실 수집 및 임직원 의견을 반영하여 교차 검증하십시오.")
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("🤖 3. 데이터 기반 투자의견 자동 판별 (AI Report)")
                c3, c4 = st.columns(2)
                
                with c3:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.write("**[매수 6원칙 자동 체크]**")
                    
                    p_txt = "**1. 가격은 저렴한가 (안전마진)?**<br>"
                    if pmos > 0: p_txt += f"▶ PER 기준: <span class='good'>합격 (+{pmos:.1f}% 저평가)</span><br>"
                    elif pmos < 0: p_txt += f"▶ PER 기준: <span class='highlight'>주의 ({pmos:.1f}% 고평가)</span><br>"
                    else: p_txt += "▶ PER 기준: (확인이 필요한 부분입니다)<br>"
                    
                    if mos > 0: p_txt += f"▶ DCF 기준: <span class='good'>합격 (+{mos:.1f}% 저평가)</span>"
                    elif mos < 0: p_txt += f"▶ DCF 기준: <span class='highlight'>주의 ({mos:.1f}% 고평가)</span>"
                    else: p_txt += "▶ DCF 기준: (확인이 필요한 부분입니다)"
                    
                    st.markdown(p_txt, unsafe_allow_html=True)
                    
                    if roe >= 15:
                        biz_eval = f"<span class='good'>우수 (ROE {roe:.2f}%로 자본효율이 탁월하며 해자가 있을 확률이 높음)</span>"
                    elif roe > 0:
                        biz_eval = f"보통 (ROE {roe:.2f}%. 압도적 해자가 있는지 제품/서비스 독점력 추가 확인 필요)"
                    else:
                        biz_eval = f"<span class='highlight'>경고 (ROE {roe:.2f}%. 비즈니스 구조 훼손 가능성 점검 시급)</span>"
                    st.markdown(f"**2. 좋은 비즈니스인가?**<br>👉 {biz_eval}", unsafe_allow_html=True)
                    
                    st.write("**3. 경영진은 신뢰할 수 있는가?** 👉 위 실시간 뉴스 점검 탭을 확인하여 오너 리스크를 점검하십시오.")
                    st.write("**4. 놓친 리스크는 없는가?** 👉 현재 주가 하락이 단순한 '미스터 마켓의 우울증'인지 영구적 손상인지 확인하세요.")
                    st.write("**5~6. 능력 범위 안인가?** 👉 이 비즈니스 모델을 타인에게 논리적으로 재반박하며 설명할 수 있습니까?")
                    st.markdown("</div>", unsafe_allow_html=True)

                with c4:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.write("**[기업 해부 및 학문적 모델 적용]**")
                    
                    if g_rate > 0:
                        math_eval = f"<span class='good'>최근 주주이익(FCF) 기반 연평균 {g_rate*100:.1f}%씩 성장하며 '복리 모형'에 탑승 중.</span>"
                    else:
                        math_eval = "<span class='highlight'>현금흐름이 역성장 또는 적자이므로 복리 팽창 구간이 아닙니다.</span>"
                        
                    st.markdown(f"- **수학 (복리 모형):** {math_eval}", unsafe_allow_html=True)
                    st.write("- **생물학 (생존력):** 부채 및 유동자산 구조를 볼 때 불황에도 견딜 '다윈주의적 생존력'이 있는지 확인 요망.")
                    st.write("- **심리학 (오판 점검):** 투자 결정 전 '희망 회로'나 '확증 편향'에 빠진 것은 아닌지 스스로 점검하십시오.")
                    st.write("- **이해관계자/파급력:** 노동자, 공급업체와의 상생 구조가 원활한가? AI 등 기술 변화가 이 기업에 득인가 독인가?")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                st.markdown("---")
                st.subheader("🛑 4. 매도 3원칙 (오직 다음 경우에만 매도)")
                st.markdown("<div class='guru-quote'>1. 기업 분석에 치명적인 실수가 있었음을 깨달았을 때.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'>2. 밸류에이션(PBR/PER)이 비상식적으로 지나치게 과열되었을 때.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'>3. 더 확실하고 안전한 기회(기회비용 고려)를 발견했을 때.</div>", unsafe_allow_html=True)

            else:
                st.error("데이터를 불러올 수 없습니다. 팩트 체크가 필수로 필요합니다.")
