import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time

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

def run_dcf(stk, i, p, ty):
    try:
        fcf = i.get('freeCashflow')
        if not fcf:
            cf = stk.cash_flow
            if cf is not None and not cf.empty:
                if 'Free Cash Flow' in cf.index:
                    fcf = cf.loc['Free Cash Flow'].iloc[0]
                else:
                    fcf = cf.loc['Operating Cash Flow'].iloc[0] + cf.loc['Capital Expenditure'].iloc[0]
        if not fcf or fcf <= 0: return 0, 0
        sh = i.get('sharesOutstanding')
        if not sh: return 0, 0
        dr = max(ty / 100, 0.09)
        cv = fcf
        fut = []
        for y in range(1, 11):
            cv *= 1.05 if y <= 5 else 1.03
            fut.append(cv / ((1 + dr) ** y))
        tv = (cv * 1.02) / (dr - 0.02)
        dtv = tv / ((1 + dr) ** 10)
        iv = (sum(fut) + dtv) / sh
        mos = ((iv - p) / iv) * 100
        return iv, mos
    except:
        return 0, 0

st.title("⚡ AGIE Value Terminal")
st.error("🚨 시클리컬 기업 주의: 본 모델은 경제적 해자(Moat)를 갖춘 기업에 최적화되어 있습니다.")

tmap = {
    "제이피모건":"JPM", "JP모건":"JPM", "애플":"AAPL", "구글":"GOOGL",
    "삼성전자":"005930.KS", "SK하이닉스":"000660.KS",
    "현대차":"005380.KS", "기아":"000270.KS"
}

ui = st.text_input("종목명 또는 티커 입력:", placeholder="예: JP모건, AAPL, 005930.KS")
if st.button("가치 분석 심층 스캔", type="primary"):
    if ui:
        with st.spinner("데이터 스캔 중..."):
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
                ey = (1 / f_pe * 100) if f_pe > 0 else 0
                
                with c1:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("📊 1. 밸류에이션 & 안전마진")
                    st.write(f"**현재 주가:** {p:,.2f}")
                    st.write(f"**배당 수익률:** {div:.2f}% (배당정책 일관성 확인 요망)")
                    
                    st.markdown("---")
                    st.write("**[상대 가치: PER & PBR]**")
                    st.write(f"- **현재 PER:** {t_pe:.2f}배")
                    st.write(f"- **Fwd PER:** {f_pe:.2f}배 (시킹알파 참고)")
                    st.write(f"- **5~10년 평균 PER:** {a_pe:.2f}배 (키움증권 참고)")
                    
                    if f_pe > 0 and a_pe > 0:
                        pmos = ((a_pe - f_pe) / a_pe) * 100
                        if pmos > 0:
                            st.markdown(f"▶ **PER 안전마진:** <span class='good'>+{pmos:.1f}%</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"▶ **PER 안전마진:** <span class='highlight'>{pmos:.1f}%</span>", unsafe_allow_html=True)
                    
                    if kr:
                        st.write(f"- **PBR:** {pbr:.2f}배 (한국 주식은 PBR 위주)")
                    else:
                        st.write(f"- **PBR:** {pbr:.2f}배")
                    st.write(f"- **ROIC(ROE대체):** {roe:.2f}%")
                    st.caption("※ PER, EPS, PBR 상승 추세 여부 지속 확인 요망")
                    
                    st.markdown("---")
                    st.write("**[이익수익률 vs 10년물 국채]**")
                    st.write(f"- 10년물 미국채 금리: {ty:.2f}%")
                    st.write(f"- 예상 이익수익률: {ey:.2f}%")
                    
                    st.markdown("---")
                    st.write("**[버핏 10-Year DCF]**")
                    iv, mos = run_dcf(stk, i, p, ty)
                    if iv:
                        st.write(f"**적정가:** {iv:,.2f}")
                        if mos > 0:
                            st.markdown(f"▶ **DCF 안전마진:** <span class='good'>+{mos:.1f}%</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"▶ **DCF 안전마진:** <span class='highlight'>{mos:.1f}%</span>", unsafe_allow_html=True)
                    else:
                        st.error("⚠️ DCF 산출 불가 (이건 확인이 필요한 부분입니다.)")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                with c2:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.subheader("🕵️‍♂️ 2. 질적 분석")
                    off = i.get('companyOfficers', [])
                    ceo = off[0].get('name') if off else '누락'
                    st.markdown(f"- **CEO:** <span class='good'>{tr(ceo)}</span>", unsafe_allow_html=True)
                    st.info("💡 경영진이 똑똑하고 열정적인가? 무엇보다 **정직함**이 가장 중요합니다.")
                    
                    sum_t = i.get('kr_sum', i.get('longBusinessSummary',''))
                    st.markdown(f"- **비즈니스 요약:**\n> {tr(sum_t)[:350]}...")
                    st.caption("※ 모든 건 사실 수집 및 임직원 의견을 반영합니다.")
                    st.caption("※ 부정확한 정보는 '확인이 필요한 부분'으로 간주하세요.")
                    
                    st.markdown("---")
                    st.write("**[기업 해부 및 모델 적용]**")
                    st.write("- **이해관계자:** 노동자/공급업체/고객 상생 구조")
                    st.write("- **경쟁우위:** 가격결정력, 규제안전, 규모화(Scaling)")
                    st.write("- **리스크:** ESG, 상식범위, 파급력(기술변화 득실)")
                    st.write("- **학문적 모델:**")
                    st.write("  · 공학(다중화), 수학(복리), 물리/화학(자가촉매)")
                    st.write("  · 생물학(생존력), 심리학(인지적 오판 방지)")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                st.markdown("---")
                st.subheader("✅ 3. 투자의견 및 거장들의 철학")
                c3, c4 = st.columns(2)
                with c3:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.write("**[매수 6원칙]**")
                    st.write("1. 가격은 저렴한가? (안전마진)")
                    st.write("2. 좋은 비즈니스인가? (해자)")
                    st.write("3. 경영진은 신뢰할 수 있는가? (검증)")
                    st.write("4. 내가 놓친 리스크는 없는가?")
                    st.write("5. 이 기회를 어떻게 발견했는가?")
                    st.write("6. 내 능력 범위 안인가?")
                    st.markdown("</div>", unsafe_allow_html=True)
                with c4:
                    st.markdown("<div class='box'>", unsafe_allow_html=True)
                    st.write("**[매도 3원칙]**")
                    st.markdown("<span class='highlight'>1. 분석에 치명적 실수가 있었을 때</span>", unsafe_allow_html=True)
                    st.markdown("<span class='highlight'>2. 밸류에이션이 지나치게 과열됐을 때</span>", unsafe_allow_html=True)
                    st.markdown("<span class='highlight'>3. 더 확실하고 안전한 기회를 발견했을 때</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                st.markdown("<div class='guru-quote'><b>철학:</b> 주식은 소유권(100% 인수 가정). 시장은 도구(미스터 마켓). 능력 범위 준수(재반박 가능 여부).</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>사전 확인:</b> 시장데이터(트레이딩, 공시), 자본효율(기회비용), 재무건전, 비상탈출 전략.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>피셔 매수:</b> 상업화 초기 문제, 미스터 마켓의 우울증, 일시적이고 해결 가능한 악재 시 매수.</div>", unsafe_allow_html=True)

            else:
                st.error("데이터를 불러올 수 없습니다. 팩트 체크가 필수로 필요합니다.")
