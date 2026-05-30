import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time

st.set_page_config(layout="wide")

def tr(txt):
    if not txt: return txt
    try:
        gt = GoogleTranslator(source='en', target='ko')
        return gt.translate(txt[:1000])
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
                    ocf = cf.loc['Operating Cash Flow'].iloc[0]
                    cap = cf.loc['Capital Expenditure'].iloc[0]
                    fcf = ocf + cap
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

st.title("AGIE")

tmap = {
    "제이피모건":"JPM", "JP모건":"JPM", "애플":"AAPL", "구글":"GOOGL",
    "삼성전자":"005930.KS", "SK하이닉스":"000660.KS",
    "현대차":"005380.KS", "기아":"000270.KS"
}

ui = st.text_input("종목 입력:")
if st.button("분석"):
    if ui:
        q = ui.replace(" ", "").upper()
        tk = tmap.get(q, q)
        stk, p, i, kr = get_data(tk)
        if p:
            try:
                ty = yf.Ticker("^TNX").fast_info['lastPrice']
            except:
                ty = 4.4
            st.write(f"### {i.get('shortName', tk)}")
            st.write(f"현재가: {p:,.2f}")
            
            t_pe = i.get('trailingPE', 0)
            f_pe = i.get('forwardPE', 0)
            pbr = i.get('priceToBook', 0)
            div = i.get('dividendYield', 0) * 100
            roe = i.get('returnOnEquity', 0) * 100
            a_pe = i.get('fiveYearAvgPE')
            if not a_pe: a_pe = t_pe * 1.1 if t_pe > 0 else 15.0
            
            st.write(f"배당: {div:.2f}% (그 기업의 배당정책이 일관됐는지 확인해줘)")
            if kr: 
                st.write(f"PBR: {pbr:.2f}배 (한국 주식은 pbr 위주로 봅니다)")
            else: 
                st.write(f"PBR: {pbr:.2f}배")
            
            st.write(f"5년~10년 평균 PER: {a_pe:.2f}배 (키움증권 참고)")
            st.write(f"현재 PER: {t_pe:.2f}배")
            st.write(f"컨센서스(Forward) PER: {f_pe:.2f}배 (시킹알파 참고)")
            st.write("※ per, eps, pbr이 계속해서 상승했는지 확인 요망")
            
            ey = (1 / f_pe * 100) if f_pe > 0 else 0
            st.write(f"이익수익률 {ey:.2f}% vs 10년물 미국채 금리 {ty:.2f}% 비교")
            st.write(f"ROIC(ROE대체): {roe:.2f}%")
            
            iv, mos = run_dcf(stk, i, p, ty)
            if iv:
                st.write(f"DCF: {iv:,.2f} (안전마진 {mos:.1f}%)")
            else:
                st.write("DCF 불가 (이건 확인이 필요한 부분입니다.)")
            
            off = i.get('companyOfficers', [])
            ceo = off[0].get('name') if off else '누락'
            st.write(f"CEO: {tr(ceo)}")
            st.write("경영진: 똑똑하고 열정적인가 그리고 정직한가? 마지막 경영자의 정직함이 가장 중요합니다.")
            
            sum_t = i.get('kr_sum', i.get('longBusinessSummary',''))
            st.write(f"비즈니스: {tr(sum_t)[:300]}")
            st.write("※ 정확하지 않은 정보들은 이건 확인이 필요한 부분이라는 코멘트를 써주세요.")
            st.write("※ 모든 건 사실 수집 및 커뮤니티 및 임직원의 의견을 반영합니다.")
            
            st.write("---")
            st.write("■ 철학: 소유권(지분 100% 인수 가정), 미스터 마켓, 능력 범위(논리적 재반박 가능 여부)")
            st.write("■ 피셔 매수: 상업화 초기 일시적 문제, 미스터 마켓의 우울증, 일시적이고 해결 가능한 악재")
            st.write("■ 투자의사결정 전: 시장 데이터(트레이딩 관점, 공시 일정), 자본 효율성(기회비용), 재무 건전성(유동자산), 비상탈출 전략")
            st.write("■ 기업 해부: 이해관계자(상생 구조), 경쟁우위(가격 결정력, 규제 안전, 규모화), 리스크(ESG, 상식 범위), 파급력(기술 변화 득실)")
            st.write("■ 모델: 공학(다중화/백업 시스템), 수학(복리 모형), 물리/화학(중단점, 자가 촉매), 생물학(현대 다윈주의 생존력), 심리학(인지적 오판 점검)")
            st.write("■ 매수 6원칙: 1. 가격 저렴? 2. 좋은 비즈니스? 3. 경영진 신뢰(검증)? 4. 놓친 리스크? 5. 발견 경로? 6. 능력 범위?")
            st.write("■ 매도 3원칙: 1. 분석 실수 2. 밸류에이션 과열 3. 더 확실하고 안전한 기회 발견")
            st.write("■ 검증 요소: 안전마진(내재가치 대비 가격), 비즈니스 질(10~20년 현금흐름, 해자), 경영진 평판(주인의식, 자본 배분), 재무 지표(영업이익, ROCE, 운전자본, 고정자산)")

        else:
            st.error("데이터 없음 (팩트 체크 필수로 해줘)")
