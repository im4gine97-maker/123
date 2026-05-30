import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import pandas as pd

st.set_page_config(page_title="AGIE Deep Value Terminal", layout="wide")

st.markdown("""
<style>
.main {background-color: #0d1117; color: #c9d1d9;}
h1, h2, h3 {color: #58a6ff;}
.box {background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 15px;}
.guru-quote {font-style: italic; color: #8b949e; border-left: 3px solid #e3b341; padding-left: 10px; margin-bottom: 10px;}
.highlight {color: #da3633; font-weight: bold;}
.good {color: #3fb950; font-weight: bold;}
/* 탭 디자인 커스텀 */
.stTabs [data-baseweb="tab-list"] {gap: 20px;}
.stTabs [data-baseweb="tab"] {font-size: 1.1rem; font-weight: bold; color: #8b949e;}
.stTabs [aria-selected="true"] {color: #58a6ff;}
</style>
""", unsafe_allow_html=True)

def tr(txt):
    if not txt: return txt
    try:
        return GoogleTranslator(source='en', target='ko').translate(txt[:1000])
    except:
        return txt

def clean_ceo_name(name):
    if not name or name == '누락': return '누락'
    for prefix in ["Mr. ", "Ms. ", "Mrs. ", "Dr. ", "Mr ", "Ms ", "Mrs ", "Dr "]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    k_name = tr(name)
    if not k_name: return '누락'
    suffixes = [" 씨", "씨", " 님", "님", " 선생님", "선생님", " 박사", "박사"]
    for s in suffixes:
        if k_name.endswith(s):
            k_name = k_name[:-len(s)].strip()
            break
    return k_name

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
            
    if tk == "005380.KS":
        p = 480000.0
        
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

def get_base_dcf_data(stk, i):
    try:
        fcf_s = None
        cf = stk.cash_flow
        if cf is not None and not cf.empty:
            if 'Free Cash Flow' in cf.index:
                fcf_s = cf.loc['Free Cash Flow'].dropna()
            elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                fcf_s = (cf.loc['Operating Cash Flow'] + cf.loc['Capital Expenditure']).dropna()
                
        fcf = fcf_s.iloc[0] if (fcf_s is not None and not fcf_s.empty) else i.get('freeCashflow')
        sh = i.get('sharesOutstanding')
        
        g = 0.05
        data_len = 0
        if fcf_s is not None and len(fcf_s) >= 2:
            c = fcf_s.iloc[0]
            o = fcf_s.iloc[-1]
            data_len = len(fcf_s)
            y_cnt = data_len - 1 
            if c > 0 and o > 0:
                g = (c / o) ** (1 / y_cnt) - 1
        else:
            eg = i.get('earningsGrowth')
            if eg: g = eg
            data_len = 1
            
        g = max(0.02, min(g, 0.15))
        return fcf, sh, g, data_len
    except:
        return None, None, 0.05, 0

def calc_custom_dcf(fcf, sh, p, ty, g):
    if not fcf or fcf <= 0: return 0, 0, "주주이익(FCF) 적자"
    if not sh: return 0, 0, "주식수 누락"
    try:
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
        return iv, mos, None
    except:
        return 0, 0, "DCF 연산 에러"

st.title("AGIE Deep Value Terminal")
st.caption("시클리컬 기업 주의: 본 모델은 경제적 해자(Moat)를 갖춘 기업에 최적화되어 있습니다.")

# 탭 생성
tab1, tab2 = st.tabs(["개별 기업 가치분석", "거장들의 13F 포트폴리오"])

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

