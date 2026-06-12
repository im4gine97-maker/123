import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import pandas as pd
from datetime import datetime
import re

# 앱 이름 변경 및 레이아웃
st.set_page_config(page_title="AGIE", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# [1] 세션 상태 초기화 및 글로벌 유틸리티
# ==========================================
if "search_tk" not in st.session_state: st.session_state.search_tk = None
if "bookmarks" not in st.session_state: st.session_state.bookmarks = []
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "main_input" not in st.session_state: st.session_state.main_input = ""
if "suggestions" not in st.session_state: st.session_state.suggestions = []

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

# 🚀 [스마트 자동완성 검색 로직]
def trigger_scan():
    if st.session_state.get("main_input"):
        raw_q = st.session_state.main_input.strip()
        if not raw_q: return
        q = raw_q.replace(" ", "").upper()
        
        if q in tmap:
            st.session_state.search_tk = tmap[q]
            st.session_state.suggestions = []
            return
            
        matches = {}
        for k, v in tmap.items():
            if raw_q.upper() in k.upper() or raw_q in k:
                if v not in matches:
                    matches[v] = k
                else:
                    if len(k) < len(matches[v]):
                        matches[v] = k
                        
        unique_tickers = list(matches.keys())
        
        is_direct_ticker = bool(re.match(r'^\d{6}$', raw_q) or re.match(r'^[A-Za-z\-\.]+$', raw_q))

        if len(unique_tickers) == 1 and not is_direct_ticker:
            st.session_state.search_tk = unique_tickers[0]
            st.session_state.suggestions = []
        elif len(unique_tickers) > 1 and not is_direct_ticker:
            st.session_state.search_tk = None
            st.session_state.suggestions = [(tk, name) for tk, name in matches.items()]
        else:
            st.session_state.search_tk = q
            st.session_state.suggestions = []

# ==========================================
# [2] 글로벌 상수 및 고정 데이터
# ==========================================
tmap = {
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
    "NVIDIA": "NVDA", "엔비디아": "NVDA", "엔비": "NVDA", "앤비디아": "NVDA",
    "APPLE": "AAPL", "애플": "AAPL", "앱등이": "AAPL",
    "ALPHABET": "GOOGL", "구글": "GOOGL", "알파벳": "GOOGL", "GOOGLE": "GOOGL",
    "MICROSOFT": "MSFT", "마이크로소프트": "MSFT", "마소": "MSFT",
    "AMAZON": "AMZN", "아마존": "AMZN", "아마존닷컴": "AMZN",
    "BROADCOM": "AVGO", "브로드컴": "AVGO",
    "TESLA": "TSLA", "테슬라": "TSLA", "테슬": "TSLA",
    "META": "META", "메타": "META", "페이스북": "META", "METAPLATFORMS": "META",
    "MICRON": "MU", "마이크론": "MU", "마이크론테크놀로지": "MU",
    "BERKSHIREHATHAWAY": "BRK-B", "버크셔해서웨이": "BRK-B", "버크셔": "BRK-B", "버핏": "BRK-B",
    "ELILILLY": "LLY", "일라이릴리": "LLY", "릴리": "LLY",
    "WALMART": "WMT", "월마트": "WMT",
    "AMD": "AMD", "에이엠디": "AMD",
    "JPMORGAN": "JPM", "제이피모건": "JPM", "JP모건": "JPM", "제이피모간": "JPM",
    "ORACLE": "ORCL", "오라클": "ORCL",
    "VISA": "V", "비자": "V", "비자카드": "V",
    "EXXONMOBIL": "XOM", "엑손모빌": "XOM", "엑손": "XOM",
    "INTEL": "INTC", "인텔": "INTC",
    "JOHNSON&JOHNSON": "JNJ", "존슨앤존슨": "JNJ", "J&J": "JNJ", "존슨앤드존슨": "JNJ",
    "CISCO": "CSCO", "시스코": "CSCO",
    "MASTERCARD": "MA", "마스터카드": "MA",
    "COSTCO": "COST", "코스트코": "COST", "코코": "COST",
    "CATERPILLAR": "CAT", "캐터필러": "CAT",
    "LAMRESEARCH": "LRCX", "램리서치": "LRCX",
    "ABBVIE": "ABBV", "애브비": "ABBV",
    "PALANTIR": "PLTR", "팔란티어": "PLTR", "팔란": "PLTR",
    "BANKOFAMERICA": "BAC", "뱅크오브아메리카": "BAC", "뱅아": "BAC",
    "CHEVRON": "CVX", "쉐브론": "CVX", "셰브론": "CVX",
    "NETFLIX": "NFLX", "넷플릭스": "NFLX", "넷플": "NFLX",
    "APPLIEDMATERIALS": "AMAT", "어플라이드머티리얼즈": "AMAT", "어플라이드": "AMAT",
    "COCA-COLA": "KO", "코카콜라": "KO", "코카": "KO", "콜라": "KO", "COCACOLA": "KO"
}

fallback_13f_data = {
    "HC": [{"티커": "GOOGL", "기업명": "Alphabet Inc.", "비중(%)": 22.84}, {"티커": "BRK-B", "기업명": "Berkshire Hathaway Inc.", "비중(%)": 13.43}],
    "BRK": [{"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 21.99}, {"티커": "AXP", "기업명": "American Express Co.", "비중(%)": 17.43}, {"티커": "KO", "기업명": "Coca-Cola Co.", "비중(%)": 11.56}, {"티커": "BAC", "기업명": "Bank of America Corp.", "비중(%)": 9.52}, {"티커": "CVX", "기업명": "Chevron Corp.", "비중(%)": 6.64}],
    "BAU": [{"티커": "AMZN", "기업명": "Amazon.com, Inc.", "비중(%)": 12.69}, {"티커": "QSR", "기업명": "Restaurant Brands", "비중(%)": 11.67}]
}

us_top30 = [{"순위": 1, "티커": "NVDA", "기업명": "NVIDIA", "시가총액": "$5.11T"}, {"순위": 2, "티커": "AAPL", "기업명": "Apple", "시가총액": "$4.58T"}, {"순위": 3, "티커": "GOOGL", "기업명": "Alphabet", "시가총액": "$4.56T"}]
kr_top30 = [{"순위": 1, "티커": "005930", "기업명": "삼성전자", "시가총액": "1,794조 원"}, {"순위": 2, "티커": "000660", "기업명": "SK하이닉스", "시가총액": "1,662조 원"}]

# ==========================================
# [3] 데이터 가져오기 엔진
# ==========================================
@st.cache_data(ttl=60) 
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
            try:
                last_p = getattr(stk.fast_info, 'last_price', None)
                if last_p is None: last_p = stk.fast_info.get('lastPrice') if isinstance(stk.fast_info, dict) else stk.fast_info['lastPrice']
                prev_p = getattr(stk.fast_info, 'previous_close', None)
                if prev_p is None: prev_p = stk.fast_info.get('previousClose') if isinstance(stk.fast_info, dict) else stk.fast_info['previousClose']
                last_p, prev_p = safe_float(last_p), safe_float(prev_p)
                if last_p == 0.0 or prev_p == 0.0: raise Exception("fallback")
            except:
                hist = stk.history(period="7d")
                if hist is not None and len(hist.dropna()) >= 2:
                    last_p, prev_p = safe_float(hist['Close'].iloc[-1]), safe_float(hist['Close'].iloc[-2])
                else: last_p, prev_p = 0.0, 0.0
            change = last_p - prev_p if prev_p != 0 else 0.0
            pct = (change / prev_p) * 100 if prev_p != 0 else 0.0
            res[name] = {"p": last_p, "c": change, "pct": pct}
        except: res[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
            
    try: res["SPY_PE"] = safe_float(yf.Ticker("SPY").info.get("forwardPE", 22.0), 22.0)
    except: res["SPY_PE"] = 22.0
    try: res["QQQ_PE"] = safe_float(yf.Ticker("QQQ").info.get("forwardPE", 30.0), 30.0)
    except: res["QQQ_PE"] = 30.0
    return res

def get_13f_portfolio(guru_code): return fallback_13f_data.get(guru_code, [])

def fetch_naver_finance_news(cd):
    url = f"https://finance.naver.com/item/news_news.naver?code={cd}"
    news_list = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        r.encoding = 'euc-kr' 
        soup = BeautifulSoup(r.text, 'html.parser')
        titles = soup.select('td.title a')
        for a in titles[:3]:
            title_text = a.text.strip()
            if not title_text: continue
            href = a.get('href', '')
            link = "https://finance.naver.com" + href if href.startswith('/') else f"https://finance.naver.com/item/news.naver?code={cd}"
            news_list.append({"title": title_text, "link": link, "publisher": "네이버증권"})
    except: pass
    return news_list

def fetch_global_news(tk):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={tk}&region=US&lang=en-US"
    news_list = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.find_all('item')[:3]:
            t_tag = item.find('title')
            l_tag = item.find('link')
            link_url = l_tag.text.strip() if l_tag and l_tag.text.strip() else (str(l_tag.next_sibling).strip() if l_tag and l_tag.next_sibling else '#')
            if t_tag and t_tag.text:
                news_list.append({"title": t_tag.text.strip(), "link": link_url, "publisher": "Yahoo Finance"})
    except: pass
    return news_list

def fetch_governance_criticism(tk, cd, ceo_name):
    tk_clean = str(tk).strip().upper().replace('.B', '-B').replace('.A', '-A')
    cd_clean = str(cd).strip()
    db = {
        "NVDA": "젠슨 황 (Jensen Huang): 비전을 현실로 만드는 강력한 실행력과 기술적 해자를 구축한 검증된 경영자입니다.\n리스크: 특정 리더(키맨)에 대한 절대적 의존도(단일 실패 지점) 및 빅테크 고객사들의 자체 칩 개발 독립 리스크. (이건 확인이 필요한 부분입니다)",
        "AAPL": "팀 쿡 (Tim Cook): 탁월한 공급망 관리와 대규모 자사주 매입으로 주주 환원에 매우 충실합니다.\n리스크: 혁신 사이클 정체 및 중국 등 지정학적 갈등에 노출된 벤더 공급망 마찰 위험. (이건 확인이 필요한 부분입니다)",
        "005930": "삼성전자 (이재용/전영현 등): 반도체 부문 수장 교체 등 쇄신을 시도하고 있으나 조직 내부의 관료화가 지적됩니다.\n리스크: AI 메모리(HBM) 및 파운드리 기술 격차 회복 지연, 오너 사법 리스크 및 창사 이래 첫 노조 파업 지속. (이건 확인이 필요한 부분입니다)",
    }
    for key, text in db.items():
        if key in tk_clean or (len(cd_clean) == 6 and key == cd_clean): return text
    return f"{ceo_name} 경영진 - 공공 기록 스크리닝 결과, 중범죄 이력은 두드러지지 않으나 가치투자 관점에서 자본 배분 오류 및 노사 갈등 여부는 투자 전 교차 검증이 필요합니다. (이건 확인이 필요한 부분입니다)"

def get_data(tk):
    try:
        if not tk: return None, None, {}, False
        tk = str(tk).strip()
        
        if tk.isdigit() and len(tk) == 6:
            test_tk = tk + ".KS"
            try:
                _ = yf.Ticker(test_tk).fast_info['lastPrice']
                tk = test_tk 
            except: tk = tk + ".KQ"

        if "." not in tk: tk = tk.upper()
        kr = tk.endswith('.KS') or tk.endswith('.KQ')
        cd = tk.split('.')[0] if kr else tk
        
        stk = yf.Ticker(tk)
        p, i = None, {}
        
        for _ in range(3):
            try:
                p_val = getattr(stk.fast_info, 'last_price', None)
                if p_val is None: p_val = stk.fast_info.get('lastPrice') if isinstance(stk.fast_info, dict) else stk.fast_info['lastPrice']
                p = safe_float(p_val)
                if p > 0: break
            except: time.sleep(0.5)
        
        try:
            i = stk.info
            if not isinstance(i, dict): i = {}
        except: i = {}
            
        # 🚀 [강화된 Finviz & Yahoo Profile 스크래핑 폴백]
        if not kr and (not i or 'forwardPE' not in i or not i.get('forwardPE')):
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            # 1. Finviz 데이터 구출 (Fwd PE, ROE, Consensus)
            try:
                fv_url = f"https://finviz.com/quote.ashx?t={cd}"
                fv_r = requests.get(fv_url, headers=headers, timeout=5)
                if fv_r.status_code == 200:
                    fv_s = BeautifulSoup(fv_r.text, 'html.parser')
                    
                    def get_fv(label):
                        elem = fv_s.find(string=label)
                        if elem:
                            val = elem.find_next('td').text.strip()
                            if val != '-': return val
                        return None

                    fpe = get_fv("Forward P/E")
                    if fpe: i['forwardPE'] = safe_float(fpe)
                    
                    pe = get_fv("P/E")
                    if pe and ('trailingPE' not in i or not i.get('trailingPE')): 
                        i['trailingPE'] = safe_float(pe)
                        
                    # 💡 누락된 ROE 완벽 복구
                    roe_str = get_fv("ROE")
                    if roe_str and ('returnOnEquity' not in i or not i.get('returnOnEquity')):
                        try: i['returnOnEquity'] = float(roe_str.replace('%', '')) / 100
                        except: pass
                    
                    # 💡 비즈니스 요약과 섞이지 않게 컨센서스는 별도 필드로 보관
                    eps_nxt = get_fv("EPS next Y")
                    if eps_nxt: 
                        i['finviz_eps_next'] = eps_nxt
            except: pass

            # 2. Yahoo 파이낸스 직접 스크래핑 강화 (비즈니스 요약 및 경영진)
            try:
                yh_url = f"https://finance.yahoo.com/quote/{cd}/profile"
                yh_r = requests.get(yh_url, headers=headers, timeout=5)
                if yh_r.status_code == 200:
                    yh_s = BeautifulSoup(yh_r.text, 'html.parser')
                    
                    # 비즈니스 요약 찾기 (최신 DOM 대응)
                    desc = yh_s.find('section', {'data-testid': 'description'})
                    if not desc: desc = yh_s.select_one('#Col1-0-Profile-Proxy section p')
                    if desc and 'longBusinessSummary' not in i:
                        i['longBusinessSummary'] = desc.text.strip()
                    
                    # 경영진(CEO) 찾기 (테이블 또는 특정 텍스트 주변 검색)
                    exec_table = yh_s.find('table')
                    if exec_table:
                        ceo_name = exec_table.find('tbody').find('tr').find('td').text.strip()
                        i['companyOfficers'] = [{'name': ceo_name}]
                    else:
                        ceo_elem = yh_s.find(string=re.compile("Chief Executive", re.IGNORECASE))
                        if ceo_elem:
                            parent_row = ceo_elem.find_parent('tr')
                            if parent_row:
                                i['companyOfficers'] = [{'name': parent_row.find('td').text.strip()}]
            except: pass

        if tk == "005380.KS": p = 480000.0
        
        # 한국 주식 크롤링
        if kr and p:
            try:
                url = f"https://finance.naver.com/item/main.naver?code={cd}"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                s = BeautifulSoup(r.text, 'html.parser')
                
                t_price = s.select_one('.no_today .blind')
                if t_price:
                    live_p = safe_float(t_price.text.replace(',', ''))
                    if live_p > 0: p = live_p
                    
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
            
        # 재무제표 직접 역산 로직
        if p and (not i or 'trailingPE' not in i or i['trailingPE'] == 0.0):
            try:
                inc, bs = stk.income_stmt, stk.balance_sheet
                sh_count = safe_float(stk.fast_info.get('shares', getattr(stk.fast_info, 'shares', 0)))
                if sh_count == 0: sh_count = safe_float(i.get('sharesOutstanding', 0))
                    
                if inc is not None and not inc.empty and bs is not None and not bs.empty:
                    eq = safe_float(bs.loc['Stockholders Equity'].iloc[0]) if 'Stockholders Equity' in bs.index else 0
                    net_inc = safe_float(inc.loc['Net Income'].iloc[0]) if 'Net Income' in inc.index else 0
                    t_eps = safe_float(inc.loc['Basic EPS'].iloc[0]) if 'Basic EPS' in inc.index else (net_inc/sh_count if sh_count > 0 else 0)
                    
                    if t_eps > 0: i['trailingPE'] = p / t_eps
                    if 'trailingEps' not in i or not i['trailingEps']: i['trailingEps'] = t_eps
                    if sh_count > 0 and eq > 0: i['priceToBook'] = p / (eq / sh_count)
                    if eq > 0 and ('returnOnEquity' not in i or not i['returnOnEquity']): i['returnOnEquity'] = net_inc / eq
                    if sh_count > 0: i['sharesOutstanding'] = sh_count
            except: pass

        if 'sharesOutstanding' not in i or not i['sharesOutstanding'] or i['sharesOutstanding'] == 0:
            try:
                sh_count = safe_float(stk.fast_info.get('shares', getattr(stk.fast_info, 'shares', 0)))
                if sh_count > 0: i['sharesOutstanding'] = sh_count
            except: pass

        return stk, p, i, kr
    except Exception as e: return None, None, {}, False

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
        if sh == 0:
            try: sh = safe_float(stk.fast_info.get('shares', getattr(stk.fast_info, 'shares', 0)))
            except: pass
            
        g, data_len = 0.05, 0
        if fcf_s is not None and len(fcf_s) >= 2:
            c, o = safe_float(fcf_s.iloc[0]), safe_float(fcf_s.iloc[-1])
            data_len = len(fcf_s)
            if c > 0 and o > 0: g = (c / o) ** (1 / (data_len - 1)) - 1
        else:
            eg = safe_float(i.get('earningsGrowth'))
            if eg != 0.0: g = eg
            data_len = 1
        return fcf, sh, max(0.02, min(g, 0.15)), data_len
    except: return None, None, 0.05, 0

def calc_custom_dcf(fcf, sh, p, ty, g, is_financial=False):
    if is_financial: return 0, 0, t("금융/보험주 평가 제외", "N/A for Financials")
    if not fcf or fcf <= 0: return 0, 0, t("FCF 적자", "Negative FCF")
    if not sh or sh <= 0: return 0, 0, t("주식수 누락", "Missing Shares")
    try:
        dr = max(ty / 100, 0.09)
        cv = fcf
        fut = [cv * ((1 + g)**y) / ((1 + dr)**y) for y in range(1, 11)]
        tv = (cv * ((1 + g)**10) * 1.02) / (dr - 0.02)
        iv = (sum(fut) + (tv / ((1 + dr)**10))) / sh
        return iv, ((iv - p) / iv) * 100, None
    except: return 0, 0, t("연산 에러", "Calc Error")

def get_implied_g(fcf, sh, p, ty):
    if not fcf or fcf <= 0 or not sh or sh <= 0 or not p or p <= 0: return None
    low, high, dr = -0.5, 1.0, max(ty / 100, 0.09)
    for _ in range(40):
        mid = (low + high) / 2
        cv, fut_sum = fcf, 0
        for y in range(1, 11):
            cv *= (1 + mid)
            fut_sum += cv / ((1 + dr) ** y)
        iv = (fut_sum + ((cv * 1.02) / (dr - 0.02) / ((1 + dr) ** 10))) / sh
        if iv > p: high = mid
        else: low = mid
    return (low + high) / 2

def get_real_roic(stk, i):
    try:
        if i.get('returnOnCapitalEmployed'): return safe_float(i['returnOnCapitalEmployed']) * 100
        if stk is None: return None
        inc, bs = stk.income_stmt, stk.balance_sheet
        if inc is not None and not inc.empty and bs is not None and not bs.empty:
            ebit = safe_float(inc.loc['EBIT'].iloc[0]) if 'EBIT' in inc.index else (safe_float(inc.loc['Operating Income'].iloc[0]) if 'Operating Income' in inc.index else 0)
            pretax = safe_float(inc.loc['Pretax Income'].iloc[0]) if 'Pretax Income' in inc.index else 0
            tax = safe_float(inc.loc['Tax Provision'].iloc[0]) if 'Tax Provision' in inc.index else 0
            nopat = ebit * (1 - (tax / pretax if pretax > 0 else 0.25))
            invested_capital = (safe_float(bs.loc['Total Debt'].iloc[0]) if 'Total Debt' in bs.index else 0) + (safe_float(bs.loc['Stockholders Equity'].iloc[0]) if 'Stockholders Equity' in bs.index else 0) - (safe_float(bs.loc['Cash And Cash Equivalents'].iloc[0]) if 'Cash And Cash Equivalents' in bs.index else 0)
            if invested_capital > 0: return (nopat / invested_capital) * 100
    except: pass
    return None

def analyze_trends(stk):
    eps_trend = f"<span style='color:#8892b0'>{t('데이터 부족', 'Insufficient Data')}</span>"
    bps_trend = f"<span style='color:#8892b0'>{t('데이터 부족', 'Insufficient Data')}</span>"
    if stk is None: return eps_trend, bps_trend
    try:
        inc, bs = stk.income_stmt, stk.balance_sheet
        if inc is not None and not inc.empty:
            target_col = 'Basic EPS' if 'Basic EPS' in inc.index else ('Diluted EPS' if 'Diluted EPS' in inc.index else None)
            if target_col:
                eps_vals = inc.loc[target_col].dropna().values[:4][::-1] 
                if len(eps_vals) >= 3:
                    if all(eps_vals[i] <= eps_vals[i+1] for i in range(len(eps_vals)-1)) and eps_vals[0] < eps_vals[-1]: 
                        eps_trend = f"<span class='good'>{t('[합격] 4년 지속 상승', '[Pass] 4Y Consistent Up')}</span>"
                    else: eps_trend = f"<span class='highlight'>{t('[주의] 변동/하락', '[Warning] Fluctuating')}</span>"
        if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index:
            eq_vals = bs.loc['Stockholders Equity'].dropna().values[:4][::-1]
            if len(eq_vals) >= 3:
                if all(eq_vals[i] <= eq_vals[i+1] for i in range(len(eq_vals)-1)) and eq_vals[0] < eq_vals[-1]: 
                    bps_trend = f"<span class='good'>{t('[합격] 4년 자본 상승', '[Pass] 4Y Consistent Up')}</span>"
                else: bps_trend = f"<span class='highlight'>{t('[주의] 자본 변동', '[Warning] Fluctuating')}</span>"
    except: pass
    return eps_trend, bps_trend

def analyze_rnd_trend(stk, base_fcf, is_financial):
    if is_financial: return f"<span style='color:#8892b0'>{t('금융/보험주 제외', 'N/A (Financial)')}</span>"
    if stk is None: return f"<span style='color:#8892b0'>{t('데이터 부족', 'No Data')}</span>"
    try:
        inc = stk.income_stmt
        if inc is not None and not inc.empty and 'Research And Development' in inc.index:
            rnd_vals = inc.loc['Research And Development'].dropna().values[:4][::-1]
            if len(rnd_vals) > 0 and safe_float(rnd_vals[-1]) > 0:
                if base_fcf and base_fcf > 0:
                    ratio = (safe_float(rnd_vals[-1]) / base_fcf) * 100
                    r_eval = f"<span class='highlight'>{t('[지출 과다]', '[High]')}</span>" if ratio >= 50 else (f"<span class='good'>{t('[적정 수준]', '[Optimal]')}</span>" if ratio >= 15 else f"<span style='color:#fdcb6e;'>{t('[지출 적음]', '[Low]')}</span>")
                    return f"{r_eval} <span style='font-size:0.95em;'>➔ FCF의 <b>{ratio:.1f}%</b> 지출</span>"
                elif base_fcf and base_fcf <= 0: return f"<span class='highlight'>{t('FCF 적자로 계산 불가', 'N/A (Negative FCF)')}</span>"
            else: return f"<span style='color:#8892b0'>{t('R&D 지출 없음', 'No R&D')}</span>"
    except: pass
    return f"<span style='color:#8892b0'>{t('데이터 부족', 'No Data')}</span>"

def get_comprehensive_investment_opinion(mos, pmos, roe, roic, erp, final_g, ceo_text, is_financial=False, pbr=0.0):
    score = sum([
        20 if any(k in ceo_text for k in ["역사상 가장 신뢰받는", "탁월한 자본 배분"]) else (10 if "검증된 경영자" in ceo_text else 5),
        -25 if any(k in ceo_text for k in ["구속", "사법 리스크"]) else 0,
        -15 if any(k in ceo_text for k in ["주주가치 훼손", "물적분할"]) else 0,
        25 if pmos >= 30 else (15 if pmos >= 15 else (5 if pmos >= 5 else (-25 if pmos < -20 else (-15 if pmos < -10 else (-5 if pmos < 0 else 0))))),
        25 if erp >= 4 else (15 if erp >= 2 else (5 if erp >= 1 else (-25 if erp < -1 else (-15 if erp < 0 else (-5 if erp < 1 else 0))))),
        25 if final_g >= 0.15 else (15 if final_g >= 0.08 else (5 if final_g >= 0.05 else (-25 if final_g < 0.0 else (-15 if final_g < 0.03 else (-5 if final_g < 0.05 else 0)))))
    ])
    
    if is_financial:
        score += 25 if roe >= 15 else (15 if roe >= 10 else (5 if roe >= 8 else (-25 if roe < 5 else -15)))
        score += 25 if (pbr > 0 and pbr <= 0.6) else (15 if pbr <= 0.9 else (5 if pbr <= 1.0 else (-25 if pbr >= 1.5 else (-15 if pbr >= 1.2 else -5))))
    else:
        score += 15 if roe >= 20 else (10 if roe >= 15 else (5 if roe >= 10 else (-15 if roe < 5 else -10)))
        score += 15 if roic and roic >= 15 else (10 if roic and roic >= 10 else (5 if roic and roic >= 7 else (-15 if roic and roic < 3 else -10)))
        score += 25 if mos >= 30 else (15 if mos >= 15 else (5 if mos >= 5 else (-25 if mos < -20 else (-15 if mos < -10 else -5))))

    is_cyclical = any(k in ceo_text for k in ["사이클", "경기 민감", "유가", "철강", "조선"])
    if is_cyclical: score -= 15

    if score >= 90: return t("적극적 할인 (Deep Discount)", "Deep Discount"), "#2ecc71", t("버핏급 초저평가 기회입니다.", "Buffett-level deep discount.")
    elif score >= 50: return t("할인 (Discount)", "Discount"), "#00b894", t("안전마진이 확보된 우량한 할인 구간입니다.", "Solid discount with margin of safety.")
    elif score >= 15: return t("약간 할인 (Slight Discount)", "Slight Discount"), "#74b9ff", t("펀더멘털 대비 약간 할인된 합리적인 구간입니다.", "Reasonable entry point at slight discount.")
    elif score >= -15: return t("적정 가치 (Fair Value)", "Fair Value"), "#fdcb6e", t("성장성 대비 적당한 가격(Fair Price)입니다.", "Fair price given business quality.")
    elif score >= -45: return t("약간 할증 (Slight Premium)", "Slight Premium"), "#ff7675", t("시장의 기대감이 선반영되어 가격에 약간의 할증이 붙어 있습니다.", "Trading at slight premium. Pullback recommended.")
    elif score >= -75: return t("할증 (Premium)", "Premium"), "#e17055", t("시장 기대감이 과도하게 반영되어 비싸게 거래 중입니다.", "Trading at a premium. Price reflects excessive expectations.")
    else: return t("과도한 할증 (Excessive Premium)", "Excessive Premium"), "#d63031", t("심각한 훼손이나 거품이 낀 매우 위험한 구간입니다.", "Dangerous territory with valuation bubble.")

def get_market_op_simple(erp):
    if erp > 3.0: return t("적극적 할인 (역사적 저평가)", "Deep Discount"), "#2ecc71"
    elif erp > 1.0: return t("할인 (안전마진 존재)", "Discount"), "#74b9ff"
    elif erp > -1.0: return t("적정 가치 (채권과 주식 매력도 유사)", "Fair Value"), "#fdcb6e"
    else: return t("과도한 할증 경고 (채권 매력도 압도적)", "Excessive Premium"), "#ff7675"

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
    for prefix in ["Mr. ", "Ms. ", "Mrs. ", "Dr. "]:
        if name_str.startswith(prefix) or name_str.startswith(prefix.strip()): name_str = name_str[len(prefix):]
    if is_ko:
        k_name = GoogleTranslator(source='en', target='ko').translate(name_str[:100]) if name_str else '누락'
        for s in [" 씨", "씨", " 님", "님", " 선생님", "선생님", " 박사", "박사"]:
            if k_name.endswith(s): k_name = k_name[:-len(s)].strip(); break
        return k_name
    return name_str

def get_safe_macro(key, is_currency=False, is_rate=False):
    data = macro_data.get(key, {"p": 0.0, "c": 0.0, "pct": 0.0})
    p, c, pct = safe_float(data.get("p")), safe_float(data.get("c")), safe_float(data.get("pct"))
    return (f"${p:,.2f}" if is_currency else (f"{p:.3f}%" if is_rate else f"{p:,.2f}")), c, pct

# ==========================================
# [4] 메인 UI 렌더링
# ==========================================
macro_data = fetch_macro_realtime_v6()

with st.sidebar:
    if st.session_state.lang == "ko":
        if st.button("English", use_container_width=True): st.session_state.lang = "en"; st.rerun()
    else:
        if st.button("Korean", use_container_width=True): st.session_state.lang = "ko"; st.rerun()
            
    is_ko = st.session_state.lang == "ko"
        
    st.divider()
    st.header(t("내 서재", "My Library"))
    st.subheader(t("관심 종목 (즐겨찾기)", "Bookmarks"))
    if not st.session_state.bookmarks: st.caption(t("즐겨찾기한 종목이 없습니다.", "No bookmarked tickers yet."))
    else:
        for b_tk in st.session_state.bookmarks:
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(b_tk, key=f"bk_{b_tk}", use_container_width=True): st.session_state.search_tk = b_tk; st.rerun()
            with c2:
                if st.button("X", key=f"del_bk_{b_tk}"): st.session_state.bookmarks.remove(b_tk); st.rerun()
    st.divider()
    st.header(t("고객 센터", "Customer Center"))
    st.markdown(f"<div style='font-size: 0.95rem; font-weight: bold;'>csjwo154515@naver.com</div>", unsafe_allow_html=True)

st.markdown("""
<meta name="google" content="notranslate">
<style>
.main { background-color: var(--background-color); color: var(--text-color); font-family: 'Pretendard', sans-serif; }
h1, h2, h3 { color: #A0C4FF; font-weight: 800; letter-spacing: -0.5px; }
.stTabs [data-baseweb="tab-list"] { gap: 15px; border-bottom: 2px solid rgba(255,255,255,0.05); padding-bottom: 5px; }
.stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: 600; color: #8892b0; background: transparent; transition: 0.2s; padding: 10px 15px; border-radius: 12px; }
.stTabs [aria-selected="true"] { color: #A0C4FF !important; background: rgba(160, 196, 255, 0.1) !important; border-bottom: none !important; }
.good { color: #2ecc71; font-weight: 700; }
.highlight { color: #ff7675; font-weight: 700; }
.guru-quote { font-style: normal; background: linear-gradient(135deg, rgba(160,196,255,0.1), rgba(255,198,255,0.1)); padding: 20px; border-radius: 16px; border-left: 5px solid #A0C4FF; margin-bottom: 15px; line-height: 1.6; }
.macro-ticker::-webkit-scrollbar { display: none; }
div[data-testid="stDataFrame"] canvas { touch-action: auto !important; }
div[data-testid="stDataFrame"] { overflow-x: auto !important; border-radius: 12px; overflow: hidden; }
div[data-testid="stArrowVegaLiteChart"] canvas { pointer-events: none !important; }
#vg-tooltip-element, .vg-tooltip, [data-testid="stElementToolbar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div translate="no" style="padding-top: 10px; padding-bottom: 15px; text-align: center;">
    <span style="font-size: 3.5rem; font-weight: 900; background: linear-gradient(45deg, #A0C4FF, #FFC6FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 3px;">AGIE</span>
    <div style="font-size: 1rem; color: #8892b0; margin-top: -10px; font-weight: 600;">똑똑하고 친절한 나만의 AI 가치투자 비서</div>
</div>
""", unsafe_allow_html=True)

k_p, k_c, k_pct = get_safe_macro("KOSPI")
kq_p, kq_c, kq_pct = get_safe_macro("KOSDAQ")
sp_p, sp_c, sp_pct = get_safe_macro("S&P 500")
nd_p, nd_c, nd_pct = get_safe_macro("Nasdaq 100")
nf_p, nf_c, nf_pct = get_safe_macro("Nasdaq Futures")
krw_p, krw_c, krw_pct = get_safe_macro("USD/KRW")
wti_p, wti_c, wti_pct = get_safe_macro("WTI Crude", is_currency=True)
tnx_p, tnx_c, tnx_pct = get_safe_macro("10Y Treasury", is_rate=True)

macro_items = [
    (t("KOSPI", "KOSPI"), k_p, k_pct, "%"), (t("KOSDAQ", "KOSDAQ"), kq_p, kq_pct, "%"),
    (t("S&P 500", "S&P 500"), sp_p, sp_pct, "%"), (t("Nasdaq 100", "Nasdaq 100"), nd_p, nd_pct, "%"),
    (t("NQ 선물", "Nasdaq Fut"), nf_p, nf_pct, "%"), (t("환율(KRW/USD)", "USD/KRW"), krw_p, krw_pct, "%"),
    (t("WTI 원유", "WTI Crude"), wti_p, wti_pct, "%"), (t("10년물 국채", "10Y Treasury"), tnx_p, tnx_c, " bp")
]

macro_html = "<div class='macro-ticker' translate='no' style='display: flex; overflow-x: auto; gap: 12px; padding: 10px 0 20px 0;'>"
for name, val, chg, unit in macro_items:
    color = "#2ecc71" if chg > 0 else ("#ff7675" if chg < 0 else "#8892b0")
    sign = "+" if chg > 0 else ""
    chg_str = f"{sign}{chg:.3f}{unit}" if unit == " bp" else f"{sign}{chg:.2f}{unit}"
    macro_html += f"<div style='flex: 0 0 auto; background: rgba(255,255,255,0.03); padding: 18px 22px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); min-width: 145px; text-align: center;'><div style='font-size: 0.85rem; color: #8892b0; margin-bottom: 8px; font-weight: 600;'>{name}</div><div style='font-size: 1.4rem; font-weight: 800; color: var(--text-color);'>{val}</div><div style='font-size: 0.95rem; font-weight: bold; color: {color}; margin-top: 5px;'>{chg_str}</div></div>"
macro_html += "</div>"
st.markdown(macro_html, unsafe_allow_html=True)

spy_pe, qqq_pe = safe_float(macro_data.get("SPY_PE", 22.0), 22.0), safe_float(macro_data.get("QQQ_PE", 30.0), 30.0)
tnx_val = safe_float(macro_data.get("10Y Treasury", {}).get("p"), 4.4)
if tnx_val == 0.0: tnx_val = 4.4
spy_ey, qqq_ey = (1 / spy_pe * 100) if spy_pe > 0 else 0, (1 / qqq_pe * 100) if qqq_pe > 0 else 0
spy_erp, qqq_erp = spy_ey - tnx_val, qqq_ey - tnx_val
spy_op, spy_col = get_market_op_simple(spy_erp)
qqq_op, qqq_col = get_market_op_simple(qqq_erp)

with st.expander(t("📌 현재 미 증시 밸류에이션 매력도 분석", "📌 Current US Market Valuation")):
    c_m1, c_m2 = st.columns(2)
    with c_m1: st.markdown(f"<div translate='no' style='background: rgba(255,255,255,0.03); padding:20px; border-radius:16px; border-top: 4px solid {spy_col};'><h4 style='margin-top:0; color:#A0C4FF;'>S&P 500</h4><p>- Fwd PER: <b>{spy_pe:.1f}배</b></p><p>- 예상 이익수익률(EY): <b>{spy_ey:.2f}%</b></p><p>- 10년물 국채: <b>{tnx_val:.2f}%</b></p><p>- 주식 위험 프리미엄(ERP): <b style='color:{spy_col}'>{spy_erp:.2f}%</b></p><hr><b>[시장 의견] <span style='color:{spy_col}'>{spy_op}</span></b></div>", unsafe_allow_html=True)
    with c_m2: st.markdown(f"<div translate='no' style='background: rgba(255,255,255,0.03); padding:20px; border-radius:16px; border-top: 4px solid {qqq_col};'><h4 style='margin-top:0; color:#A0C4FF;'>Nasdaq 100</h4><p>- Fwd PER: <b>{qqq_pe:.1f}배</b></p><p>- 예상 이익수익률(EY): <b>{qqq_ey:.2f}%</b></p><p>- 10년물 국채: <b>{tnx_val:.2f}%</b></p><p>- 주식 위험 프리미엄(ERP): <b style='color:{qqq_col}'>{qqq_erp:.2f}%</b></p><hr><b>[시장 의견] <span style='color:{qqq_col}'>{qqq_op}</span></b></div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:25px;'></div>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4, tab5 = st.tabs([t("개별 기업 가치분석", "Company Value Analysis"), t("유명 가치투자자 13F", "Guru 13F"), t("시가총액 랭킹", "Market Cap Top 30"), t("주식 용어 사전", "Glossary"), t("AGIE 철학", "Philosophy")])

with tab1:
    col_input, col_btn = st.columns([4, 1])
    with col_input: ui = st.text_input(t("종목명 또는 티커 입력:", "Enter Stock:"), key="main_input", on_change=trigger_scan, label_visibility="collapsed")
    with col_btn:
        if st.button(t("가치 분석 스캔", "Scan"), use_container_width=True, type="primary"): trigger_scan(); st.rerun() 

    if st.session_state.suggestions:
        sug_cols = st.columns(4)
        for idx, (s_tk, s_name) in enumerate(st.session_state.suggestions[:12]):
            with sug_cols[idx % 4]:
                if st.button(f"{s_name}", key=f"sug_{s_tk}", use_container_width=True): st.session_state.search_tk = s_tk; st.session_state.suggestions = []; st.rerun()

    elif st.session_state.search_tk:
        tk = st.session_state.search_tk
        st_container = st.empty()
        with st_container.container():
            st.toast(t("데이터 연동 중...", "Fetching data..."), icon="⏳")
            stk, p, i, kr = get_data(tk)
            
            if p:
                ty = safe_float(macro_data["10Y Treasury"]["p"], 4.4)
                if ty == 0.0: ty = 4.4
                if i is None: i = {}
                is_financial = i.get('industry') in ['Banks - Regional', 'Banks - Diversified', 'Insurance - Specialists', 'Insurance - Life', 'Insurance - Property & Casualty', 'Insurance Brokers', 'Insurance - Diversified']
                
                c_title, c_star = st.columns([4, 1])
                with c_title: st.success(f"{i.get('shortName', tk)} ({tk}) {t('분석 완료', 'Complete')}")
                with c_star:
                    if st.button(t("즐겨찾기 관리", "Toggle Bookmark"), use_container_width=True):
                        if tk in st.session_state.bookmarks: st.session_state.bookmarks.remove(tk)
                        else: st.session_state.bookmarks.append(tk)
                        st.rerun() 
                
                off, ceo_raw = i.get('companyOfficers', []), '누락'
                if isinstance(off, list) and len(off) > 0: ceo_raw = off[0].get('name', '누락') if isinstance(off[0], dict) else str(off[0])
                elif isinstance(off, dict): ceo_raw = off.get('name', '누락')
                ceo_cleaned = clean_ceo_name(ceo_raw)
                criticism_text = fetch_governance_criticism(tk, tk.split('.')[0] if kr else tk, ceo_cleaned)

                t_pe, f_pe = safe_float(i.get('trailingPE')), safe_float(i.get('forwardPE'))
                pbr = safe_float(i.get('priceToBook'))
                if pbr == 0.0 and safe_float(i.get('bookValue')) > 0: pbr = p / safe_float(i.get('bookValue'))
                
                # 💡 여기서 복구된 ROE 변수를 안전하게 가져옵니다.
                roe = safe_float(i.get('returnOnEquity')) * 100
                real_roic = get_real_roic(stk, i)
                roic_str = t("금융/보험주 제외", "N/A (Financial)") if is_financial else (f"{real_roic:.2f}%" if real_roic is not None else t("데이터 부족", "N/A"))
                
                a_pe = safe_float(i.get('fiveYearAvgPE'))
                if a_pe == 0.0: a_pe = t_pe * 1.1 if t_pe > 0 else 15.0
                div_yield, div_rate = safe_float(i.get('dividendYield')), safe_float(i.get('dividendRate'))
                div = div_yield * 100 if kr else ((div_rate / p * 100) if div_rate > 0 and p > 0 else 0.0)
                
                pmos_val = ((a_pe - f_pe) / a_pe) * 100 if f_pe > 0 and a_pe > 0 else 0
                ey = (1 / f_pe * 100) if f_pe > 0 else 0
                erp = ey - ty
                
                base_fcf, sh, final_g, data_len = get_base_dcf_data(stk, i)
                rnd_trend = analyze_rnd_trend(stk, base_fcf, is_financial)
                p_str = f"{int(p):,}원" if kr else f"${p:,.2f}"

                t_eps, f_eps = safe_float(i.get('trailingEps')), safe_float(i.get('forwardEps'))
                if t_eps == 0 and t_pe > 0: t_eps = p / t_pe
                if f_eps == 0 and f_pe > 0: f_eps = p / f_pe
                
                has_eps_g = False
                if t_eps > 0 and f_eps > 0:
                    eps_g_val = ((f_eps - t_eps) / t_eps) * 100
                    eps_g_str, eps_col, has_eps_g = (f"+{eps_g_val:.1f}%" if eps_g_val > 0 else f"{eps_g_val:.1f}%"), ("#2ecc71" if eps_g_val > 0 else "#ff7675"), True
                else: eps_g_str, eps_col = t("확인불가", "N/A"), "#8892b0"
                    
                has_ytd = False
                try:
                    hist_ytd = stk.history(period="ytd")
                    if not hist_ytd.empty and len(hist_ytd) >= 2:
                        ytd_ret = ((p - hist_ytd['Close'].iloc[0]) / hist_ytd['Close'].iloc[0]) * 100
                        ytd_str, ytd_col, has_ytd = (f"+{ytd_ret:.1f}%" if ytd_ret > 0 else f"{ytd_ret:.1f}%"), ("#2ecc71" if ytd_ret > 0 else "#ff7675"), True
                    else: ytd_str, ytd_col = "N/A", "#8892b0"
                except: ytd_str, ytd_col = "N/A", "#8892b0"

                gap_text = f" ➔ <span class='{'highlight' if ytd_ret > eps_g_val else 'good'}'>{t('[과열 유의]', '[Watch overheat]') if ytd_ret > eps_g_val else t('[기회 가능성]', '[Potential opp]')}</span>" if (has_eps_g and has_ytd) else ""
                eps_vs_ytd_html = f"<span style='color:{eps_col}; font-weight:bold;'>{eps_g_str}</span> vs <span style='color:{ytd_col}; font-weight:bold;'>{ytd_str}</span>{gap_text}"

                eps_trend, bps_trend = analyze_trends(stk)
                iv, mos_val, err = calc_custom_dcf(base_fcf, sh, p, ty, final_g, is_financial)
                mos_val = safe_float(mos_val)
                iv_best, mos_best, _ = calc_custom_dcf(base_fcf, sh, p, ty, min(final_g * 1.5, 0.25), is_financial)
                iv_worst, mos_worst, _ = calc_custom_dcf(base_fcf, sh, p, ty, max(final_g * 0.5, 0.0), is_financial)
                
                op_title, op_color, op_reason = get_comprehensive_investment_opinion(mos_val, pmos_val, roe, (real_roic if real_roic else 0), erp, final_g, criticism_text, is_financial, pbr)

                st.markdown(f"""
                <div translate="no" style="padding: 25px 20px; border-radius: 16px; border: 1px solid {op_color}; background: linear-gradient(145deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); margin-bottom: 25px; text-align: center;">
                    <h3 style="margin: 0 0 12px 0; color: {op_color};">✨ [AI 종합 투자의견] : {op_title} ✨</h3>
                    <span style="color: var(--text-color); font-size: 1.05rem;">{op_reason}</span>
                </div>
                """, unsafe_allow_html=True)

                st.subheader(t("1. 핵심 밸류에이션 지표", "1. Core Valuation Metrics"))
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"- **{t('현재 주가', 'Current Price')}:** {p_str}")
                    st.markdown(f"- **ROE {t('(자본수익률)', '(Equity Return)')} / ROIC:** <b class='good'>{roe:.2f}%</b> / {roic_str}", unsafe_allow_html=True)
                    st.write(f"- **{t('현재 / Fwd PER', 'Current / Fwd PE')}:** {t_pe:.1f}배 / {f_pe:.1f}배")
                    st.write(f"- **{t('과거평균 PER', 'Avg PE')}:** {a_pe:.1f}배")
                with c2:
                    st.write(f"- **PBR {t('(자산가치)', '(Price to Book)')}:** {pbr:.2f}배")
                    st.markdown(f"- **{t('주식 위험 프리미엄 (ERP)', 'Equity Risk Premium')}:** <b style='color:{'#2ecc71' if erp>0 else '#ff7675'}'>{erp:.2f}%p</b>", unsafe_allow_html=True)
                    st.markdown(f"- **{t('컨센서스(EPS 성장률) vs 실제주가(YTD)', 'Consensus vs YTD')}:** {eps_vs_ytd_html}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('자본/BPS 장기 추세', 'Equity Trend')}:** {bps_trend}", unsafe_allow_html=True)

                st.divider()
                st.subheader(t("2. 10년 DCF (내재가치 3가지 시나리오)", "2. 10-Year DCF (3 Scenarios)"))
                if is_financial: st.write(t("금융주는 DCF 평가를 생략합니다.", "DCF N/A for Financials"))
                elif iv:
                    c_w, c_b, c_e = st.columns(3)
                    val_b = f"{int(iv):,}원" if kr else f"${iv:,.2f}"
                    with c_b: st.markdown(f"<div style='border-top:4px solid #fdcb6e; padding:20px; text-align:center;'><b>평균(Base) 적정가: {val_b}</b><br>안전마진: {mos_val:.1f}%</div>", unsafe_allow_html=True)
                
                st.divider()
                st.subheader(t("3. 질적 분석 및 경영진 스크리닝", "3. Qualitative Analysis"))
                st.markdown(f"- **CEO:** {ceo_cleaned}")
                
                # 💡 비즈니스 요약과 Finviz 컨센서스를 완벽히 분리 표출
                st.write(t("**비즈니스 요약**", "**Business Summary**"))
                raw_summary = i.get('longBusinessSummary') or i.get('kr_sum') or "비즈니스 요약 데이터를 가져올 수 없습니다."
                st.caption(f"{tr_text(str(raw_summary))[:400]}...")
                
                fv_eps = i.get('finviz_eps_next')
                if fv_eps:
                    st.markdown(f"<br>**[Finviz 시장 컨센서스]** 내년 예상 EPS 성장률: <span class='good'>{fv_eps}</span> <span style='font-size:0.8em; color:#8892b0;'>(모든 건 사실 수집 및 커뮤니티의 의견을 반영합니다. 이건 확인이 필요한 부분입니다)</span>", unsafe_allow_html=True)

                st.write(t("**경영진 및 지배구조 비판 점검 패널**", "Governance Criticism Panel"))
                st.markdown(f"<div style='color:#ff7675; padding:15px; border:1px solid rgba(255,118,117,0.3); border-radius:10px;'>{criticism_text}</div>", unsafe_allow_html=True)
                
            else:
                st.error(t("데이터 오류", "Data Error"))
