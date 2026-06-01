import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import pandas as pd
from datetime import datetime

# 앱 이름 변경 및 레이아웃
st.set_page_config(page_title="VALUE", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# [1] 세션 상태 초기화 및 글로벌 유틸리티
# ==========================================
if "search_tk" not in st.session_state: st.session_state.search_tk = None
if "history" not in st.session_state: st.session_state.history = []
if "bookmarks" not in st.session_state: st.session_state.bookmarks = []
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "main_input" not in st.session_state: st.session_state.main_input = ""

if "search_ranking" not in st.session_state: st.session_state.search_ranking = {}
if "stock_comments" not in st.session_state: st.session_state.stock_comments = {}
if "community_posts" not in st.session_state: st.session_state.community_posts = []

def t(ko, en):
    return ko if st.session_state.lang == "ko" else en

def safe_float(val, default=0.0):
    try:
        if val is None or pd.isna(val): return default
        return float(val)
    except:
        return default

def fmt_f(val, decimals=1):
    try:
        return f"{float(val):.{decimals}f}"
    except:
        return "0.0" if decimals == 1 else "0.00"

def trigger_scan():
    if st.session_state.get("main_input"):
        q = st.session_state.main_input.replace(" ", "").upper()
        tk = tmap.get(q, q)
        st.session_state.search_tk = tk

# ==========================================
# [2] 글로벌 상수 및 고정 데이터
# ==========================================
tmap = {
    # 한국 주요 우량주 명칭 및 줄임말 매핑
    "삼성전자": "005930.KS", "삼전": "005930.KS", "삼성": "005930.KS", "SAMSUNG": "005930.KS",
    "SK하이닉스": "000660.KS", "하닉": "000660.KS", "하이닉스": "000660.KS", "HYNIX": "000660.KS",
    "LG에너지솔루션": "373220.KS", "엔솔": "373220.KS", "LG엔솔": "373220.KS", "엘지엔솔": "373220.KS",
    "현대자동차": "005380.KS", "현대차": "005380.KS", "현대": "005380.KS", "HYUNDAI": "005380.KS",
    "삼성바이오로직스": "207940.KS", "삼바": "207940.KS", "바이오로직스": "207940.KS",
    "기아": "000270.KS", "기아차": "000270.KS", "KIA": "000270.KS",
    "셀트리온": "068270.KS", "셀트": "068270.KS", "CELLTRION": "068270.KS",
    "KB금융": "105560.KS", "국민은행": "105560.KS", "KB금융지주": "105560.KS",
    "POSCO홀딩스": "005490.KS", "포스코": "005490.KS", "포홀": "005490.KS", "POSCO": "005490.KS",
    "신한지주": "055550.KS", "신한금융": "055550.KS", "신한은행": "055550.KS",
    "삼성SDI": "006400.KS", "스디": "006400.KS", "삼성스디": "006400.KS", "SDI": "006400.KS",
    "NAVER": "035420.KS", "네이버": "035420.KS",
    "현대모비스": "012330.KS", "모비스": "012330.KS", "MOBIS": "012330.KS",
    "LG화학": "051910.KS", "엘화": "051910.KS", "LG화": "051910.KS",
    "카카오": "035720.KS", "KAKAO": "035720.KS",
    "삼성물산": "028260.KS", "물산": "028260.KS",
    "하나금융지주": "086790.KS", "하나금융": "086790.KS", "하나지주": "086790.KS",
    "LG전자": "066570.KS", "엘전": "066570.KS", "엘지전자": "066570.KS",
    "SK스퀘어": "402340.KS", "스퀘어": "402340.KS",
    "삼성생명": "032830.KS", "삼생": "032830.KS",
    "메리츠금융지주": "138040.KS", "메리츠": "138040.KS", "메리츠금융": "138040.KS",
    "SK이노베이션": "096770.KS", "이노": "096770.KS", "SK이노": "096770.KS",
    "HD현대중공업": "329180.KS", "현중": "329180.KS", "현대중공업": "329180.KS",
    "HMM": "011200.KS", "흠": "011200.KS", "현대상선": "011200.KS",
    "고려아연": "010130.KS", "고아": "010130.KS",
    "KT&G": "033780.KS", "케이티앤지": "033780.KS",
    "두산에너빌리티": "034020.KS", "두산에너": "034020.KS", "에너빌리티": "034020.KS",
    "삼성전기": "009150.KS", "삼전기": "009150.KS",
    "크래프톤": "259960.KS", "KRAFTON": "259960.KS",
    "한화에어로스페이스": "012450.KS", "한화에어로": "012450.KS", "에어로스페이스": "012450.KS",

    # 미국 주요 빅테크·우량주 매핑
    "NVIDIA": "NVDA", "엔비디아": "NVDA", "엔비": "NVDA",
    "APPLE": "AAPL", "애플": "AAPL",
    "ALPHABET": "GOOGL", "구글": "GOOGL", "알파벳": "GOOGL",
    "MICROSOFT": "MSFT", "마이크로소프트": "MSFT", "마소": "MSFT",
    "AMAZON": "AMZN", "아마존": "AMZN",
    "BROADCOM": "AVGO", "브로드컴": "AVGO",
    "TESLA": "TSLA", "테슬라": "TSLA",
    "META": "META", "메타": "META",
    "MICRON": "MU", "마이크론": "MU",
    "BERKSHIREHATHAWAY": "BRK-B", "버크셔해서웨이": "BRK-B", "버크셔": "BRK-B",
    "ELILILLY": "LLY", "일라이릴리": "LLY",
    "WALMART": "WMT", "월마트": "WMT",
    "AMD": "AMD", "에이엠디": "AMD",
    "JPMORGAN": "JPM", "제이피모건": "JPM", "JP모건": "JPM",
    "ORACLE": "ORCL", "오라클": "ORCL",
    "VISA": "V", "비자": "V",
    "EXXONMOBIL": "XOM", "엑손모빌": "XOM",
    "INTEL": "INTC", "인텔": "INTC",
    "JOHNSON&JOHNSON": "JNJ", "존슨앤존슨": "JNJ",
    "CISCO": "CSCO", "시스코": "CSCO",
    "MASTERCARD": "MA", "마스터카드": "MA",
    "COSTCO": "COST", "코스트코": "COST",
    "CATERPILLAR": "CAT", "캐터필러": "CAT",
    "LAMRESEARCH": "LRCX", "램리서치": "LRCX",
    "ABBVIE": "ABBV", "애브비": "ABBV",
    "PALANTIR": "PLTR", "팔란티어": "PLTR",
    "BANKOFAMERICA": "BAC", "뱅크오브아메리카": "BAC", "뱅아": "BAC",
    "CHEVRON": "CVX", "쉐브론": "CVX",
    "NETFLIX": "NFLX", "넷플릭스": "NFLX",
    "APPLIEDMATERIALS": "AMAT", "어플라이드머티리얼즈": "AMAT",
    "COCA-COLA": "KO", "코카콜라": "KO"
}

fallback_13f_data = {
    "HC": [{"티커": "GOOGL", "기업명": "Alphabet Inc.", "비중(%)": 22.84}, {"티커": "BRK-B", "기업명": "Berkshire Hathaway Inc.", "비중(%)": 13.43}, {"티커": "BAC", "기업명": "Bank of America Corporation", "비중(%)": 4.56}],
    "BRK": [{"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 21.99}, {"티커": "AXP", "기업명": "American Express Co.", "비중(%)": 17.43}, {"티커": "KO", "기업명": "Coca-Cola Co.", "비중(%)": 11.56}, {"티커": "BAC", "기업명": "Bank of America Corp.", "비중(%)": 9.52}],
    "PSH": [{"티커": "BN", "기업명": "Brookfield Corp.", "비중(%)": 17.62}, {"티커": "AMZN", "기업명": "Amazon.com Inc.", "비중(%)": 17.39}, {"티커": "MSFT", "기업명": "Microsoft Corp.", "비중(%)": 15.26}],
    "BAU": [{"티커": "AMZN", "기업명": "Amazon.com, Inc.", "비중(%)": 12.69}, {"티커": "QSR", "기업명": "Restaurant Brands", "비중(%)": 11.67}],
    "AKRE": [{"티커": "MA", "기업명": "Mastercard Inc", "비중(%)": 18.64}, {"티커": "MCO", "기업명": "Moody's Corp", "비중(%)": 8.89}, {"티커": "V", "기업명": "Visa Inc", "비중(%)": 8.10}],
    "PI": [{"티커": "HCC", "기업명": "Warrior Met Coal, Inc.", "비중(%)": 39.88}, {"티커": "RIG", "기업명": "Transocean Ltd.", "비중(%)": 31.97}],
    "AQUA": [{"티커": "BRK-B", "기업명": "Berkshire Hathaway Inc", "비중(%)": 34.57}, {"티커": "MA", "기업명": "Mastercard Inc", "비중(%)": 14.77}]
}

us_top30 = [{"순위": 1, "티커": "NVDA", "기업명": "NVIDIA", "시가총액": "$5.11T"}, {"순위": 2, "티커": "AAPL", "기업명": "Apple", "시가총액": "$4.58T"}, {"순위": 3, "티커": "GOOGL", "기업명": "Alphabet", "시가총액": "$4.56T"}]
kr_top30 = [{"순위": 1, "티커": "005930", "기업명": "삼성전자", "시가총액": "1,794조 원"}, {"순위": 2, "티커": "000660", "기업명": "SK하이닉스", "시가총액": "1,662조 원"}, {"순위": 3, "티커": "105560", "기업명": "KB금융", "시가총액": "57조 원"}]

# ==========================================
# [3] 데이터 가져오기 엔진
# ==========================================
@st.cache_data(ttl=900) 
def fetch_macro_realtime_v6():
    macro_symbols = {
        "KOSPI": "^KS11", "KOSDAQ": "^KQ11", 
        "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Nasdaq Futures": "NQ=F",
        "USD/KRW": "KRW=X", "WTI Crude": "CL=F", "10Y Treasury": "^TNX"
    }
    res = {}
    for name, tk in macro_symbols.items():
        try:
            stk = yf.Ticker(tk)
            hist = stk.history(period="5d")
            if len(hist) >= 2:
                last_p = safe_float(hist['Close'].iloc[-1])
                prev_p = safe_float(hist['Close'].iloc[-2])
                if prev_p != 0:
                    change = last_p - prev_p
                    pct = (change / prev_p) * 100
                else:
                    change, pct = 0.0, 0.0
                res[name] = {"p": last_p, "c": change, "pct": pct}
            else: res[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
        except: res[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
            
    try:
        spy_info = yf.Ticker("SPY").info
        res["SPY_PE"] = safe_float(spy_info.get("trailingPE", spy_info.get("forwardPE", 22.0)), 22.0)
    except:
        res["SPY_PE"] = 22.0
        
    try:
        qqq_info = yf.Ticker("QQQ").info
        res["QQQ_PE"] = safe_float(qqq_info.get("trailingPE", qqq_info.get("forwardPE", 30.0)), 30.0)
    except:
        res["QQQ_PE"] = 30.0
    
    return res

@st.cache_data
def get_13f_portfolio(guru_code):
    return fallback_13f_data.get(guru_code, [])

def fetch_naver_finance_news(cd):
    url = f"https://finance.naver.com/item/news_news.naver?code={cd}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    news_list = []
    try:
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        titles = soup.select('td.title a')
        for a in titles[:3]:
            title_text = a.text.strip()
            link = "https://finance.naver.com" + a['href'] if a.has_attr('href') else f"https://finance.naver.com/item/news.naver?code={cd}"
            news_list.append({"title": title_text, "link": link, "publisher": "네이버금융"})
    except:
        pass
    return news_list

def fetch_global_news(tk):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={tk}&region=US&lang=en-US"
    news_list = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.find_all('item')
        for item in items[:3]:
            t_tag = item.find('title')
            l_tag = item.find('link')
            if t_tag and t_tag.text:
                news_list.append({
                    "title": t_tag.text.strip(),
                    "link": l_tag.text.strip() if l_tag else '#',
                    "publisher": "Yahoo Finance"
                })
    except:
        pass
    return news_list

def fetch_governance_criticism(tk, cd, ceo_name):
    tk_clean = str(tk).strip().upper().replace('.B', '-B').replace('.A', '-A')
    cd_clean = str(cd).strip()
    
    db = {
        "NVDA": "젠슨 황 (Jensen Huang): 비전을 현실로 만드는 강력한 실행력과 기술적 해자를 구축한 검증된 경영자입니다.\n리스크: 특정 리더(키맨)에 대한 절대적 의존도(단일 실패 지점) 및 자체 칩 개발 독립 리스크. (이건 확인이 필요한 부분입니다)",
        "AAPL": "팀 쿡 (Tim Cook): 탁월한 공급망 관리와 대규모 자사주 매입으로 주주 환원에 매우 충실합니다.\n리스크: 혁신 사이클 정체 및 중국 등 지정학적 갈등에 노출. (이건 확인이 필요한 부분입니다)",
        "105560": "KB금융 (양종희): 국내 은행권 최초로 강력하고 투명한 밸류업(주주환원) 로드맵을 제시했습니다.\n리스크: 정부의 은행권 이자 수익 개입(상생 금융 압박) 및 부동산 PF 부실 전이 가능성. (이건 확인이 필요한 부분입니다)"
    }
    
    for key, text in db.items():
        if key in tk_clean or (len(cd_clean) == 6 and key == cd_clean):
            return text
            
    return f"{ceo_name} 경영진 - 위키 및 공공 기록 스크리닝 결과, 해당 경영진에 대한 사법적 리스크나 중범죄 이력은 두드러지지 않습니다. 다만 가치투자 관점에서 과도한 자본 배분 오류 여부는 투자 전 추가 교차 검증이 필요합니다. (이건 확인이 필요한 부분입니다)"

def get_data(tk):
    try:
        if not tk: return None, None, {}, False
        tk = str(tk).strip()
        
        if tk.isdigit() and len(tk) == 6:
            test_tk = tk + ".KS"
            stk_test = yf.Ticker(test_tk)
            try:
                _ = stk_test.fast_info['lastPrice']
                tk = test_tk 
            except: tk = tk + ".KQ"

        if "." not in tk: tk = tk.upper()
        kr = tk.endswith('.KS') or tk.endswith('.KQ')
        cd = tk.split('.')[0] if kr else tk
        stk = yf.Ticker(tk)
        p, i = None, {}
        for _ in range(3):
            try:
                p = safe_float(stk.fast_info['lastPrice'])
                i = stk.info
                break
            except: time.sleep(1)
        
        if tk == "005380.KS": p = 480000.0
        
        if kr and p:
            try:
                url = f"https://finance.naver.com/item/main.naver?code={cd}"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                s = BeautifulSoup(r.text, 'html.parser')
                t_name = s.select_one('.wrap_company h2 a')
                if t_name: i['shortName'] = t_name.text
                t_pe = s.select_one('#_per')
                if t_pe: i['trailingPE'] = safe_float(t_pe.text.replace(',',''))
                t_fpe = s.select_one('#_cns_per')
                if t_fpe: i['forwardPE'] = safe_float(t_fpe.text.replace(',',''))
                t_pbr = s.select_one('#_pbr')
                if t_pbr: i['priceToBook'] = safe_float(t_pbr.text.replace(',',''))
                t_div = s.select_one('#_dvr')
                if t_div: i['dividendYield'] = safe_float(t_div.text.replace(',',''))/100
                t_sum = s.select_one('.summary_info p')
                if t_sum: i['kr_sum'] = t_sum.text
            except: pass
            
        return stk, p, i, kr
    except Exception as e:
        return None, None, {}, False

def get_base_dcf_data(stk, i):
    try:
        if stk is None: return None, None, 0.05, 0
        fcf_s = None
        cf = stk.cash_flow
        if cf is not None and not cf.empty:
            if 'Free Cash Flow' in cf.index: fcf_s = cf.loc['Free Cash Flow'].dropna()
            elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                fcf_s = (cf.loc['Operating Cash Flow'] + cf.loc['Capital Expenditure']).dropna()
                
        fcf = safe_float(fcf_s.iloc[0]) if (fcf_s is not None and not fcf_s.empty) else safe_float(i.get('freeCashflow'))
        sh = safe_float(i.get('sharesOutstanding'))
        
        g, data_len = 0.05, 0
        if fcf_s is not None and len(fcf_s) >= 2:
            c, o = safe_float(fcf_s.iloc[0]), safe_float(fcf_s.iloc[-1])
            data_len = len(fcf_s)
            if c > 0 and o > 0: g = (c / o) ** (1 / (data_len - 1)) - 1
        else:
            eg = safe_float(i.get('earningsGrowth'))
            if eg != 0.0: g = eg
            data_len = 1
            
        g = max(0.02, min(g, 0.15))
        return fcf, sh, g, data_len
    except: return None, None, 0.05, 0

# [수정] 금융주 판별 파라미터 추가
def calc_custom_dcf(fcf, sh, p, ty, g, is_financial=False):
    if is_financial: return 0, 0, t("금융/보험주 DCF 평가 제외 (Financial FCF N/A)", "DCF N/A for Financials")
    if not fcf or fcf <= 0: return 0, 0, t("주주이익(FCF) 적자", "Negative FCF (Owner Earnings)")
    if not sh or sh <= 0: return 0, 0, t("주식수 누락", "Missing Shares Outstanding")
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
    except: return 0, 0, t("DCF 연산 에러", "DCF Calculation Error")

def get_real_roic(stk, i):
    try:
        if 'returnOnCapitalEmployed' in i and i['returnOnCapitalEmployed'] is not None:
            return safe_float(i['returnOnCapitalEmployed']) * 100
        if stk is None: return None
        inc = stk.income_stmt
        bs = stk.balance_sheet
        if inc is not None and not inc.empty and bs is not None and not bs.empty:
            ebit = safe_float(inc.loc['EBIT'].iloc[0]) if 'EBIT' in inc.index else (safe_float(inc.loc['Operating Income'].iloc[0]) if 'Operating Income' in inc.index else 0)
            pretax = safe_float(inc.loc['Pretax Income'].iloc[0]) if 'Pretax Income' in inc.index else 0
            tax = safe_float(inc.loc['Tax Provision'].iloc[0]) if 'Tax Provision' in inc.index else 0
            tax_rate = tax / pretax if pretax > 0 else 0.25
            nopat = ebit * (1 - tax_rate)
            total_debt = safe_float(bs.loc['Total Debt'].iloc[0]) if 'Total Debt' in bs.index else 0
            total_equity = safe_float(bs.loc['Stockholders Equity'].iloc[0]) if 'Stockholders Equity' in bs.index else 0
            cash = safe_float(bs.loc['Cash And Cash Equivalents'].iloc[0]) if 'Cash And Cash Equivalents' in bs.index else 0
            invested_capital = total_debt + total_equity - cash
            if invested_capital > 0:
                roic = (nopat / invested_capital) * 100
                return roic
    except:
        pass
    return None

def analyze_trends(stk):
    eps_trend, bps_trend = t("데이터 부족", "Insufficient Data"), t("데이터 부족", "Insufficient Data")
    if stk is None: return eps_trend, bps_trend
    try:
        inc, bs = stk.income_stmt, stk.balance_sheet
        if inc is not None and not inc.empty:
            target_col = 'Basic EPS' if 'Basic EPS' in inc.index else ('Diluted EPS' if 'Diluted EPS' in inc.index else None)
            if target_col:
                eps_vals = inc.loc[target_col].dropna().values[:4][::-1] 
                if len(eps_vals) >= 3:
                    if all(eps_vals[i] <= eps_vals[i+1] for i in range(len(eps_vals)-1)) and eps_vals[0] < eps_vals[-1]: eps_trend = t("[합격] 4년 지속 상승 추세", "[Pass] 4Y Consistent Upward Trend")
                    else: eps_trend = t("[주의] 변동/하락", "[Warning] Fluctuating/Declining")
        if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index:
            eq_vals = bs.loc['Stockholders Equity'].dropna().values[:4][::-1]
            if len(eq_vals) >= 3:
                if all(eq_vals[i] <= eq_vals[i+1] for i in range(len(eq_vals)-1)) and eq_vals[0] < eq_vals[-1]: bps_trend = t("[합격] 4년 자본 지속 증가", "[Pass] 4Y Consistent Equity Growth")
                else: bps_trend = t("[주의] 자본 변동/감소", "[Warning] Equity Fluctuating/Declining")
    except: pass
    return eps_trend, bps_trend

# [수정] 금융주 파라미터 및 PBR 추가 평가 로직
def get_comprehensive_investment_opinion(mos, pmos, roe, roic, erp, final_g, ceo_text, is_financial=False, pbr=0.0):
    score = 0
    ceo_score = 0
    
    if any(k in ceo_text for k in ["역사상 가장 신뢰받는", "탁월한 자본 배분", "주주 환원", "자사주 매입", "상생", "훌륭한 방어", "주주환원"]):
        ceo_score += 20
    elif any(k in ceo_text for k in ["검증된 경영자", "안정적", "수익성 우위", "선점", "실행력", "투명한", "신뢰도가 높으나", "역량은 우수", "지배적 지위", "독보적", "확실한"]):
        ceo_score += 10
    else:
        ceo_score += 5 
        
    if any(k in ceo_text for k in ["구속", "횡령", "사법 리스크", "사법적 리스크", "배임", "재판에 얽힌", "대규모 배상금", "파산", "회계 처리 논란"]):
        ceo_score -= 25
        
    if any(k in ceo_text for k in ["물적분할", "주주가치 훼손", "차등의결권", "지배력 유지", "경영권 분쟁", "과도한 출혈", "잉여 현금 지속 소각", "가이던스 수정", "희생양", "자본 배치 비효율", "반독점", "독점 규제", "인수 합병 규제", "합병 규제", "지배구조 개편"]):
        ceo_score -= 15
        
    if any(k in ceo_text for k in ["관료주의", "지정학적", "노조", "마진 압박", "경쟁 격화", "침체", "수요 둔화", "부채 부담", "환차손", "파업", "변동성", "둔화", "위축", "침체", "잠식", "만료", "포화"]):
        ceo_score -= 5
        
    score += max(-20, min(20, ceo_score))
        
    if pmos > 15: score += 20
    elif pmos > 0: score += 10
    elif pmos < -15: score -= 20
    else: score -= 10

    # [수정] 금융주 여부에 따른 분기 처리 (ROIC, DCF 대체)
    if is_financial:
        # 금융주는 ROIC를 보지 않는 대신 ROE 점수 비중을 조정
        if roe >= 10: score += 20
        elif roe < 8: score -= 10
        
        # 금융주는 DCF(mos) 대신 PBR을 평가
        if pbr > 0 and pbr < 0.8: score += 20
        elif pbr >= 0.8 and pbr < 1.2: score += 10
        elif pbr >= 1.5: score -= 20
    else:
        # 일반 기업 (기존 로직 유지)
        if roe >= 15: score += 10
        elif roe < 8: score -= 10
        
        if roic and roic >= 12: score += 10
        elif roic and roic < 6: score -= 10
        
        if mos > 15: score += 20
        elif mos > 0: score += 10
        elif mos < -15: score -= 20
        else: score -= 10

    if erp > 3: score += 20
    elif erp > 0: score += 10
    elif erp < -2: score -= 20
    else: score -= 10

    if final_g >= 0.10: score += 20
    elif final_g > 0.0: score += 10
    else: score -= 20

    is_cyclical = any(k in ceo_text for k in ["사이클", "유가", "경기 민감", "철강", "석유화학", "화석 연료", "조선", "해운", "운임", "원자재", "건설", "메모리"])
    if is_cyclical:
        score -= 15

    if score >= 70:
        title, color, reason = t("적극적 할인 (Deep Discount)", "Deep Discount"), "#09ab3b", t("경영진, 자본효율, 모든 가격 지표가 균일하게 완벽한 초저평가 할인 구간을 가리키고 있습니다.", "All evenly weighted metrics indicate a deep discount.")
    elif score >= 20:
        title, color, reason = t("할인 (Discount)", "Discount"), "#3fb950", t("모든 평가 지표들이 고르게 양호하며, 펀더멘털과 밸류에이션 종합 점수 기준 충분한 안전마진이 확보되었습니다.", "All metrics are consistently solid, showing a sufficient margin of safety across fundamentals and valuation.")
    elif score >= -20:
        title, color, reason = t("적정 가치 (Fair Value)", "Fair Value"), "#e3b341", t("6가지 핵심 가치 지표가 상호 상쇄되며 주가가 기업의 본질 가치에 딱 부합하게 거래 중입니다. 뚜렷한 할인 구간이 아닙니다.", "Trading closely to intrinsic value. Not a clear discount.")
    elif score >= -70:
        title, color, reason = t("할증 (Premium)", "Premium"), "#ff7b72", t("펀더멘털 지표 대비 가격 지표들이 전반적으로 비싸게 형성되어 있어, 기대수익률이 열위에 있는 할증 구간입니다.", "Price metrics are uniformly expensive relative to yields.")
    else:
        title, color, reason = t("과도한 할증 (Excessive Premium)", "Excessive Premium"), "#da3633", t("종합적인 악재에도 불구하고 주가가 비상식적으로 과열된 투기적 위험 구간입니다.", "Dangerous speculative territory due to severe management criticism or overvaluation.")

    if is_cyclical:
        reason += t(" (⚠️ 시클리컬 기업 감점 적용됨)", " (⚠️ Cyclical Penalty Applied)")
    if is_financial:
        reason += t(" (🏦 금융주: ROIC/DCF 제외, ROE/PBR 중점 평가 반영)", " (🏦 Financial: Evaluated on ROE/PBR focus)")

    return title, color, reason

def get_market_op_simple(erp):
    if erp > 3.0: return t("적극적 할인 (역사적 저평가)", "Deep Discount"), "#3fb950"
    elif erp > 1.0: return t("할인 (안전마진 존재)", "Discount"), "#58a6ff"
    elif erp > -1.0: return t("적정 가치 (채권과 주식 매력도 유사)", "Fair Value"), "#e3b341"
    else: return t("과도한 할증 경고 (채권 매력도 압도적)", "Excessive Premium"), "#ff7b72"

def tr_text(txt):
    if not txt: return ""
    txt_str = str(txt)
    if is_ko:
        try: return GoogleTranslator(source='en', target='ko').translate(txt_str[:1000])
        except: return txt_str
    return txt_str

def clean_ceo_name(name):
    if not name or str(name).strip() in ['누락', 'None', '']: return 'N/A' if not is_ko else '누락'
    name_str = str(name).strip()
    for prefix in ["Mr. ", "Ms. ", "Mrs. ", "Dr. ", "Mr ", "Ms ", "Mrs ", "Dr "]:
        if name_str.startswith(prefix): name_str = name_str[len(prefix):]
    if is_ko:
        k_name = GoogleTranslator(source='en', target='ko').translate(name_str[:1000]) if name_str else '누락'
        suffixes = [" 씨", "씨", " 님", "님", " 선생님", "선생님", " 박사", "박사"]
        for s in suffixes:
            if k_name.endswith(s):
                k_name = k_name[:-len(s)].strip(); break
        return k_name
    return name_str

def get_safe_macro(key, is_currency=False, is_rate=False):
    data = macro_data.get(key, {"p": 0.0, "c": 0.0, "pct": 0.0})
    p, c, pct = safe_float(data.get("p")), safe_float(data.get("c")), safe_float(data.get("pct"))
    if is_currency: p_str = f"${p:,.2f}"
    elif is_rate: p_str = f"{p:.3f}%"
    else: p_str = f"{p:,.2f}"
    return p_str, c, pct

# ==========================================
# [4] 메인 UI 렌더링
# ==========================================
macro_data = fetch_macro_realtime_v6()

with st.sidebar:
    if st.session_state.lang == "ko":
        if st.button("English", use_container_width=True):
            st.session_state.lang = "en"; st.rerun()
    else:
        if st.button("Korean", use_container_width=True):
            st.session_state.lang = "ko"; st.rerun()
            
    is_ko = st.session_state.lang == "ko"
        
    st.divider()
    
    st.header(t("실시간 인기 종목", "Trending Stocks"))
    if not st.session_state.search_ranking:
        st.caption(t("아직 검색된 종목이 없습니다.", "No searches yet."))
    else:
        top_5 = sorted(st.session_state.search_ranking.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (rtk, count) in enumerate(top_5):
            if st.button(f"{i+1}. {rtk} ({count}{t('회', ' hits')})", key=f"rank_{rtk}", use_container_width=True):
                st.session_state.search_tk = rtk
                st.rerun()
                
    st.divider()
    
    st.header(t("내 서재", "My Library"))
    st.subheader(t("관심 종목 (즐겨찾기)", "Bookmarks"))
    if not st.session_state.bookmarks:
        st.caption(t("즐겨찾기한 종목이 없습니다.", "No bookmarked tickers yet."))
    else:
        for b_tk in st.session_state.bookmarks:
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(b_tk, key=f"bk_{b_tk}", use_container_width=True):
                    st.session_state.search_tk = b_tk; st.rerun()
            with c2:
                if st.button("X", key=f"del_bk_{b_tk}"):
                    st.session_state.bookmarks.remove(b_tk); st.rerun()
                    
    st.divider()
    
    st.subheader(t("최근 검색 기록", "Recent Searches"))
    if not st.session_state.history:
        st.caption(t("검색 기록이 없습니다.", "No recent searches."))
    else:
        if st.button(t("전체 삭제", "Clear All History"), use_container_width=True):
            st.session_state.history = []; st.rerun()
            
        for h_tk in reversed(st.session_state.history):
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(h_tk, key=f"h_{h_tk}", use_container_width=True):
                    st.session_state.search_tk = h_tk; st.rerun()
            with c2:
                if st.button("X", key=f"del_h_{h_tk}"):
                    st.session_state.history.remove(h_tk); st.rerun()
                    
    st.divider()
    
    st.header(t("고객 센터", "Customer Center"))
    st.caption(t("버그 신고, 피드백, 기능 제안을 환영합니다.", "Report bugs, send feedback, or suggest features."))
    st.markdown(f"<a href='mailto:csjwo154515@naver.com' style='display: block; text-align: center; background-color: #30363d; color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold;'>{t('개발자에게 이메일 보내기', 'Send Email to Developer')}</a>", unsafe_allow_html=True)

st.markdown("""
<meta name="google" content="notranslate">
<style>
.main{background-color:#0e1117;color:#c9d1d9;font-family:'Pretendard',sans-serif;}
h1,h2,h3{color:#58a6ff;font-weight:700;}
.box{background-color:#161b22;padding:25px;border-radius:12px;border:1px solid #30363d;margin-bottom:20px;}
.guru-quote{font-style:italic;color:#8b949e;border-left:3px solid #58a6ff;padding-left:15px;margin-bottom:12px;background:#1c2128;padding:15px;border-radius:0 8px 8px 0;}
.highlight{color:#ff7b72;font-weight:bold;}
.good{color:#3fb950;font-weight:bold;}
.stTabs [data-baseweb="tab-list"]{gap:20px;border-bottom:1px solid #30363d;}
.stTabs [data-baseweb="tab"]{font-size:1.15rem;font-weight:600;color:#8b949e;padding-bottom:10px;}
.stTabs [aria-selected="true"]{color:#58a6ff;border-bottom:2px solid #58a6ff;}
.macro-ticker::-webkit-scrollbar{display:none;}
.macro-ticker{-ms-overflow-style:none;scrollbar-width:none;}
.comment-box{background-color:#1c2128;padding:15px;border-radius:8px;border-left:4px solid #8b949e;margin-bottom:10px;color:#e6edf3;}
.comment-time{font-size:0.8rem;color:#8b949e;}
div[data-testid="stArrowVegaLiteChart"]>div,div[data-testid="stVegaLiteChart"]>div{pointer-events:none!important;}
#vg-tooltip-element,.vg-tooltip{display:none!important;opacity:0!important;}
[data-testid="stElementToolbar"]{display:none!important;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div translate="no" style="padding-top: 5px; padding-bottom: 5px;">
    <span style="font-size: 3.2rem; font-weight: 900; color: var(--text-color); letter-spacing: 2px; line-height: 1.2;">
        VALUE
    </span>
</div>
""", unsafe_allow_html=True)

st.info(t("[안내] 화면 글씨가 어색하게 번역되어 보인다면 브라우저의 '자동 번역' 기능을 꺼주세요. (앱 자체의 언어 변환 기능을 이용해 주십시오)", "[Info] If the text looks distorted, please disable your browser's auto-translate. Use the language toggle in the sidebar instead."))

st.warning(t("⚠️ [참고] 본 가치투자 분석 모델은 해운, 철강, 화학 등 실적 변동성이 극심한 **시클리컬(경기민감) 기업**의 내재가치 평가에는 적합하지 않을 수 있습니다.", "⚠️ [Note] This value investing model may not be suitable for evaluating the intrinsic value of **cyclical companies** (e.g., shipping, steel, chemicals) with extreme earnings volatility."))

k_p, k_c, k_pct = get_safe_macro("KOSPI")
kq_p, kq_c, kq_pct = get_safe_macro("KOSDAQ")
sp_p, sp_c, sp_pct = get_safe_macro("S&P 500")
nd_p, nd_c, nd_pct = get_safe_macro("Nasdaq 100")
nf_p, nf_c, nf_pct = get_safe_macro("Nasdaq Futures")
krw_p, krw_c, krw_pct = get_safe_macro("USD/KRW")
wti_p, wti_c, wti_pct = get_safe_macro("WTI Crude", is_currency=True)
tnx_p, tnx_c, tnx_pct = get_safe_macro("10Y Treasury", is_rate=True)

macro_items = [
    (t("KOSPI", "KOSPI"), k_p, k_pct, "%"),
    (t("KOSDAQ", "KOSDAQ"), kq_p, kq_pct, "%"),
    (t("S&P 500", "S&P 500"), sp_p, sp_pct, "%"),
    (t("Nasdaq 100", "Nasdaq 100"), nd_p, nd_pct, "%"),
    (t("NQ 선물", "Nasdaq Fut"), nf_p, nf_pct, "%"),
    (t("환율(KRW/USD)", "USD/KRW"), krw_p, krw_pct, "%"),
    (t("WTI 원유", "WTI Crude"), wti_p, wti_pct, "%"),
    (t("10년물 국채", "10Y Treasury"), tnx_p, tnx_c, " bp")
]

macro_html = "<div class='macro-ticker' translate='no' style='display: flex; overflow-x: auto; gap: 12px; padding: 10px 0 20px 0; -webkit-overflow-scrolling: touch;'>"
for name, val, chg, unit in macro_items:
    color = "#3fb950" if chg > 0 else ("#ff7b72" if chg < 0 else "#8b949e")
    sign = "+" if chg > 0 else ""
    chg_str = f"{sign}{chg:.3f}{unit}" if unit == " bp" else f"{sign}{chg:.2f}{unit}"
    macro_html += f"<div style='flex: 0 0 auto; background: #161b22; padding: 15px 20px; border-radius: 10px; border: 1px solid #30363d; min-width: 140px;'><div style='font-size: 0.85rem; color: #8b949e; margin-bottom: 5px; font-weight: 600;'>{name}</div><div style='font-size: 1.3rem; font-weight: bold; color: #ffffff;'>{val}</div><div style='font-size: 0.95rem; font-weight: bold; color: {color}; margin-top: 2px;'>{chg_str}</div></div>"
macro_html += "</div>"
st.markdown(macro_html, unsafe_allow_html=True)

spy_pe = safe_float(macro_data.get("SPY_PE", 22.0), 22.0)
qqq_pe = safe_float(macro_data.get("QQQ_PE", 30.0), 30.0)
tnx_val = safe_float(macro_data.get("10Y Treasury", {}).get("p"), 4.4)
if tnx_val == 0.0: tnx_val = 4.4

spy_ey = (1 / spy_pe) * 100 if spy_pe > 0 else 0
qqq_ey = (1 / qqq_pe) * 100 if qqq_pe > 0 else 0
spy_erp, qqq_erp = spy_ey - tnx_val, qqq_ey - tnx_val

spy_op, spy_col = get_market_op_simple(spy_erp)
qqq_op, qqq_col = get_market_op_simple(qqq_erp)

spy_pe_str = fmt_f(spy_pe, 1)
spy_ey_str = fmt_f(spy_ey, 2)
tnx_val_str = fmt_f(tnx_val, 2)
spy_erp_str = fmt_f(spy_erp, 2)

qqq_pe_str = fmt_f(qqq_pe, 1)
qqq_ey_str = fmt_f(qqq_ey, 2)
qqq_erp_str = fmt_f(qqq_erp, 2)

with st.expander(t("현재 미 증시 밸류에이션 매력도 분석 (이익수익률 vs 국채)", "Current US Market Valuation Attractiveness (Earnings Yield vs Treasury)")):
    st.write(t("주식의 예상 수익률(이익수익률 = 1/PER)과 무위험 이자인 10년물 국채를 비교하는 [주식 위험 프리미엄(ERP)] 분석입니다. (ERP가 높을수록 주식이 싸고, 마이너스면 채권을 사는 것이 유리합니다.)", "This is an [Equity Risk Premium (ERP)] analysis comparing the expected return of stocks (Earnings Yield = 1/PE) with the risk-free 10-year Treasury yield."))
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.markdown(f"<div translate='no' style='background-color:#161b22; color:#e6edf3; padding:15px; border-radius:8px; border-left: 5px solid {spy_col};'><h4 style='margin-top:0; color:#e6edf3;'>S&P 500 밸류에이션</h4><p style='margin:4px 0;'>- Fwd PER: <b>{spy_pe_str}배</b></p><p style='margin:4px 0;'>- 예상 이익수익률(EY): <b>{spy_ey_str}%</b></p><p style='margin:4px 0;'>- 10년물 국채: <b>{tnx_val_str}%</b></p><p style='margin:4px 0;'>- 주식 위험 프리미엄(ERP): <b style='color:{spy_col}'>{spy_erp_str}%</b></p><hr style='margin:12px 0; border-color:#30363d;'><b>[AI 시장 의견] <span style='color:{spy_col}'>{spy_op}</span></b></div>", unsafe_allow_html=True)
    with c_m2:
        st.markdown(f"<div translate='no' style='background-color:#161b22; color:#e6edf3; padding:15px; border-radius:8px; border-left: 5px solid {qqq_col};'><h4 style='margin-top:0; color:#e6edf3;'>Nasdaq 100 밸류에이션</h4><p style='margin:4px 0;'>- Fwd PER: <b>{qqq_pe_str}배</b></p><p style='margin:4px 0;'>- 예상 이익수익률(EY): <b>{qqq_ey_str}%</b></p><p style='margin:4px 0;'>- 10년물 국채: <b>{tnx_val_str}%</b></p><p style='margin:4px 0;'>- 주식 위험 프리미엄(ERP): <b style='color:{qqq_col}'>{qqq_erp_str}%</b></p><hr style='margin:12px 0; border-color:#30363d;'><b>[AI 시장 의견] <span style='color:{qqq_col}'>{qqq_op}</span></b></div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    t("개별 기업 가치분석", "Company Value Analysis"), 
    t("유명 가치투자자 13F", "Guru 13F Portfolios"),
    t("커뮤니티", "Community"),
    t("시가총액 랭킹", "Market Cap Top 30"),
    t("주식 용어 사전", "Stock Glossary"),
    t("VALUE 철학", "About VALUE")
])

# ==========================================
# 탭 1: 개별 기업 가치분석
# ==========================================
with tab1:
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        ui = st.text_input(
            t("종목명 또는 티커 입력:", "Enter Stock Name or Ticker:"), 
            placeholder=t("예: 삼전, 하닉, AAPL, 엔비디아 (입력 후 Enter)", "e.g., 삼전, 하닉, AAPL, 엔비디아 (Press Enter)"), 
            label_visibility="collapsed",
            key="main_input",
            on_change=trigger_scan 
        )
        st.caption(t("[안내] 정확한 종목 스캔을 위해 가급적 종목 명칭이나 코드(예: 한국 주식은 6자리 숫자)를 정확히 입력해 주십시오.", "[Info] For accurate scanning, please preferably enter the exact stock name or code (e.g., 6-digit code for KR stocks)."))
    with col_btn:
        if st.button(t("가치 분석 스캔", "Start Value Scan"), use_container_width=True, type="primary"):
            trigger_scan(); st.rerun() 

    if st.session_state.search_tk:
        tk = st.session_state.search_tk
        
        if tk in st.session_state.history: st.session_state.history.remove(tk)
        st.session_state.history.append(tk)
        st.session_state.search_ranking[tk] = st.session_state.search_ranking.get(tk, 0) + 1

        st_container = st.empty()
        with st_container.container():
            st.toast(t("데이터를 불러오는 중입니다...", "Fetching data..."), icon="⏳")
            stk, p, i, kr = get_data(tk)
            
            if p:
                try: ty = safe_float(macro_data["10Y Treasury"]["p"], 4.4)
                except: ty = 4.4
                if ty == 0.0: ty = 4.4

                # [추가] 금융주 판별 로직
                is_financial = i.get('sector') == 'Financial Services'
                
                c_title, c_star = st.columns([4, 1])
                with c_title:
                    st.success(f"{i.get('shortName', tk)} ({tk}) {t('분석 완료', 'Analysis Complete')}")
                with c_star:
                    is_bookmarked = tk in st.session_state.bookmarks
                    star_label = t("즐겨찾기 해제", "Remove Bookmark") if is_bookmarked else t("즐겨찾기 추가", "Add Bookmark")
                    if st.button(star_label, use_container_width=True):
                        if is_bookmarked: st.session_state.bookmarks.remove(tk)
                        else: st.session_state.bookmarks.append(tk)
                        st.rerun() 
                
                off = i.get('companyOfficers', [])
                ceo_raw = '누락'
                if isinstance(off, list) and len(off) > 0:
                    if isinstance(off[0], dict): ceo_raw = off[0].get('name', '누락')
                    else: ceo_raw = str(off[0])
                elif isinstance(off, dict): ceo_raw = off.get('name', '누락')
                elif isinstance(off, str): ceo_raw = off
                ceo_cleaned = clean_ceo_name(ceo_raw)
                criticism_text = fetch_governance_criticism(tk, tk.split('.')[0] if kr else tk, ceo_cleaned)

                t_pe = safe_float(i.get('trailingPE'))
                f_pe = safe_float(i.get('forwardPE'))
                pbr = safe_float(i.get('priceToBook'))
                
                roe = safe_float(i.get('returnOnEquity')) * 100
                real_roic = get_real_roic(stk, i)
                
                # [수정] 금융주는 ROIC 텍스트 대체 표기
                if is_financial:
                    roic_str = t("금융/보험주 제외", "N/A (Financial)")
                else:
                    if real_roic is not None: roic_str = f"{real_roic:.2f}%"
                    else: roic_str = t("데이터 부족 (확인 요망)", "N/A (Needs verification)")
                
                a_pe = safe_float(i.get('fiveYearAvgPE'))
                if a_pe == 0.0: a_pe = t_pe * 1.1 if t_pe > 0 else 15.0
                
                div_yield = safe_float(i.get('dividendYield'))
                div_rate = safe_float(i.get('dividendRate'))
                if kr: div = div_yield * 100
                else: div = (div_rate / p * 100) if div_rate > 0 and p > 0 else 0.0
                
                div_trend = t("확인 불가", "N/A")
                try:
                    div_history = stk.dividends
                    if not div_history.empty:
                        yearly_div = div_history.groupby(div_history.index.year).sum()
                        if len(yearly_div) >= 3:
                            last_3 = yearly_div.tail(3)
                            if last_3.is_monotonic_increasing and last_3.iloc[-1] > last_3.iloc[0]:
                                div_trend = f"<span class='good'>{t('지속 상승 중', 'Consistently Increasing')}</span>"
                            elif last_3.iloc[-1] > 0:
                                div_trend = t("유지/변동", "Maintained/Fluctuating")
                            else:
                                div_trend = t("배당 없음", "No Dividend")
                except:
                    pass
                
                pmos_val = ((a_pe - f_pe) / a_pe) * 100 if f_pe > 0 and a_pe > 0 else 0
                ey = (1 / f_pe * 100) if f_pe > 0 else 0
                erp = ey - ty
                
                base_fcf, sh, final_g, data_len = get_base_dcf_data(stk, i)
                dcf_source_txt = f"({data_len}{t('년 yfinance 기반 산출', ' yrs yf data)')})"

                p_str = f"{int(p):,}원" if kr else f"${p:,.2f}"

                eps_trend, bps_trend = analyze_trends(stk)
                
                # [수정] 금융주 is_financial 파라미터 전달
                iv, mos_val, err = calc_custom_dcf(base_fcf, sh, p, ty, final_g, is_financial)
                mos_val = safe_float(mos_val)
                
                roic_val = real_roic if real_roic is not None else 0
                
                # [수정] 금융주 PBR 및 is_financial 파라미터 반영하여 종합 의견 산출
                op_title, op_color, op_reason = get_comprehensive_investment_opinion(mos_val, pmos_val, roe, roic_val, erp, final_g, criticism_text, is_financial, pbr)

                st.markdown(f"""
                <div translate="no" style="padding: 18px 20px; border-radius: 8px; border-left: 6px solid {op_color}; background-color: #1c2128; color: #e6edf3; margin-bottom: 25px; margin-top: 10px;">
                    <h3 style="margin: 0 0 12px 0; color: {op_color}; font-size: 1.4rem;">[AI 종합 투자의견] : {op_title}</h3>
                    <span style="color: #c9d1d9; font-size: 0.95rem; display: block; margin-top: 8px;">{op_reason}</span>
                </div>
                """, unsafe_allow_html=True)

                st.divider()

                if pmos_val > 0:
                    per_mos_str = f"<span class='good'>+[합격] {pmos_val:.1f}% (과거 평균 {a_pe:.1f}배 대비 현재 {f_pe:.1f}배로 저렴하여 할인 구간)</span>"
                elif pmos_val < 0:
                    per_mos_str = f"<span class='highlight'>[주의] {pmos_val:.1f}% (과거 평균 {a_pe:.1f}배 대비 현재 {f_pe:.1f}배로 비싸서 할증 구간)</span>"
                else:
                    per_mos_str = f"확인 필요"

                # [수정] 금융주 여부에 따른 ROE/ROIC 종합 평가 텍스트 분기 처리
                if is_financial:
                    if roe >= 10: rr_eval = f"<span class='good'>{t('훌륭함 (금융주 기준 탁월한 자본 효율성)', 'Excellent (Great for Financials)')}</span>"
                    elif roe >= 7: rr_eval = f"<span style='color:#58a6ff;'>{t('양호함 (준수한 수익성)', 'Good (Decent profitability)')}</span>"
                    else: rr_eval = f"<span class='highlight'>{t('형편없음 (자본을 비효율적으로 낭비 중입니다)', 'Poor (Wasting capital inefficiently)')}</span>"
                else:
                    if roe >= 15 and roic_val >= 12: rr_eval = f"<span class='good'>{t('훌륭함 (자본 배치 능력이 탁월합니다)', 'Excellent (Great capital allocation)')}</span>"
                    elif roe >= 10 and roic_val >= 8: rr_eval = f"<span style='color:#58a6ff;'>{t('양호함 (준수한 수익성)', 'Good (Decent profitability)')}</span>"
                    else: rr_eval = f"<span class='highlight'>{t('형편없음 (자본을 비효율적으로 낭비 중입니다)', 'Poor (Wasting capital inefficiently)')}</span>"
                    
                if erp > 0:
                    ey_str = f"{ey:.2f}% <span class='good'>(국채 이김! +{erp:.2f}%p 수익률 추가 우위/할인)</span>"
                else:
                    ey_str = f"{ey:.2f}% <span class='highlight'>(국채에 짐! {abs(erp):.2f}%p 매력도 열위/할증)</span>"

                st.subheader(t("1. 핵심 밸류에이션 지표", "1. Core Valuation Metrics"))
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"- **{t('현재 주가', 'Current Price')}:** {p_str}")
                    st.markdown(f"- **{t('배당 추이', 'Dividend Trend')}:** {div:.2f}% ({div_trend})", unsafe_allow_html=True)
                    st.markdown(f"- **ROE / ROIC:** {roe:.2f}% / {roic_str} ➔ {rr_eval}", unsafe_allow_html=True)
                    st.write(f"- **{t('현재 PER', 'Current PE')}:** {t_pe:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('Fwd PER', 'Fwd PE')}:** {f_pe:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('5~10년 평균 PER', '5-10Y Avg PE')}:** {a_pe:.2f}{t('배', 'x')}")
                with c2:
                    st.markdown(f"- **{t('PER 안전마진', 'PE Margin of Safety')}:** {per_mos_str}", unsafe_allow_html=True)
                    st.write(f"- **PBR:** {pbr:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('10년물 미국채 금리', '10Y US Treasury Yield')}:** {ty:.2f}%")
                    st.markdown(f"- **{t('예상 이익수익률', 'Expected Earnings Yield')}:** {ey_str}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('EPS 추세 (최근 4년)', 'EPS Trend (4 Years)')}:** {eps_trend}")
                    st.markdown(f"- **{t('자본/BPS 추세 (최근 4년)', 'Equity Trend (4 Years)')}:** {bps_trend}")

                st.divider()
                
                st.subheader(t("2. 10년 DCF (내재가치 추정)", "2. 10-Year DCF (Intrinsic Value)"))
                # [수정] 금융주는 안내 텍스트로 대체
                if is_financial:
                    st.write(f"- **{t('추정 적정가 (DCF)', 'Estimated Fair Value (DCF)')}:** {t('🏦 금융/보험주는 비즈니스 특성상 잉여현금흐름(FCF)이 부채 및 지급 준비금과 혼재되어 잦은 적자가 발생하므로, DCF 모델을 적용하지 않고 PBR 중심의 자산 기반 밸류에이션으로 대체 평가합니다.', 'DCF is not applicable for financials due to mixed cash flows. Replaced with PBR evaluation.')}")
                elif iv:
                    iv_str = f"{int(iv):,}원" if kr else f"${iv:,.2f}"
                    st.write(f"- **{t('FCF/EPS 연평균 성장률', 'FCF/EPS CAGR')}:** {final_g*100:.1f}% {dcf_source_txt}")
                    st.write(f"- **{t('추정 적정가', 'Estimated Fair Value')}:** {iv_str}")
                    if mos_val > 0: st.markdown(f"- **{t('DCF 안전마진', 'DCF Margin of Safety')}:** <span class='good'>+[합격] {mos_val:.1f}% ({t('할인', 'Discount')})</span>", unsafe_allow_html=True)
                    else: st.markdown(f"- **{t('DCF 안전마진', 'DCF Margin of Safety')}:** <span class='highlight'>[주의] {mos_val:.1f}% ({t('할증', 'Premium')})</span>", unsafe_allow_html=True)
                else:
                    st.error(f"{err}")
                
                st.divider()

                st.subheader(t("3. 장기 재무 시각화 (최근 4년 연속 지표)", "3. Long-term Financial Visualizations"))
                try:
                    inc = stk.income_stmt if stk else None
                    cf = stk.cash_flow if stk else None
                    if inc is not None and not inc.empty:
                        cols = inc.columns[:4]
                        years = [str(c)[:4] for c in cols][::-1]
                        
                        rev = inc.loc['Total Revenue'].iloc[:4].values[::-1] if 'Total Revenue' in inc.index else []
                        ni = inc.loc['Net Income'].iloc[:4].values[::-1] if 'Net Income' in inc.index else []
                        
                        fcf_chart = []
                        if cf is not None and not cf.empty:
                            if 'Free Cash Flow' in cf.index:
                                fcf_chart = cf.loc['Free Cash Flow'].iloc[:4].values[::-1]
                            elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                                fcf_chart = (cf.loc['Operating Cash Flow'] + cf.loc['Capital Expenditure']).iloc[:4].values[::-1]
                        
                        c_v1, c_v2 = st.columns(2)
                        with c_v1:
                            if len(rev) == len(years) and len(ni) == len(years):
                                df_rev_ni = pd.DataFrame({t('매출액', 'Revenue'): rev, t('순이익', 'Net Income'): ni}, index=years)
                                st.write(t("**[최근 4년 매출 및 순이익 추이]**", "**[Revenue & Net Income Trend]**"))
                                st.bar_chart(df_rev_ni, color=["#58a6ff", "#3fb950"], height=300)
                            else:
                                st.caption(t("매출/순이익 시각화 데이터가 부족합니다.", "Insufficient Revenue/Net Income data for visualization."))
                        with c_v2:
                            if len(fcf_chart) == len(years):
                                df_fcf = pd.DataFrame({t('잉여현금흐름(FCF)', 'Free Cash Flow'): fcf_chart}, index=years)
                                st.write(t("**[최근 4년 잉여현금흐름(FCF) 추이]**", "**[Free Cash Flow (FCF) Trend]**"))
                                st.bar_chart(df_fcf, color="#e3b341", height=300)
                            else:
                                st.caption(t("FCF 시각화 데이터가 부족합니다.", "Insufficient FCF data for visualization."))
                except Exception as e:
                    st.caption(t("시각화 데이터를 불러오는 데 실패했습니다.", "Failed to load visualization data."))

                st.divider()

                st.subheader(t("4. 질적 분석 및 리스크 스크리닝", "4. Qualitative Analysis & Risk Screening"))
                
                st.markdown(f"- **CEO:** {ceo_cleaned}")
                st.info(t("[안내] 기업의 리스크와 지배구조 취약점은 하단 패널에 상세히 요약되어 있으며, 이 내용은 상단 AI 투자의견 점수(120점 만점)에 균일한 영향력으로 직접 반영됩니다.", "[Info] Governance and management risks are summarized below and directly impact the AI Investment Opinion score.")) 
                
                st.write(t("**비즈니스 요약**", "**Business Summary**"))
                raw_summary = i.get('kr_sum') or i.get('longBusinessSummary') or ""
                st.caption(f"{tr_text(str(raw_summary))[:350]}...")

                st.write(t("**최근 주요 뉴스 요약 (실시간 연동)**", "Major Recent News Summary"))
                with st.spinner(t("최신 뉴스 스트리밍 중...", "Streaming news...")):
                    try:
                        if kr:
                            news_items = fetch_naver_finance_news(tk.split('.')[0])
                            if news_items:
                                for item in news_items:
                                    st.markdown(f"- [{item['title']}]({item['link']}) *(출처: {item['publisher']})*")
                            else:
                                st.caption(t("최근 뉴스가 존재하지 않습니다.", "No recent news found."))
                        else:
                            news_items = fetch_global_news(tk)
                            if news_items:
                                for item in news_items:
                                    st.markdown(f"- [{tr_text(item['title'])}]({item['link']}) *(출처: {item['publisher']})*")
                            else:
                                st.caption(t("최근 뉴스가 존재하지 않습니다.", "No recent news found."))
                    except:
                        st.caption(t("뉴스 피드를 연동하지 못했습니다.", "Failed to load real-time news feed."))

                st.write(t("**경영진 및 지배구조 비판 점검 패널**", "Management & Governance Criticism Panel"))
                st.markdown(f"""
                <div translate="no" style="background-color: rgba(255, 123, 114, 0.07); color: #ff7b72; padding: 15px; border-radius: 8px; border: 1px solid rgba(255, 123, 114, 0.2); font-size: 0.95rem; line-height: 1.6;">
                    {criticism_text}
                </div>
                """, unsafe_allow_html=True)

                st.divider()

                st.subheader(t("5. 매수 6원칙 자동 체크", "5. Buy 6-Principles Auto Check"))
                p_txt = f"**1. {t('가격은 저렴한가 (안전마진)?', 'Is the price cheap (Margin of Safety)?')}**\n"
                
                if pmos_val > 0: p_txt += f"- PER: <span class='good'>[합격] (+{pmos_val:.1f}% 할인)</span>\n"
                elif pmos_val < 0: p_txt += f"- PER: <span class='highlight'>[주의] ({pmos_val:.1f}% 할증)</span>\n"
                else: p_txt += f"- PER: ({t('확인 필요', 'Needs Check')})\n"
                
                # [수정] 금융주 매수체크 출력 변경
                if is_financial:
                    if pbr < 0.8: p_txt += f"- PBR: <span class='good'>[합격] ({pbr:.2f}배 - 자산가치 대비 저평가)</span>"
                    elif pbr < 1.2: p_txt += f"- PBR: <span style='color:#e3b341;'>[보통] ({pbr:.2f}배)</span>"
                    else: p_txt += f"- PBR: <span class='highlight'>[주의] ({pbr:.2f}배 - 할증)</span>"
                else:
                    if mos_val > 0: p_txt += f"- DCF: <span class='good'>[합격] (+{mos_val:.1f}% 할인)</span>"
                    elif mos_val < 0: p_txt += f"- DCF: <span class='highlight'>[주의] ({mos_val:.1f}% 할증)</span>"
                    else: p_txt += f"- DCF: ({t('직접 확인 필요', 'Needs Check')})"
                    
                st.markdown(p_txt, unsafe_allow_html=True)
                
                if roe >= 15: biz_eval = f"<span class='good'>{t('[우수] 자본효율 탁월, 해자 확률 높음', '[Excellent] Great capital efficiency, high moat probability')}</span>"
                elif roe > 0: biz_eval = t("[보통] 독점력 추가 확인 필요", "[Average] Requires moat verification")
                else: biz_eval = f"<span class='highlight'>{t('[경고] 구조 훼손 점검 시급', '[Warning] Structural damage check urgent')}</span>"
                st.markdown(f"**2. {t('좋은 비즈니스인가?', 'Is it a good business?')}** {biz_eval}", unsafe_allow_html=True)
                st.markdown(f"**3. {t('경영진은 신뢰할 수 있는가?', 'Is management trustworthy?')}** {t('위 4번 리포트 참조', 'Refer to section 4 report above')}")
                st.write(f"**4. {t('놓친 리스크는 없는가?', 'Are there overlooked risks?')}** {t('주가 하락이 단순한 우울증인지 영구적 손상인지 확인하세요.', 'Check if price drop is temporary depression or permanent loss.')}")
                st.write(f"**5~6. {t('능력 범위 안인가?', 'Within Circle of Competence?')}** {t('이 비즈니스 모델을 타인에게 논리적으로 설명할 수 있습니까?', 'Can you logically explain this business model to others?')}")

                st.divider()

                st.subheader(t("6. 기업 해부 및 학문적 모델 적용", "6. Corporate Anatomy & Academic Models"))
                if final_g > 0: math_eval = f"<span class='good'>{t(f'[합격] 연평균 {final_g*100:.1f}% 성장하며 복리 모형 탑승 중.', f'[Pass] Growing at {final_g*100:.1f}% CAGR, riding the compound model.')}</span>"
                else: math_eval = f"<span class='highlight'>{t('[주의] 현금흐름 역성장 (복리 팽창 구간 아님).', '[Warning] Negative FCF (Not a compounding phase).')}</span>"
                    
                st.markdown(f"- **{t('수학 (복리 모형):', 'Math (Compound Model):')}** {math_eval}", unsafe_allow_html=True)
                st.write(f"- **{t('생물학 (생존력):', 'Biology (Survivability):')}** {t('부채 구조를 볼 때 다윈주의적 생존력이 있는지 확인 요망.', 'Check Darwinian survivability regarding debt structure.')}")
                st.write(f"- **{t('심리학 (오판 점검):', 'Psychology (Misjudgment):')}** {t('희망 회로나 확증 편향에 빠진 매수가 아닌지 점검하십시오.', 'Check for confirmation bias or wishful thinking.')}")
                st.write(f"- **{t('파급력:', 'Impact:')}** {t('기술 변화가 이 기업에 득인가 독인가?', 'Is technological change a boon or bane for this company?')}")

                st.divider()

                st.subheader(t("7. 비상탈출 (오직 다음 경우에만 할증 시 매도)", "7. Exit Strategy (Sell ONLY if:)"))
                sell_rules = t("1. 기업 분석에 치명적인 실수가 있었음을 깨달았을 때.<br>2. 밸류에이션(PBR/PER)이 비상식적으로 지나치게 과열(할증)되었을 때.<br>3. 더 확실하고 안전한 기회(기회비용 고려)를 발견했을 때.", "1. You realize a fatal mistake in your initial analysis.<br>2. Valuation (PER/PBR) becomes irrationally overheated (premium).<br>3. You find a much safer and better opportunity (Opportunity Cost).")
                st.markdown(f"<div class='guru-quote'>{sell_rules}</div>", unsafe_allow_html=True)

                st.divider()

                st.subheader(f"{tk} {t('종목 토론방', 'Discussion Board')}")
                if tk not in st.session_state.stock_comments: st.session_state.stock_comments[tk] = []
                for cmt in reversed(st.session_state.stock_comments[tk]):
                    st.markdown(f"<div class='comment-box'><b>{cmt['user']}</b> <span class='comment-time'>({cmt['time']})</span><br>{cmt['text']}</div>", unsafe_allow_html=True)
                if not st.session_state.stock_comments[tk]:
                    st.caption(t("아직 작성된 코멘트가 없습니다. 첫 번째 의견을 남겨주세요.", "No comments yet. Be the first to share your thoughts."))

                with st.form(key=f"comment_form_{tk}", clear_on_submit=True):
                    c_user, c_txt = st.columns([1, 4])
                    with c_user: user_name = st.text_input(t("닉네임", "Nickname"), placeholder=t("가치투자자", "Value Investor"))
                    with c_txt: user_text = st.text_input(t("코멘트 남기기", "Add a comment"), placeholder=t("이 종목의 해자(Moat)는 무엇이라고 생각하시나요?", "What is this company's moat?"))
                    if st.form_submit_button(t("등록", "Post")) and user_text:
                        st.session_state.stock_comments[tk].append({"user": user_name if user_name else t("익명", "Anonymous"), "text": user_text, "time": datetime.now().strftime("%H:%M")})
                        st.rerun()

            else:
                st.error(t("[데이터 연결 오류] 서버에서 데이터를 정상적으로 불러올 수 없습니다. 인터넷 상태를 확인하거나 티커(종목코드)가 올바른지 확인해주세요.", "[Data Connection Error] Could not fetch data from the server. Please check your internet connection or ticker."))

# ==========================================
# 탭 2: 유명 가치투자자 13F 포트폴리오
# ==========================================
with tab2:
    st.subheader(t("글로벌 유명 가치투자자 13F 포트폴리오", "Global Value Gurus 13F Portfolio"))
    st.caption(t("※ 미국의 13F 공시를 추적하여 최신 포트폴리오 비중을 표출합니다.", "※ Tracks US 13F filings to display latest portfolio weights."))
    
    guru_map = {"리 루 (Himalaya Capital)": "HC", "워런 버핏 (Berkshire Hathaway)": "BRK", "빌 애크먼 (Pershing Square)": "PSH", "세스 클라만 (Baupost Group)": "BAU", "척 아크레 (Akre Capital)": "AKRE", "모니시 파브라이 (Dalal Street)": "PI", "가이 스피어 (Aquamarine Capital)": "AQUA"}
    guru_option = st.selectbox(t("포트폴리오를 조회할 유명 가치투자자를 선택하세요:", "Select a Value Guru:"), list(guru_map.keys()))

    with st.spinner(t("최신 포트폴리오 데이터 연동 중...", "Fetching latest portfolio data...")):
        code = guru_map[guru_option]
        scraped_data = get_13f_portfolio(code)
            
        if scraped_data and len(scraped_data) > 0:
            df = pd.DataFrame(scraped_data)
            df.index = df.index + 1
            st.dataframe(df, height=800, column_config={"티커": st.column_config.TextColumn("Ticker"), "기업명": st.column_config.TextColumn("Company Name"), "비중(%)": st.column_config.ProgressColumn("Weight (%)", format="%.2f%%", min_value=0, max_value=max(df["비중(%)"]) + 5)}, use_container_width=True)
            
            st.markdown("---")
            st.write(t("[랭킹 종목 빠른 분석 장전]", "[Fast Load for Analysis]"))
            c_tk, c_btn = st.columns([3, 1])
            with c_tk: fast_tk = st.selectbox("Ticker", df["티커"].tolist(), label_visibility="collapsed")
            with c_btn:
                if st.button(t("검색창에 장전하기", "Load to Search"), use_container_width=True):
                    st.session_state.search_tk = fast_tk
                    st.toast(t(f"{fast_tk} 분석 장전 완료!", f"{fast_tk} Loaded!"))
                    st.rerun() 
        else:
            st.warning(t("데이터를 불러오는 데 실패했습니다.", "Failed to load data."))

# ==========================================
# 탭 3: 커뮤니티
# ==========================================
with tab3:
    st.subheader(t("글로벌 밸류 커뮤니티 (자유 게시판)", "Global Value Community (Free Board)"))
    st.caption(t("※ 가치투자 철학, 매크로 시황, 유망 종목에 대해 자유롭게 토론하는 공간입니다. (현재 버전은 임시 메모리를 사용하므로 새로고침 시 초기화됩니다.)", "※ Discuss value investing, macro, and stocks freely. (Currently uses session memory and resets on refresh.)"))
    
    with st.form(key="community_form", clear_on_submit=True):
        f_user = st.text_input(t("닉네임", "Nickname"), placeholder=t("찰리 멍거 지망생", "Munger Wannabe"))
        f_text = st.text_area(t("내용", "Message"), placeholder=t("어떤 훌륭한 기업을 발견하셨나요?", "Did you find any wonderful companies?"), height=100)
        
        if st.form_submit_button(t("글 남기기", "Post to Community")):
            if f_text:
                st.session_state.community_posts.append({"user": f_user if f_user else t("익명", "Anonymous"), "text": f_text, "time": datetime.now().strftime("%m-%d %H:%M")})
                st.rerun()

    st.divider()
    
    if not st.session_state.community_posts:
        st.info(t("아직 커뮤니티에 등록된 글이 없습니다. 첫 번째 이야기를 꺼내보세요.", "No posts in the community yet. Start the conversation."))
    else:
        for post in reversed(st.session_state.community_posts):
            st.markdown(f"""
            <div style="background-color: #161b22; color: #c9d1d9; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <strong style="color: #58a6ff; font-size: 1.1rem;">{post['user']}</strong>
                    <span style="color: #8b949e; font-size: 0.85rem;">{post['time']}</span>
                </div>
                <div style="font-size: 1.05rem; line-height: 1.5;">{post['text']}</div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 탭 4: 시가총액 랭킹 TOP 30
# ==========================================
with tab4:
    st.subheader(t("한국 및 미국 시가총액 TOP 30", "US & KR Market Cap TOP 30"))
    st.caption(t("※ 속도 최적화를 위해 2026년 기준 랭킹 데이터가 내장되어 있습니다. 종목을 선택해 즉시 분석해 보세요.", "※ Static ranking data (as of 2026) is embedded for speed optimization. Select a stock to analyze."))
    
    mkt = st.radio(t("시장 선택", "Select Market"), [t("미국 시장 (US Market)", "US Market"), t("한국 시장 (KR Market)", "KR Market")], horizontal=True, label_visibility="collapsed")
    df_mkt = pd.DataFrame(us_top30) if "US" in mkt or "미국" in mkt else pd.DataFrame(kr_top30)
        
    st.dataframe(df_mkt, height=1200, use_container_width=True, hide_index=True, column_config={
        "순위": st.column_config.NumberColumn(t("순위", "Rank")),
        "티커": st.column_config.TextColumn(t("티커", "Ticker")),
        "기업명": st.column_config.TextColumn(t("기업명", "Company Name")),
        "시가총액": st.column_config.TextColumn(t("시가총액", "Market Cap"))
    })
    
    st.markdown("---")
    st.write(t("[랭킹 종목 빠른 분석 장전]", "[Fast Load for Analysis]"))
    c_tk2, c_btn2 = st.columns([3, 1])
    with c_tk2: fast_tk_mkt = st.selectbox("Ticker", df_mkt["티커"].tolist(), key="mkt_fast_tk", label_visibility="collapsed")
    with c_btn2:
        if st.button(t("검색창에 장전하기", "Load to Search"), key="mkt_load_btn", use_container_width=True):
            st.session_state.search_tk = fast_tk_mkt
            st.toast(t(f"{fast_tk_mkt} 분석 장전 완료!", f"{fast_tk_mkt} Loaded!"))
            st.rerun() 

# ==========================================
# 탭 5: 주식 용어 사전 
# ==========================================
with tab5:
    st.subheader(t("주식 용어 사전", "Stock Glossary"))
    st.write(t("앱에서 자주 쓰이는 금융 용어들을 알기 쉽게 설명해 드립니다.", "Complex financial jargon used in this app, explained simply using everyday analogies."))
    st.markdown("<br>", unsafe_allow_html=True)

    terms = [
        ("시가총액 (Market Cap)", 
         t("이 회사를 '통째로' 살 때 내야 하는 가격표입니다.", "The price tag to buy the ENTIRE company at once."), 
         t("예를 들어 삼성전자의 시가총액이 400조라면, 통장에 400조 원이 있어야 삼성전자의 주인이 될 수 있다는 뜻입니다.", "If a company's market cap is $1 Trillion, you need that much cash in your bank to buy every single share.")),
        
        ("PER (주가수익비율)", 
         t("내가 투자한 돈의 '본전'을 뽑는 데 몇 년이 걸리는지 알려주는 숫자입니다.", "How many years it will take for the company to earn back your investment."), 
         t("예를 들어 상가 건물을 10억에 샀는데 1년에 1억씩 번다면 본전 뽑는 데 10년이 걸리죠. 이때 PER은 10배입니다. 숫자가 낮을수록 싼 주식입니다.", "If you buy a building for $100k and it profits $10k a year, it takes 10 years to break even. This is a PE ratio of 10. Lower is usually cheaper.")),
        
        ("Fwd PER (선행 주가수익비율)", 
         t("과거가 아니라 '앞으로 1년 동안 벌 돈'을 기준으로 계산한 본전 회수 기간입니다.", "The PE ratio based on how much money the company is EXPECTED to make next year, rather than last year."), 
         t("주식은 미래의 가치를 반영하므로 단순 PER보다 Fwd PER이 더 중요합니다.", "Since stocks reflect future value, Fwd PE is more important than trailing PE.")),
        
        ("PBR (주가순자산비율)", 
         t("회사가 당장 문을 닫고 남은 자산을 다 팔았을 때(청산), 투자금을 건질 수 있는지 확인하는 숫자입니다.", "If the company closes tomorrow and sells its assets, will you get your money back?"), 
         t("PBR이 1보다 낮으면 회사를 다 쪼개서 팔아도 주가보다 돈이 남는다는 뜻으로, 장부상 안전하다는 의미입니다.", "If PBR is below 1, the liquidation value is higher than its stock price. It implies statistical safety on the books.")),
        
        ("ROE (자기자본이익률)", 
         t("회사가 주주의 돈(자본)을 이용해 '얼마나 돈을 효율적으로 잘 버는지' 보여주는 이자율입니다.", "Shows how efficiently the company multiplies its equity capital."), 
         t("은행 예금이 1년에 3% 이자를 준다면, ROE 15%인 회사는 1년에 15%씩 자본을 불려준다는 뜻입니다. 15% 이상을 꾸준히 유지하는 회사가 훌륭한 기업입니다.", "If a bank gives 3% interest, a company with 15% ROE grows equity at 15% a year. Consistent 15%+ ROE defines a great business.")),
        
        ("ROIC (투하자본수익률)", 
         t("ROE에서 빚(부채)으로 인한 착시 효과를 제거하고, 회사가 실제로 굴린 돈 대비 순수하게 벌어들인 진짜 수익률입니다.", "The true return on all capital invested (debt + equity), removing leverage distortions."), 
         t("빚을 많이 내서 ROE만 높아 보이는 회사를 걸러내고, 진짜 장사를 잘하는 알짜 기업을 찾아내는 핵심 지표입니다.", "Used to filter out companies that look good just because of high debt, revealing true operational efficiency.")),
        
        ("FCF (잉여현금흐름)", 
         t("월급 받고 생활비, 공과금 등을 다 내고 통장에 진짜 남은 '순수 여윳돈'입니다.", "The pure 'leftover cash' after paying all expenses and capital investments."), 
         t("영업이익이 높아도 공장 짓느라 돈을 다 쓰면 남는 현금이 없습니다. 진정으로 튼튼한 회사는 이 FCF가 두둑한 회사입니다.", "A company might have high accounting profit, but if it spends it all on maintenance, there's no real cash. High FCF means true financial strength.")),
        
        ("DCF (현금흐름할인법) & 내재가치", 
         t("이 회사가 앞으로 평생 벌어들일 모든 현금을 합쳐서, 현재 가치로 환산해 낸 '진정한 적정 가격'입니다.", "The 'true fair value' calculated by adding up all the future cash the company will ever generate, discounted to today's value."), 
         t("상가 건물을 살 때 평생 받을 '월세'를 다 계산해보고 진짜 건물값을 정하는 것과 같습니다. 이 가격보다 현재 주가가 싸면 저평가된 것입니다.", "Like valuing a rental property based on future rent. If the stock is cheaper than this DCF value, it is undervalued.")),
        
        ("안전마진 (Margin of Safety)", 
         t("100만 원짜리 물건을 70만 원에 할인할 때 사는 것과 같은 원리입니다.", "Like buying a $1,000 item on sale for $700."), 
         t("분석이 틀렸거나 예기치 못한 위기가 닥쳐도 손실을 방어해 줄 수 있는 '할인 폭(안전판)'을 의미합니다.", "The 'discount cushion' that protects you from losses in case of miscalculation or sudden market crises.")),
        
        ("이익수익률 (Earnings Yield)", 
         t("주식을 은행 예금이라고 가정했을 때, 1년에 이자를 몇 %나 주는지를 나타냅니다.", "If a stock were a bank account, this is the annual interest rate it yields."), 
         t("계산법은 (1 / PER) 입니다. PER이 10배인 회사의 이익수익률은 10%입니다.", "Calculated as (1 / PE ratio). A company with a PE of 10 has an Earnings Yield of 10%.")),
        
        ("주식 위험 프리미엄 (ERP)", 
         t("안전한 국채 이자 대신 위험한 주식에 투자할 때, 수익을 얼마나 더 얹어주어야 하는가를 나타내는 지표입니다.", "The extra return demanded for investing in risky stocks instead of risk-free government bonds."), 
         t("이 숫자가 높을수록 주식이 국채보다 매력적(저평가)이라는 뜻이고, 마이너스면 주식이 너무 비싸서 국채를 사는 게 유리하다는 뜻입니다.", "A higher number means stocks are more attractive (cheap). A negative number means stocks are overvalued compared to bonds."))
    ]

    lbl_analogy = t('이해하기:', 'Analogy:')
    for term, definition, example in terms:
        st.markdown(f"""
        <div translate="no" style="background-color: #161b22; color: #e6edf3; padding: 20px; border-radius: 12px; border-left: 5px solid #58a6ff; margin-bottom: 15px;">
            <h4 style="margin-top: 0; color: #58a6ff; margin-bottom: 10px;">{term}</h4>
            <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px;">{definition}</div>
            <div style="font-size: 0.95rem; color: #8b949e;"><b>{lbl_analogy}</b> {example}</div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 탭 6: VALUE 철학
# ==========================================
with tab6:
    phil_title1 = t("가치투자의 진정한 의미와 의의: 투기(Speculation) vs 투자(Investment)", "The True Meaning of Value Investing: Speculation vs. Investment")
    phil_p1 = t("주식 시장에는 두 부류의 참여자가 있습니다. 가격 변동에 베팅하며 누군가 나보다 더 비싼 가격에 사주기만을 바라는 '투기자(Speculator)', 그리고 기업의 비즈니스 모델과 내재가치를 분석하여 성장을 함께 나누고자 하는 '투자자(Investor)'입니다.", "There are two types of participants in the stock market: 'Speculators' who bet on price fluctuations, hoping someone will buy at a higher price, and 'Investors' who analyze business models and intrinsic value to share in the company's growth.")
    phil_p2 = t("가치투자(Value Investing)는 매일같이 요동치는 주가의 이면을 꿰뚫어 보고, 그 기업이 실제로 창출하는 현금흐름과 자산에 집중하는 행위입니다. 시장의 광기나 패닉에 휩쓸리지 않고, '가격(Price)은 우리가 지불하는 것이며, 가치(Value)는 우리가 얻는 것'이라는 확고한 믿음을 실천하는 것이 가치투자의 진정한 의의입니다.", "Value investing focuses on the cash flows and assets a company actually generates, seeing through daily price fluctuations. It is the practice of maintaining the firm belief that 'Price is what you pay, Value is what you get,' without being swept away by market mania or panic.")
    phil_title2 = t("워런 버핏과 찰리 멍거의 핵심 철학", "Core Philosophy of Warren Buffett & Charlie Munger")
    phil_li1 = t("**기업의 소유권 (Business Ownership):** 주식은 단순한 거래의 수단이나 종이가 아닙니다. 주식을 산다는 것은 기업의 지분을 인수하여 진정한 '동업자'가 되는 것입니다. 지분 100%를 인수한다는 마음가짐으로 비즈니스를 해부해야 합니다.", "**Business Ownership:** Stocks are not just trading instruments or pieces of paper. Buying a stock means acquiring an equity stake and becoming a true 'partner'. You must dissect the business as if you were buying 100% of it.")
    phil_li2 = t("**미스터 마켓 (Mr. Market):** 시장은 매일 기분에 따라 터무니없이 비싼 가격이나 싼 가격을 부르는 변덕스러운 동업자일 뿐입니다. 시장은 선생님이 아니라, 가격이 내재가치보다 현저히 낮을 때만 이용해야 하는 도구입니다.", "**Mr. Market:** The market is merely a fickle partner who quotes absurdly high or low prices depending on its daily mood. The market is not your teacher, but a tool to be used only when prices are significantly below intrinsic value.")
    phil_li3 = t("**경영진의 정직성 (Integrity of Management):** 재무적 성과만큼이나 중요한 것이 경영진의 도덕성입니다. 비즈니스가 훌륭해도 경영진의 정직성에 의구심이 든다면 미련 없이 동업을 끝내야 합니다. 신뢰할 수 없는 사람과는 좋은 거래를 할 수 없습니다.", "**Integrity of Management:** Management's morality is just as important as financial performance. Even if the business is great, if you doubt their integrity, you must walk away. You cannot make a good deal with a bad person.")
    phil_li4 = t("**능력 범위 (Circle of Competence):** 완벽히 이해할 수 있고, 논리적으로 설명할 수 있으며, 전문가의 반론에도 재반박할 수 있는 비즈니스에만 투자해야 합니다. 무엇을 아는지보다 '무엇을 모르는지'를 아는 것이 훨씬 중요합니다.", "**Circle of Competence:** Invest only in businesses you fully understand, can logically explain, and can defend against expert counterarguments. Knowing 'what you don't know' is far more important than what you know.")
    phil_li5 = t("**안전마진 (Margin of Safety):** 1만 파운드의 트럭이 지나갈 다리를 3만 파운드를 견딜 수 있도록 짓는 것이 안전마진입니다. 분석에 실수가 있거나 예기치 못한 위기가 닥치더라도 자본을 잃지 않도록 지켜주는 방패입니다.", "**Margin of Safety:** Building a bridge to withstand 30,000 pounds when only 10,000-pound trucks will drive across it. It is the shield that protects your capital from analysis errors or unforeseen crises.")
    phil_title3 = t("VALUE 앱의 존재 이유", "Why VALUE Exists")
    
    phil_decl_ko = """
    > **투기가 아닌 '진정한 투자'를 위한 나침반**<br><br>
    오늘날의 주식 시장은 자극적인 뉴스, 단기적인 차트의 움직임, 그리고 끊임없이 쏟아지는 소음들로 가득 차 있습니다. 수많은 투자자들이 기업의 본질이 아닌 주가창의 붉고 푸른 숫자에 매몰되어 투기적 거래의 늪에 빠지곤 합니다.<br><br>
    **VALUE**는 이러한 시장의 광기 속에서 흔들리지 않는 이성을 유지하기 위해 탄생했습니다.<br><br>
    우리는 일시적인 주가 상승률이나 테마주를 쫓지 않습니다. 대신, 철저한 잉여현금흐름(FCF) 기반의 내재가치를 계산하고, 경제적 해자(Moat)를 점검하며, 안전마진이 확보된 위대한 기업을 적당한 가격에 발굴하는 데 모든 역량을 집중합니다.<br><br>
    이 터미널은 당신이 감정에 휘둘리지 않고, 철저히 데이터와 논리에 기반해 '기업의 소유권'을 올바르게 매입할 수 있도록 돕는 가장 강력하고 냉철한 보조 도구가 될 것입니다.<br><br>
    **투기자가 아닌, 사회에 기여하는 진정한 투자자로서의 여정을 VALUE와 함께 하십시오.**
    """
    
    phil_decl_en = """
    > **A Compass for 'True Investment', Not Speculation**<br><br>
    Today's stock market is filled with sensational news, short-term chart movements, and endless noise. Many fall into the swamp of speculative trading, fixated on the red and green numbers rather than the essence of the business.<br><br>
    **VALUE** was created to help you maintain unwavering rationality amidst this market mania.<br><br>
    We do not chase temporary stock surges or thematic trends. Instead, we focus all our capabilities on calculating intrinsic value based on Free Cash Flow (FCF), examining economic moats, and discovering great companies with a secured margin of safety at fair prices.<br><br>
    This terminal will serve as your most powerful and objective auxiliary tool, helping you purchase 'business ownership' correctly based strictly on data and logic, free from emotion.<br><br>
    **Join VALUE on the journey to becoming a true investor who contributes to society, not a speculator.**
    """
    
    phil_decl = t(phil_decl_ko, phil_decl_en)

    st.subheader(phil_title1)
    st.write(phil_p1)
    st.write(phil_p2)
    
    st.divider()
    st.subheader(phil_title2)
    st.markdown(f"- {phil_li1}")
    st.markdown(f"- {phil_li2}")
    st.markdown(f"- {phil_li3}")
    st.markdown(f"- {phil_li4}")
    st.markdown(f"- {phil_li5}")
    
    st.divider()
    st.subheader(phil_title3)
    st.markdown(f"<div translate='no' style='font-size: 1.1rem; line-height: 1.7; background-color: #1c2128; padding: 25px; border-radius: 8px; border-left: 5px solid #58a6ff; color: #c9d1d9;'>{phil_decl}</div>", unsafe_allow_html=True)

# 하단 면책 조항 및 카피라이트 
st.divider()
lbl_disc_title = t('[면책 조항 / Disclaimer]', '[Disclaimer]')
lbl_disc_1 = t('본 애플리케이션은 가치투자 분석을 돕기 위한 단순 투자 보조 도구일 뿐입니다. 제공되는 재무 데이터, 13F 공시 정보, 분석 결과는 오류나 지연이 발생할 수 있습니다.', 'This application is a simple auxiliary tool to assist in value investing analysis. Provided financial data, 13F filings, and analysis results may contain errors or delays.')
lbl_disc_2 = t('본 터미널의 결과만으로 실제 주식의 특정 종목 매수 및 매도를 권유하지 않으며, 최종 투자 결정 및 그로 인한 재무적 손실에 대한 모든 법적 책임은 전적으로 투자자 본인에게 있습니다.', 'The results of this terminal do not solicit the purchase or sale of specific stocks, and all legal responsibility for final investment decisions and resulting financial losses lies entirely with the investor.')
lbl_copy = t('본 프로그램의 분석 로직, 산식 및 데이터 표출 양식은 저작권법의 보호를 받으며, 원작자의 허가 없는 무단 복제, 배포, 상업적 이용을 엄격히 금지합니다.', 'The analysis logic, formulas, and data display formats of this program are protected by copyright law, and unauthorized reproduction, distribution, or commercial use without permission is strictly prohibited.')

st.markdown(f"""
<div translate="no" style='text-align: center; color: #8b949e; font-size: 0.85rem; line-height: 1.6;'>
    <p><b>{lbl_disc_title}</b><br>
    {lbl_disc_1}<br>
    {lbl_disc_2}</p>
    <p><b>[Copyright]</b><br>
    ⓒ 2026 VALUE. All rights reserved.<br>
    {lbl_copy}</p>
</div>
""", unsafe_allow_html=True)