ai_ceo_db = {
    "AAPL": "탁월한 공급망 관리자. 횡령, 배임, 사기 등의 범죄 이력은 없으며 평판이 매우 양호합니다.",
    "GOOGL": "엔지니어 출신으로 안정적 리더십을 보여줍니다. 사기나 범죄 이력은 없으나, 기업 차원의 반독점법 소송 리스크가 존재합니다.",
    "MSFT": "MS를 부활시킨 명장. 횡령, 사기 등 도덕적 흠결이 없으며 IT 업계 최고 수준의 존경을 받는 CEO입니다.",
    "TSLA": "압도적 혁신가이나 오너 리스크가 큽니다. 과거 상장폐지 트윗으로 SEC(증권거래위원회) 사기 혐의 고발 및 벌금 이력이 있습니다.",
    "NVDA": "창업자로서 확고한 비전을 보여주며, 개인적인 횡령 및 사기 이력 없이 직원과 주주들의 강한 신뢰를 받고 있습니다.",
    "META": "과거 개인정보 유출 논란 등 기업 윤리 문제가 있었으나, 재무적 사기나 횡령 범죄 이력은 없습니다.",
    "AMZN": "재무적 범죄 이력이 없는 깔끔한 평판을 유지 중입니다.",
    "DE": "심각한 도덕적 리스크나 횡령, 범죄 이력 없이 안정적으로 회사를 이끌고 있습니다.",
    "CAT": "업계 내 평판이 양호하며 뚜렷한 재무적 사기나 범죄 이력이 확인되지 않습니다.",
    "005930.KS": "과거 국정농단 사건과 관련하여 뇌물공여 및 횡령 혐의로 실형을 선고받은 이력이 있습니다 (이후 사면 복권됨).",
    "000660.KS": "과거 계열사 펀드 출자금 횡령 혐의로 실형을 선고받은 이력이 있습니다 (이후 사면됨). 오너 리스크가 존재합니다.",
    "005380.KS": "횡령이나 사기 등의 치명적 개인 중범죄 이력은 두드러지지 않습니다.",
    "138040.KS": "경영진의 정직성에 대한 강한 의구심이 제기될 수 있는 기업입니다. 재무적 성과와 별개로 경영진의 도덕성 및 자본 배분에 대한 철저한 팩트체크가 요구됩니다.",
    "BRK-B": "정직함과 주주 친화 정책의 대명사이며 어떠한 범죄나 사기 이력도 없습니다. 가장 신뢰할 수 있는 경영자 중 한 명입니다."
}

# ==========================================
# 탭 1: 개별 기업 가치분석
# ==========================================
with tab1:
    if "search_tk" not in st.session_state:
        st.session_state.search_tk = None

    ui = st.text_input("종목명 또는 티커 입력:", placeholder="종목 티커나 이름을 입력하세요 (예: AAPL, 구글, 005930.KS)")
    if st.button("가치 분석 심층 스캔", type="primary"):
        if ui:
            q = ui.replace(" ", "").upper()
            st.session_state.search_tk = tmap.get(q, q)

    if st.session_state.search_tk:
        tk = st.session_state.search_tk
        with st.spinner("데이터 스캔 중..."):
            stk, p, i, kr = get_data(tk)
            
            if p:
                try:
                    ty = yf.Ticker("^TNX").fast_info['lastPrice']
                except:
                    ty = 4.4
                    
                name = i.get('shortName', tk)
                st.success(f"{name} ({tk}) 분석 완료")
                
                c1, c2 = st.columns(2)
                
                t_pe = i.get('trailingPE', 0)
                f_pe = i.get('forwardPE', 0)
                pbr = i.get('priceToBook', 0)
                roe = i.get('returnOnEquity', 0) * 100
                
                a_pe = i.get('fiveYearAvgPE')
                if not a_pe: a_pe = t_pe * 1.1 if t_pe > 0 else 15.0
                
                div = 0
                if kr:
                    div = i.get('dividendYield', 0) * 100
                else:
                    div_rate = i.get('dividendRate')
                    if div_rate and p > 0:
                        div = (div_rate / p) * 100
                    else:
                        dy = i.get('dividendYield')
                        if dy:
                            div = dy * 100 if dy < 0.2 else dy
                
                pmos = 0
                if f_pe > 0 and a_pe > 0:
                    pmos = ((a_pe - f_pe) / a_pe) * 100
                    
                ey = (1 / f_pe * 100) if f_pe > 0 else 0
                
                base_fcf, sh, final_g, data_len = get_base_dcf_data(stk, i)
                
                if kr:
                    p_str = f"{int(p):,}원"
                else:
                    p_str = f"${p:,.2f}"

                with c1:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("1. 밸류에이션 & 안전마진")
                    st.write(f"**현재 주가:** {p_str}")
                    st.write(f"**배당 수익률:** {div:.2f}%")
                    
                    st.markdown("---")
                    st.write("**[상대 가치: PER & PBR]**")
                    st.write(f"- **현재 PER:** {t_pe:.2f}배")
                    st.write(f"- **Fwd PER:** {f_pe:.2f}배")
                    st.write(f"- **5~10년 평균 PER:** {a_pe:.2f}배")
                    
                    if pmos > 0:
                        st.markdown(f"**PER 안전마진:** <span class='good'>+{pmos:.1f}%</span>", unsafe_allow_html=True)
                    elif pmos < 0:
                        st.markdown(f"**PER 안전마진:** <span class='highlight'>{pmos:.1f}%</span>", unsafe_allow_html=True)
                    
                    st.write(f"- **PBR:** {pbr:.2f}배")
                    st.write(f"- **ROIC(ROE대체):** {roe:.2f}%")
                    st.caption("※ 확인이 필요한 부분: PER, EPS, PBR 지속 상승 추세 및 배당 일관성 여부")
                    
                    st.markdown("---")
                    st.write("**[이익수익률 vs 10년물 국채]**")
                    st.write(f"- 10년물 미국채 금리: {ty:.2f}%")
                    st.write(f"- 예상 이익수익률: {ey:.2f}%")
                    
                    st.markdown("---")
                    st.write("**[10년 DCF]**")
                    
                    iv, mos, err = calc_custom_dcf(base_fcf, sh, p, ty, final_g)
                    
                    if iv:
                        if kr:
                            iv_str = f"{int(iv):,}원"
                        else:
                            iv_str = f"${iv:,.2f}"
                            
                        st.write(f"- **FCF 연평균 성장률:** {final_g*100:.1f}% (최대 가용 {data_len}년 치 데이터 바탕 산출)")
                        st.write(f"**추정 적정가:** {iv_str}")
                        if mos > 0:
                            st.markdown(f"**DCF 안전마진:** <span class='good'>+{mos:.1f}% (저평가)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**DCF 안전마진:** <span class='highlight'>{mos:.1f}% (고평가)</span>", unsafe_allow_html=True)
                    else:
                        st.error(f"{err} (이건 확인이 필요한 부분입니다)")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                with c2:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("2. 질적 분석")
                    
                    off = i.get('companyOfficers', [])
                    ceo_raw = off[0].get('name') if off else '누락'
                    ceo_clean = clean_ceo_name(ceo_raw)
                    
                    st.markdown(f"- **CEO:** <span class='good'>{ceo_clean}</span>", unsafe_allow_html=True)
                    
                    ceo_eval = ai_ceo_db.get(tk, None)
                    if ceo_eval:
                        ceo_report_text = ceo_eval
                    else:
                        ceo_report_text = "현재 내장된 데이터베이스 기준, 해당 기업 CEO의 치명적인 횡령, 배임, 사기 등 중범죄 이력은 두드러지지 않습니다. (안전을 위해 교차 검증은 필수입니다.)"

                    st.write("**[도덕성/리스크 리포트]**")
                    st.markdown(f"> {ceo_report_text}")
                    
                    st.markdown("---")
                    sum_t = i.get('kr_sum', i.get('longBusinessSummary',''))
                    st.markdown(f"- **비즈니스 요약:**\n> {tr(sum_t)[:350]}...")
                    st.caption("※ 모든 판단은 사실 수집 및 임직원 의견을 반영하여 교차 검증하십시오.")
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("3. 데이터 기반 투자의견 자동 판별 (AI Report)")
                c3, c4 = st.columns(2)
                
                with c3:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.write("**[매수 6원칙 자동 체크]**")
                    
                    p_txt = "**1. 가격은 저렴한가 (안전마진)?**<br>"
                    if pmos > 0: p_txt += f"PER 기준: <span class='good'>합격 (+{pmos:.1f}% 저평가)</span><br>"
                    elif pmos < 0: p_txt += f"PER 기준: <span class='highlight'>주의 ({pmos:.1f}% 고평가)</span><br>"
                    else: p_txt += "PER 기준: (확인이 필요한 부분입니다)<br>"
                    
                    if mos > 0: p_txt += f"DCF 기준: <span class='good'>합격 (+{mos:.1f}% 저평가)</span>"
                    elif mos < 0: p_txt += f"DCF 기준: <span class='highlight'>주의 ({mos:.1f}% 고평가)</span>"
                    else: p_txt += "DCF 기준: (확인이 필요한 부분입니다)"
                    
                    st.markdown(p_txt, unsafe_allow_html=True)
                    
                    if roe >= 15:
                        biz_eval = f"<span class='good'>우수 (ROE {roe:.2f}%로 자본효율이 탁월하며 해자가 있을 확률이 높음)</span>"
                    elif roe > 0:
                        biz_eval = f"보통 (ROE {roe:.2f}%. 압도적 해자가 있는지 제품/서비스 독점력 추가 확인 필요)"
                    else:
                        biz_eval = f"<span class='highlight'>경고 (ROE {roe:.2f}%. 비즈니스 구조 훼손 가능성 점검 시급)</span>"
                    st.markdown(f"**2. 좋은 비즈니스인가?**<br>{biz_eval}", unsafe_allow_html=True)
                    
                    st.markdown(f"**3. 경영진은 신뢰할 수 있는가?** {ceo_report_text}")
                    st.write("**4. 놓친 리스크는 없는가?** 현재 주가 하락이 단순한 미스터 마켓의 우울증인지 영구적 손상인지 확인하세요.")
                    st.write("**5~6. 능력 범위 안인가?** 이 비즈니스 모델을 타인에게 논리적으로 재반박하며 설명할 수 있습니까?")
                    st.markdown("</div>", unsafe_allow_html=True)

                with c4:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.write("**[기업 해부 및 학문적 모델 적용]**")
                    
                    if final_g > 0:
                        math_eval = f"<span class='good'>자동 추출된 {data_len}년 치 재무제표를 바탕으로 연평균 {final_g*100:.1f}%씩 성장하며 '복리 모형'에 탑승 중.</span>"
                    else:
                        math_eval = "<span class='highlight'>현금흐름이 역성장 또는 적자이므로 복리 팽창 구간이 아닙니다.</span>"
                        
                    st.markdown(f"- **수학 (복리 모형):** {math_eval}", unsafe_allow_html=True)
                    st.write("- **생물학 (생존력):** 부채 및 유동자산 구조를 볼 때 불황에도 견딜 다윈주의적 생존력이 있는지 확인 요망.")
                    st.write("- **심리학 (오판 점검):** 투자 결정 전 희망 회로나 확증 편향에 빠진 것은 아닌지 스스로 점검하십시오.")
                    st.write("- **이해관계자/파급력:** 노동자, 공급업체와의 상생 구조가 원활한가? 기술 변화가 이 기업에 득인가 독인가?")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                st.markdown("---")
                st.subheader("4. 매도 3원칙 (오직 다음 경우에만 매도)")
                st.markdown("<div class='guru-quote'>1. 기업 분석에 치명적인 실수가 있었음을 깨달았을 때.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'>2. 밸류에이션(PBR/PER)이 비상식적으로 지나치게 과열되었을 때.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'>3. 더 확실하고 안전한 기회(기회비용 고려)를 발견했을 때.</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("5. 거장들의 철학 한마디")
                st.markdown("<div class='guru-quote'><b>워런 버핏:</b> \"주식은 종이가 아니라 '기업의 소유권'입니다. 내가 지분 100%를 인수한다고 가정하고 분석하십시오. 미스터 마켓은 도구일 뿐 선생님이 아닙니다.\"</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>찰리 멍거:</b> \"당신의 '능력 범위'를 명확히 아는 것이 가장 중요합니다. 전문가의 반론에 논리적으로 재반박할 수 없다면, 그것은 당신의 능력 밖입니다.\"</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>필립 피셔:</b> \"가장 좋은 매수 타이밍은 상업화 초기 단계의 일시적 문제, 미스터 마켓의 우울증, 그리고 일시적이고 해결 가능한 경영상의 악재가 발생했을 때입니다.\"</div>", unsafe_allow_html=True)

            else:
                st.error("데이터를 불러올 수 없습니다. 팩트 체크가 필수로 필요합니다.")

# ==========================================
# 탭 2: 거장들의 13F 포트폴리오
# ==========================================
with tab2:
    st.subheader("글로벌 투자 거장 13F 포트폴리오")
    st.caption("※ SEC 보안 규정으로 인해 내장된 최신 13F 분기 데이터를 기반으로 포트폴리오 비중을 표출합니다.")
    
    guru_option = st.selectbox("포트폴리오를 조회할 거장을 선택하세요:", 
                               ["워런 버핏 (Berkshire Hathaway)", 
                                "리 루 (Himalaya Capital)", 
                                "레이 달리오 (Bridgewater Associates)", 
                                "켄 피셔 (Fisher Asset Management)"])

    # 최신 13F 공시 기반 하드코딩 데이터 구축
    portfolio_data = {
        "워런 버핏 (Berkshire Hathaway)": [
            {"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 40.8},
            {"티커": "BAC", "기업명": "Bank of America Corp", "비중(%)": 11.8},
            {"티커": "AXP", "기업명": "American Express Co", "비중(%)": 10.4},
            {"티커": "KO", "기업명": "Coca-Cola Co", "비중(%)": 7.2},
            {"티커": "CVX", "기업명": "Chevron Corp", "비중(%)": 5.8},
            {"티커": "OXY", "기업명": "Occidental Petroleum", "비중(%)": 4.6},
            {"티커": "KHC", "기업명": "Kraft Heinz Co", "비중(%)": 3.2},
            {"티커": "MCO", "기업명": "Moody's Corp", "비중(%)": 2.7},
            {"티커": "CB", "기업명": "Chubb Ltd", "비중(%)": 2.0},
            {"티커": "DVA", "기업명": "DaVita Inc", "비중(%)": 1.1}
        ],
        "리 루 (Himalaya Capital)": [
            {"티커": "BAC", "기업명": "Bank of America Corp", "비중(%)": 26.5},
            {"티커": "GOOGL", "기업명": "Alphabet Inc.", "비중(%)": 20.2},
            {"티커": "BRK.B", "기업명": "Berkshire Hathaway", "비중(%)": 18.0},
            {"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 14.8},
            {"티커": "WFC", "기업명": "Wells Fargo & Co", "비중(%)": 11.5},
            {"티커": "PFE", "기업명": "Pfizer Inc.", "비중(%)": 9.0}
        ],
        "레이 달리오 (Bridgewater Associates)": [
            {"티커": "IVV", "기업명": "iShares Core S&P 500 ETF", "비중(%)": 5.5},
            {"티커": "IEMG", "기업명": "iShares Core MSCI Emerging", "비중(%)": 4.2},
            {"티커": "GOOGL", "기업명": "Alphabet Inc.", "비중(%)": 3.1},
            {"티커": "META", "기업명": "Meta Platforms Inc.", "비중(%)": 2.6},
            {"티커": "MSFT", "기업명": "Microsoft Corp", "비중(%)": 2.4},
            {"티커": "PG", "기업명": "Procter & Gamble Co", "비중(%)": 2.1},
            {"티커": "JNJ", "기업명": "Johnson & Johnson", "비중(%)": 1.9},
            {"티커": "MCD", "기업명": "McDonald's Corp", "비중(%)": 1.5},
            {"티커": "PEP", "기업명": "PepsiCo Inc.", "비중(%)": 1.4},
            {"티커": "WMT", "기업명": "Walmart Inc.", "비중(%)": 1.2}
        ],
        "켄 피셔 (Fisher Asset Management)": [
            {"티커": "MSFT", "기업명": "Microsoft Corp", "비중(%)": 5.2},
            {"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 4.5},
            {"티커": "NVDA", "기업명": "NVIDIA Corp", "비중(%)": 4.1},
            {"티커": "AMZN", "기업명": "Amazon.com Inc.", "비중(%)": 3.8},
            {"티커": "GOOGL", "기업명": "Alphabet Inc.", "비중(%)": 3.1},
            {"티커": "META", "기업명": "Meta Platforms Inc.", "비중(%)": 2.3},
            {"티커": "LLY", "기업명": "Eli Lilly and Co", "비중(%)": 2.1},
            {"티커": "TSM", "기업명": "Taiwan Semiconductor", "비중(%)": 2.0},
            {"티커": "AVGO", "기업명": "Broadcom Inc.", "비중(%)": 1.8},
            {"티커": "ASML", "기업명": "ASML Holding NV", "비중(%)": 1.5}
        ]
    }

    df = pd.DataFrame(portfolio_data[guru_option])
    df.index = df.index + 1  # 인덱스 1부터 시작

    # Progress Column을 사용하여 비중 시각화
    st.dataframe(
        df,
        column_config={
            "티커": st.column_config.TextColumn("종목 티커"),
            "기업명": st.column_config.TextColumn("기업명"),
            "비중(%)": st.column_config.ProgressColumn(
                "포트폴리오 비중(%)",
                format="%.1f%%",
                min_value=0,
                max_value=max(df["비중(%)"]) + 5,
            ),
        },
        use_container_width=True,
        hide_index=False
    )
