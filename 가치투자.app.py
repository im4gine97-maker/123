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
if "bookmarks" not in st.session_state: st.session_state.bookmarks = []
if "lang" not in st.session_state: st.session_state.lang = "ko"
if "main_input" not in st.session_state: st.session_state.main_input = ""

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
    "BRK": [{"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 21.99}, {"티커": "AXP", "기업명": "American Express Co.", "비중(%)": 17.43}],
    "PSH": [{"티커": "BN", "기업명": "Brookfield Corp.", "비중(%)": 17.62}, {"티커": "AMZN", "기업명": "Amazon.com Inc.", "비중(%)": 17.39}],
    "BAU": [{"티커": "AMZN", "기업명": "Amazon.com, Inc.", "비중(%)": 12.69}, {"티커": "QSR", "기업명": "Restaurant Brands International", "비중(%)": 11.67}],
    "AKRE": [{"티커": "MA", "기업명": "Mastercard Inc - A", "비중(%)": 18.64}, {"티커": "BN", "기업명": "Brookfield Corp", "비중(%)": 11.27}],
    "PI": [{"티커": "HCC", "기업명": "Warrior Met Coal, Inc.", "비중(%)": 39.88}, {"티커": "RIG", "기업명": "Transocean Ltd.", "비중(%)": 31.97}],
    "AQUA": [{"티커": "BRK-B", "기업명": "Berkshire Hathaway Inc Cl-B", "비중(%)": 34.57}, {"티커": "MA", "기업명": "Mastercard Inc - A", "비중(%)": 14.77}]
}

us_top30 = [
    {"순위": 1, "티커": "NVDA", "기업명": "NVIDIA", "시가총액": "$5.11T"},
    {"순위": 2, "티커": "AAPL", "기업명": "Apple", "시가총액": "$4.58T"},
    {"순위": 3, "티커": "GOOGL", "기업명": "Alphabet", "시가총액": "$4.56T"},
    {"순위": 4, "티커": "MSFT", "기업명": "Microsoft", "시가총액": "$3.34T"}
]

kr_top30 = [
    {"순위": 1, "티커": "005930", "기업명": "삼성전자", "시가총액": "1,794조 원"},
    {"순위": 2, "티커": "000660", "기업명": "SK하이닉스", "시가총액": "1,662조 원"},
    {"순위": 3, "티커": "373220", "기업명": "LG에너지솔루션", "시가총액": "89조 원"}
]

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
            hist = stk.history(period="7d")
            if hist is not None and not hist.empty:
                hist = hist.dropna(subset=['Close'])
                
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

def get_13f_portfolio(guru_code):
    return fallback_13f_data.get(guru_code, [])

def fetch_naver_finance_news(cd):
    url = f"https://finance.naver.com/item/news_news.naver?code={cd}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    news_list = []
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.encoding = 'euc-kr' 
        soup = BeautifulSoup(r.text, 'html.parser')
        titles = soup.select('td.title a')
        for a in titles[:3]:
            title_text = a.text.strip()
            if not title_text: continue
            href = a.get('href', '')
            if href.startswith('/'):
                link = "https://finance.naver.com" + href
            else:
                link = f"https://finance.naver.com/item/news.naver?code={cd}"
            news_list.append({"title": title_text, "link": link, "publisher": "네이버증권"})
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
        "AAPL": "Apple (팀 쿡): 자본 배분(자사주 매입)은 탁월하나, AI 혁신 주도권에 대한 외부 커뮤니티의 엇갈린 평가는 이건 확인이 필요한 부분입니다.",
        "MSFT": "Microsoft (사티아 나델라): 강력한 자본 배치와 임직원들의 절대적 지지를 받으나, 반복되는 보안 리스크의 완전한 통제 여부는 이건 확인이 필요한 부분입니다.",
        "NVDA": "Nvidia (젠슨 황): 압도적인 비전으로 강력한 해자를 구축했으나, 창업자 개인에 대한 극단적인 키맨(Key-man) 의존도 리스크가 존재합니다.",
        "GOOGL": "Alphabet (순다르 피차이): 우수한 현금흐름을 유지하나, 관료주의 심화로 인한 의사결정 지연에 대한 내부 임직원 불만은 이건 확인이 필요한 부분입니다.",
        "GOOG": "Alphabet (순다르 피차이): 우수한 현금흐름을 유지하나, 관료주의 심화로 인한 의사결정 지연에 대한 내부 임직원 불만은 이건 확인이 필요한 부분입니다.",
        "AMZN": "Amazon (앤디 재시): 실용주의적 비용 통제로 수익성을 개선 중이나, 노동 환경 논란과 관련된 현장 직원들의 불만이 리스크로 작용할 수 있습니다.",
        "META": "Meta (마크 저커버그): 빠른 의사결정이 장점이나, 차등의결권으로 인한 이사회 견제 기능 부족으로 자본 배분이 독단적일 수 있는 리스크가 있습니다.",
        "BRK-B": "Berkshire Hathaway (그렉 아벨): 투명성과 정직함의 교과서이나, 포스트 버핏 체제에서의 자본 배분 효율성 유지 여부는 이건 확인이 필요한 부분입니다.",
        "BRK-A": "Berkshire Hathaway (그렉 아벨): 투명성과 정직함의 교과서이나, 포스트 버핏 체제에서의 자본 배분 효율성 유지 여부는 이건 확인이 필요한 부분입니다.",
        "TSLA": "Tesla (일론 머스크): 파괴적 혁신을 이끌지만, 잦은 구설수와 타 사업 병행으로 인한 경영 집중도 분산이 외부 평판 리스크로 작용합니다.",
        "AVGO": "Broadcom (혹 탄): 극도로 효율적인 M&A와 비용 통제를 보여주나, 피인수 기업 임직원들의 반발 및 고객 이탈 가능성은 이건 확인이 필요한 부분입니다.",
        "LLY": "Eli Lilly (데이비드 리크스): 핵심 파이프라인에 대한 선제적 자본 배분이 돋보이나, 향후 약가 인하 규제 리스크에 대한 방어력은 점검해야 합니다.",
        "JPM": "JPMorgan Chase (제이미 다이먼): 정직함과 위기관리 능력으로 깊은 신뢰를 받으나, 은퇴 시 후계 승계 과정의 리스크가 존재합니다.",
        "V": "Visa (라이언 맥이너니): 압도적인 영업이익률을 방어 중이나, 신용카드 수수료 규제에 대한 장기 대처 능력은 이건 확인이 필요한 부분입니다.",
        "WMT": "Walmart (더그 맥밀런): 직원 중심의 문화와 옴니채널 전환을 성공적으로 이끌었으나, 이커머스 부문을 방어하는 지속력은 점검이 필요합니다.",
        "MA": "Mastercard (마이클 미바흐): 결제 네트워크 해자를 훌륭히 방어 중이나, 대체 결제 수단 부상에 따른 경영진의 장기 비전은 이건 확인이 필요한 부분입니다.",
        "XOM": "ExxonMobil (대런 우즈): 철저한 현금흐름 중심의 자본 배분을 실행하지만, 화석연료 수요 감소에 대한 친환경 전환 의지는 이건 확인이 필요한 부분입니다.",
        "UNH": "UnitedHealth (앤드류 위티): 강력한 헬스케어 네트워크 장악력을 가졌으나, 최근 사이버 보안 문제로 인한 리스크 관리 부실 논란은 팩트 체크가 필요합니다.",
        "HD": "Home Depot (테드 데커): 투하자본수익률(ROIC) 관리에 탁월하나, 주택 시장 침체기에도 임직원 처우와 마진 방어를 동시에 해낼지는 이건 확인이 필요한 부분입니다.",
        "PG": "Procter & Gamble (존 뮬러): 강력한 가격 결정력으로 불황을 방어 중이나, 혁신적인 신제품 부재에 대한 외부 커뮤니티의 우려는 리스크입니다.",
        "JNJ": "Johnson & Johnson (호아킨 두아토): 소비자 사업부 분사 등 결단력 있는 자본 배분을 보여주나, 탈크 소송 등 과거 소송 리스크의 완전한 해소는 이건 확인이 필요한 부분입니다.",
        "ORCL": "Oracle (사프라 카츠): 클라우드 전환에서 강한 추진력을 보여주지만, 공격적인 영업 방식에 대한 고객 커뮤니티의 불만은 리스크 요인입니다.",
        "COST": "Costco (론 배트리스): 임직원 복지와 고객 신뢰를 최우선으로 하는 정직한 경영을 유지 중이나, 프리미엄 밸류에이션 장기 유지력은 점검 대상입니다.",
        "MRK": "Merck (로버트 데이비스): 핵심 의약품의 수익화는 훌륭하나, 특허 만료 이후를 대비한 R&D 자본 배분 성과는 이건 확인이 필요한 부분입니다.",
        "CVX": "Chevron (마이크 워스): 규율 있는 자본 투자와 주주환원을 중시하지만, 대형 M&A에 대한 독점 규제 당국의 승인 리스크가 상존합니다.",
        "ABBV": "AbbVie (리처드 곤잘레스): 주력 제품 특허 만료 방어에 성공적이었으나, 파이프라인 다각화를 위한 향후 자본 배분 효율성은 이건 확인이 필요한 부분입니다.",
        "CRM": "Salesforce (마크 베니오프): 강력한 비전을 갖췄으나, 잦은 M&A로 인한 자본 배분 비효율성과 임직원 턴오버 증가 리스크가 존재합니다.",
        "AMD": "AMD (리사 수): 탁월한 리더십과 정직함으로 시장 신뢰가 두터우나, 경쟁사의 AI 해자를 실질적으로 침투할 수 있을지는 이건 확인이 필요한 부분입니다.",
        "NFLX": "Netflix (테드 사란도스): 계정 공유 제한 등 수익성 개선이 적중했으나, 콘텐츠 투자(CAPEX) 효율성의 장기 유지는 점검이 필요합니다.",
        "ADBE": "Adobe (샨타누 나라옌): 성공적인 구독 전환을 이끈 경영자이나, AI 그래픽 툴 경쟁 격화에 따른 기존 해자 훼손 우려는 이건 확인이 필요한 부분입니다.",
        "KO": "Coca-Cola (제임스 퀸시): 압도적 브랜드로 안정적 현금을 창출하나, 글로벌 헬스케어 트렌드 변화에 대한 경영진의 장기 대응력은 리스크입니다.",
        "BAC": "Bank of America (브라이언 모이니한): 보수적이고 안정적인 리스크 관리로 정평이 나 있으나, 미실현 손실 포트폴리오의 안전 마진은 이건 확인이 필요한 부분입니다.",
        "PEP": "PepsiCo (라몬 라구아르타): 제품 다각화로 안정적이나, 인플레이션에 따른 가격 저항 리스크를 어떻게 돌파할지는 이건 확인이 필요한 부분입니다.",
        "TMO": "Thermo Fisher (마크 캐스퍼): 꾸준한 복리 성장을 이끈 경영진이나, 바이오텍 투자 침체기에서의 실적 방어력은 점검이 필요합니다.",
        "MCD": "McDonald's (크리스 켐프친스키): 프랜차이즈 비용 통제는 우수하나, 가맹점주 및 임직원 커뮤니티와의 마찰 가능성은 잠재적 리스크입니다.",
        "CSCO": "Cisco (척 로빈스): 구독 모델 전환을 꾀하고 있으나, 대규모 인수합병 이후의 조직 통합 및 시너지 창출 여부는 이건 확인이 필요한 부분입니다.",
        "ABT": "Abbott Laboratories (로버트 포드): 다각화된 사업을 안정적으로 운영하나, 과거 리콜 사태 이후 위기관리 시스템의 완전한 신뢰 회복은 이건 확인이 필요한 부분입니다.",
        "DHR": "Danaher (라이너 블레어): 자체 비즈니스 시스템을 통한 마진 개선은 탁월하나, M&A 타겟 소진 시 유기적 성장률 확보는 점검 대상입니다.",
        "ACN": "Accenture (줄리 스위트): 우수한 인재 관리를 보여주나, 매크로 불확실성 시기 고객사의 예산 삭감 방어력은 이건 확인이 필요한 부분입니다.",
        "INTU": "Intuit (사산 구다르지): 세무 소프트웨어 독점력을 방어 중이나, AI 자동화 확산으로 인한 기존 모델 훼손 방어는 이건 확인이 필요한 부분입니다.",
        "IBM": "IBM (아빈드 크리슈나): AI 기반 사업 구조 재편을 정직하게 추진 중이나, 과거 관료주의 탈피 여부는 외부 커뮤니티 평판 확인이 계속 필요합니다.",
        "CMCSA": "Comcast (브라이언 로버츠): 안정적인 현금을 창출하나, 스트리밍 경쟁 격화에 따른 미디어 부문 자본 배분 전략은 이건 확인이 필요한 부분입니다.",
        "QCOM": "Qualcomm (크리스티아노 아몬): 모바일 외 다각화 비전은 긍정적이나, 주요 고객사의 자체 칩 개발로 인한 매출 타격 방어력은 점검해야 합니다.",
        "VZ": "Verizon (한스 베스트베리): 고배당 주주환원에 힘쓰고 있으나, 막대한 인프라 투자 대비 잉여현금흐름 성장 정체 리스크가 높습니다.",
        "TMUS": "T-Mobile US (마이크 시버트): 공격적인 점유율 확대 전략은 성공적이나, 향후 부채 상환 계획과 가격 경쟁력 유지는 이건 확인이 필요한 부분입니다.",
        "NKE": "Nike (존 도나호): 직접 판매 전환으로 현금흐름을 늘렸으나, 혁신 부족에 대한 내부 임직원 및 소비자 불만은 중대한 리스크입니다.",
        "PFE": "Pfizer (앨버트 불라): 팬데믹 시기 투자 성과를 거두었으나, 이후 막대한 현금을 활용한 M&A 자본 배분 효율성은 이건 확인이 필요한 부분입니다.",
        "DIS": "Disney (밥 아이거): 구조조정을 통한 수익성 방어에 노력 중이나, 명확한 후계자 양성과 콘텐츠 퀄리티 회복 여부는 이건 확인이 필요한 부분입니다.",
        "TXN": "Texas Instruments (하비브 일란): 강력한 해자와 철저한 주주환원이 훌륭하나, 최근 CAPEX 급증에 따른 잉여현금흐름 감소는 점검 대상입니다.",
        "INTC": "Intel (팻 겔싱어): 파운드리 재건 열정은 강하나, 설계와 제조의 이해상충 및 실제 공정 로드맵 달성 가능성은 이건 확인이 필요한 부분입니다.",
        "CAT": "Caterpillar (짐 엄플비): 효율적인 자본 관리로 ROIC를 잘 유지 중이나, 경기 둔화 시 장비 수요 급감을 방어할 잉여현금흐름은 이건 확인이 필요한 부분입니다.",
        "SBUX": "Starbucks (랙스먼 내러시먼): 매장 운영 효율화를 시도 중이나, 노조 결성 등 현장 임직원과의 관계 악화 및 브랜드 평판 훼손 우려는 리스크입니다.",
        "AMAT": "Applied Materials (개리 디커슨): 반도체 장비 혁신을 이끌며 자본 배분이 우수하나, 지정학적 수출 규제에 따른 장기 매출 방어력은 이건 확인이 필요한 부분입니다.",
        "NOW": "ServiceNow (빌 맥더멋): 강력한 열정으로 클라우드 생태계를 확장 중이나, 공격적인 성장 목표가 임직원 번아웃을 유발할 리스크가 있는지 외부 평판 점검이 필요합니다.",
        "LOW": "Lowe's (마빈 엘리슨): 경쟁사 대비 운영 효율화를 정직하게 개선 중이나, 주택 경기 침체 시 마진 방어가 가능할지는 이건 확인이 필요한 부분입니다.",
        "ISRG": "Intuitive Surgical (개리 구타르트): 수술용 로봇 시스템으로 압도적 해자를 구축하나, 향후 경쟁 심화 시 가격 결정력 유지는 점검 대상입니다.",
        "SPGI": "S&P Global (더글러스 피터슨): 독과점 비즈니스로 엄청난 현금을 창출하나, 금리 상승기 채권 발행 감소에 따른 단기 실적 변동성은 이건 확인이 필요한 부분입니다.",
        "BA": "Boeing (켈리 오트버그): 최근 경영진 교체로 쇄신을 시도 중이나, 과거 안전 문제 은폐 논란으로 인한 외부 불신은 매우 중대한 리스크입니다.",
        "LMT": "Lockheed Martin (제임스 타이클렛): 정부 계약 기반의 현금흐름은 확실하나, 대규모 국방 프로젝트의 비용 초과 리스크 통제력은 이건 확인이 필요한 부분입니다.",
        "PLD": "Prologis (하미드 모가담): 물류 부동산 최강자로 자산 배분 통찰력이 탁월하나, 이커머스 성장 둔화 시 공실률 방어 여부는 이건 확인이 필요한 부분입니다.",
        "GE": "General Electric (GE Aerospace) (래리 컬프): 훌륭한 자본 배분과 정직한 기업 분할로 신뢰를 완전히 회복했으나, 단일 항공 사업부 사이클 변동 리스크는 존재합니다.",
        "SYK": "Stryker (케빈 로보): M&A를 통한 성장은 성공적이나, 피인수 기업 임직원들과의 유기적인 화학적 결합 여부는 이건 확인이 필요한 부분입니다.",
        "BLK": "BlackRock (래리 핑크): 막대한 운용자산으로 패시브 시장을 지배하나, 정치적 이슈 및 외부 커뮤니티의 ESG 반발 리스크가 상존합니다.",
        "MS": "Morgan Stanley (테드 픽): 자산관리 부문 강화로 수익 안정성을 높였으나, 경영진 교체 이후 조직 내 정치적 결속력은 이건 확인이 필요한 부분입니다.",
        "TJX": "TJX Companies (어니 허먼): 불황에 강한 비즈니스 모델로 재고 관리가 탁월하나, 공급업체와의 장기적 우호 관계 지속은 점검 대상입니다.",
        "RTX": "Raytheon (RTX) (크리스토퍼 칼리오): 방산과 항공 부문을 잘 결합했으나, 엔진 결함 리스크의 완전한 해결은 이건 확인이 필요한 부분입니다.",
        "BSX": "Boston Scientific (마이클 마호니): 제품 혁신과 자본 배분이 우수하나, 신제품 관련 소송 리스크 발생 가능성은 늘 염두에 두어야 합니다.",
        "AXP": "American Express (스티븐 스퀘리): 프리미엄 고객층 확충으로 브랜드를 지켰으나, 매크로 둔화 시 연회비 이탈 방어력은 이건 확인이 필요한 부분입니다.",
        "GS": "Goldman Sachs (데이비드 솔로몬): 투자은행 본연의 경쟁력은 확고하나, 소매 금융 철수 과정에서의 자본 배분 비효율과 내부 임직원 불만은 리스크입니다.",
        "LRCX": "Lam Research (팀 아처): 반도체 장비 사이클을 견디는 재무 건전성은 훌륭하나, 차세대 R&D 투자의 실질적 성과 도출은 이건 확인이 필요한 부분입니다.",
        "UNP": "Union Pacific (짐 베나): 극단적인 비용 통제로 이익률을 극대화했으나, 철도 노조 및 노동자와의 지속적인 마찰은 외부 평판 훼손 리스크입니다.",
        "CVS": "CVS Health (카렌 린치): 헬스케어 밸류체인 통합 비전은 뚜렷하나, 복잡한 사업 구조로 인해 주주의 자본 효율성이 개선될지는 이건 확인이 필요한 부분입니다.",
        "ETN": "Eaton (크레이그 아놀드): 전력 관리 전환 수혜를 입고 자본을 효율적으로 배치하나, 정책 보조금 축소 시 유기적 성장성은 점검 대상입니다.",
        "VRTX": "Vertex Pharmaceuticals (레쉬마 케왈라마니): 기존 치료제의 수익 창출력은 압도적이나, 신규 파이프라인의 임상 성공 여부는 이건 확인이 필요한 부분입니다.",
        "COP": "ConocoPhillips (라이언 랜스): 현금흐름 중심 전략으로 자본을 배분하나, 규제 당국의 환경 정책 변화 리스크에 취약할 수 있습니다.",
        "PGR": "Progressive (트리시아 그리피스): 데이터 기반 언더라이팅 마진 관리는 업계 최고이나, 기후 변화로 인한 자연재해 손해율 급증 방어력은 이건 확인이 필요한 부분입니다.",
        "ELV": "Elevance Health (게일 부드로): 의료비 통제 능력이 탁월하고 현금흐름이 훌륭하나, 메디케어 어드밴티지 규제 리스크는 점검이 필요합니다.",
        "UBER": "Uber (다라 코스로샤히): 비용 구조조정 흑자 전환 실행력은 우수하나, 긱 워커 처우 관련 법적 규제 리스크가 존재합니다.",
        "BMY": "Bristol-Myers Squibb (크리스토퍼 보어너): 대형 M&A로 규모의 경제는 달성했으나, 특허 만료 절벽을 극복할 R&D 성과는 이건 확인이 필요한 부분입니다.",
        "PM": "Philip Morris (야첵 올자크): 비연소 제품 전환 비전은 명확하나, 각국의 규제 및 세금 인상 리스크 방어력은 이건 확인이 필요한 부분입니다.",
        "BKNG": "Booking Holdings (글렌 포겔): 여행 플랫폼 네트워크 효과를 다졌으나, 빅테크의 여행 검색 진출 방어는 이건 확인이 필요한 부분입니다.",
        "GILD": "Gilead Sciences (다니엘 오데이): 기존 해자는 강력하나, 항암제 분야로의 과도한 M&A가 실제로 ROIC 상승을 이끌지는 이건 확인이 필요한 부분입니다.",
        "DE": "Deere & Company (존 메이): 스마트화로 가격 결정력을 높인 훌륭한 비즈니스이나, 고금리로 인한 장비 교체 주기 지연 여부는 이건 확인이 필요한 부분입니다.",
        "C": "Citigroup (제인 프레이저): 비핵심 소매 금융 매각 등 정직한 구조조정을 진행 중이나, 수익성(ROE) 회복은 이건 확인이 필요한 부분입니다.",
        "SNPS": "Synopsis (사신 가지): EDA의 강력한 해자를 지녔으나, M&A 과정에서 독점 규제 당국의 감시 리스크는 점검이 필요합니다.",
        "ZTS": "Zoetis (크리스틴 펙): 동물 의약품 시장의 훌륭한 가격 결정력을 보이나, 시장 성장 둔화 시 실적 방어 여부는 이건 확인이 필요한 부분입니다.",
        "MMC": "Marsh & McLennan (존 도일): 높은 고객 유지율로 복리 성장을 만드나, 글로벌 경기 침체 시 컨설팅 부문 마진 방어는 이건 확인이 필요한 부분입니다.",
        "SLB": "Schlumberger (올리비에 르 푀치): 유전 서비스 전환을 성공적으로 이끌고 있으나, 지정학적 리스크에 따른 실적 변동성은 이건 확인이 필요한 부분입니다.",
        "CDNS": "Cadence Design Systems (아니루드 데브간): R&D 집중 리더십을 보이나, 소수 반도체 고객사에 대한 높은 의존도 리스크가 존재합니다.",
        "PNC": "PNC Financial Services (윌리엄 뎀착): 보수적인 자본 배분을 하나, 상업용 부동산 대출 포트폴리오 부실화 우려는 이건 확인이 필요한 부분입니다.",
        "CMG": "Chipotle Mexican Grill (스캇 보트라이트): 브랜드력으로 인플레이션을 상쇄 중이나, 임원 교체 이후 기존 품질 유지 여부는 이건 확인이 필요한 부분입니다.",
        "ABNB": "Airbnb (브라이언 체스키): 주인의식으로 훌륭한 플랫폼을 구축했으나, 각국 정부의 단기 임대 규제 심화 리스크는 이건 확인이 필요한 부분입니다.",
        "FI": "Fiserv (프랭크 비시냐노): 결제 인프라 락인 효과가 강력하나, 핀테크 스타트업들의 도전에 대한 기술적 방어력은 이건 확인이 필요한 부분입니다.",
        "ORLY": "O'Reilly Automotive (브래드 베컴): ROIC가 우수하나, 전기차 보급 확대가 부품 교체 수요에 미칠 장기적 영향은 이건 확인이 필요한 부분입니다.",
        "EQIX": "Equinix (찰스 마이어스): AI 인프라 수혜를 입고 있으나, 막대한 데이터센터 자본 지출 대비 잉여현금흐름 장기 성장성은 이건 확인이 필요한 부분입니다.",
        "KLAC": "KLA Corporation (릭 월레스): 계측 독점적 지위를 잘 수성하나, 최선단 공정 R&D 비용 급증 리스크는 점검 대상입니다.",
        "SO": "Southern Company (크리스 워맥): 원전 완공 자본 불확실성을 해소했으나, 전력망 현대화 추가 자본 지출 요구는 이건 확인이 필요한 부분입니다.",
        "WM": "Waste Management (짐 피쉬): 수거망 현금흐름이 돋보이나, 친환경 설비 투자로 인한 마진 훼손 여부는 이건 확인이 필요한 부분입니다.",
        "MCO": "Moody's (롭 파우버): 신용 평가 듀오폴리 구조가 훌륭하나, 금리 변동에 따른 단기 채권 시장 위축 리스크가 있습니다.",
        "CI": "Cigna (데이비드 코다니): 현금흐름을 창출하나, 불투명한 리베이트 논란 등 외부 평판은 지속적인 점검이 필요합니다.",
        "SHW": "Sherwin-Williams (하이디 페츠): 가격 결정력으로 불황을 돌파 중이나, 글로벌 부동산 시장 침체 타격은 이건 확인이 필요한 부분입니다.",
        "TGT": "Target (브라이언 코넬): 매장 혁신 등은 우수하나, 정치/사회적 이슈 개입으로 인한 고객 커뮤니티 충돌 평판 리스크가 존재합니다.",

        "005930": "삼성전자 (이재용/한종희): 막대한 자본과 우수한 PBR 대비 낮은 주가를 보이나, HBM 차세대 주도권과 파운드리 등 임직원 혁신 동력 회복은 이건 확인이 필요한 부분입니다.",
        "000660": "SK하이닉스 (최태원/곽노정): HBM 선점으로 탁월한 자본 배분 성과를 증명했으나, 다운사이클 재무 건전성 및 주주환원 여력은 이건 확인이 필요한 부분입니다.",
        "373220": "LG에너지솔루션 (김동명): 훌륭한 고객사 관계를 구축했으나, 모회사 물적분할(쪼개기 상장) 거버넌스 불신 극복 및 수익성 방어는 이건 확인이 필요한 부분입니다.",
        "005380": "현대차 (정의선): PBR 1배 향한 주주환원(자사주 소각)이 탁월하나, 노조 상생 및 전기차 캐즘 극복 여부는 이건 확인이 필요한 부분입니다.",
        "000270": "기아 (송호성): 우수한 이익률과 강력한 주주환원으로 밸류업에 적극적이나, 이익 피크아웃 속 브랜드 가치 상승 유지는 이건 확인이 필요한 부분입니다.",
        "207940": "삼성바이오로직스 (존 림): 압도적인 위탁생산 규모화(Scaling)를 달성했으나, 고PBR을 정당화할 유기적 성장 장기 지속은 이건 확인이 필요한 부분입니다.",
        "068270": "셀트리온 (서정진): 리더십으로 신약 성과를 내고 있으나, 합병 이후 재고자산 투명성/회계 처리에 대한 시장 신뢰 회복은 이건 확인이 필요한 부분입니다.",
        "005490": "POSCO홀딩스 (장인화): 철강 저PBR 매력을 갖췄으나, 이차전지 소재 자본 배분 장기 효율성과 관치에서 자유로운 경영 여부는 이건 확인이 필요한 부분입니다.",
        "105560": "KB금융 (양종희): 적극적 자사주 소각 등 주주환원 확대로 저PBR 탈피를 시도 중이나, PF 리스크 및 관치 금융 우려 방어력은 이건 확인이 필요한 부분입니다.",
        "035420": "NAVER (최수연): 독점 플랫폼 해자를 보유하나, AI 투자 대비 수익화 성과와 글로벌 확장에 대한 내부 불만 해결은 이건 확인이 필요한 부분입니다.",
        "055550": "신한지주 (진옥동): 우수한 자본력으로 PBR 재평가를 추진 중이나, 내부 통제(금융 사고) 리스크 근절과 정직한 문화 안착 여부는 이건 확인이 필요한 부분입니다.",
        "006400": "삼성SDI (최윤호): 보수적이고 정직한 자본 배분으로 재무 건전성이 우수하나, 전고체 등 차세대 패권에서 점유율 확보는 이건 확인이 필요한 부분입니다.",
        "051910": "LG화학 (신학철): 첨단소재 다각화를 이끌고 있으나, 핵심 자회사 분할 상장 이후 주주 신뢰 회복과 지주사 디스카운트 근본 해소는 이건 확인이 필요한 부분입니다.",
        "012330": "현대모비스 (이규석): 핵심 부품사로서 현금 창출력이 뛰어나나, 저PBR 해소를 위한 지배구조 개편 시 소액주주 권익 보호는 이건 확인이 필요한 부분입니다.",
        "035720": "카카오 (정신아): 과거 쪼개기 상장으로 잃은 도덕성과 시장 신뢰를 경영진 교체를 통해 얼마나 빠르게 회복할지는 이건 확인이 필요한 부분입니다.",
        "028260": "삼성물산 (오세철 외): 자산가치(저PBR)가 매우 뛰어나나, 소액주주 요구에 부응하는 자본 배치 및 거버넌스 선진화 의지는 이건 확인이 필요한 부분입니다.",
        "086790": "하나금융지주 (함영주): 고배당과 자사주 매입에 적극적이나, 해외 대체투자 부실 가능성 및 매크로 악화 시 자본 방어력은 이건 확인이 필요한 부분입니다.",
        "066570": "LG전자 (조주완): 구독 및 B2B 전장으로 수익성을 정직하게 개선 중이나, 질적 도약이 실질적인 기업가치(PBR) 상승으로 이어질지는 이건 확인이 필요한 부분입니다.",
        "138040": "메리츠금융지주 (김용범): 전액 주주환원이라는 선구적 자본 배분을 보여주었으나, 경영진 과거 행보 대비 도덕성/정직함 유지 및 거버넌스는 이건 확인이 필요한 부분입니다.",
        "032830": "삼성생명 (홍원학): 막대한 자산 대비 지나치게 낮은 PBR이나, 보험업법 리스크와 삼성전자 지분 관련 거버넌스/자본 효율화는 이건 확인이 필요한 부분입니다.",
        "096770": "SK이노베이션 (박상규): 정유 현금을 배터리에 공격적으로 배분했으나, SK온 흑자 지연 및 훼손된 주주가치 회복 여부는 이건 확인이 필요한 부분입니다.",
        "010130": "고려아연 (최윤범): 제련 해자를 지녔으나, 경영권 분쟁 시 과도한 자본 지출과 향후 주주친화(상생) 배당 정책 일관성은 이건 확인이 필요한 부분입니다.",
        "329180": "HD현대중공업 (이상균): 턴어라운드에 성공해 수익을 회복 중이나, 고질적인 인력난 문제 및 노사(노동자) 장기적 상생은 이건 확인이 필요한 부분입니다.",
        "033780": "KT&G (방경만): 자본 배치(주주환원 확대) 개선으로 매력을 높이고 있으나, 궐련형 전자담배 글로벌 점유율 장기 확대는 이건 확인이 필요한 부분입니다.",
        "000810": "삼성화재 (이문화): 업계 최고 수준 손해율 관리로 PBR 개선을 꾀하고 있으나, IFRS17 이후 장기 이익 변동성 축소 여부는 이건 확인이 필요한 부분입니다.",
        "316140": "우리금융지주 (임종룡): 높은 배당 매력을 지니나, 부족한 비은행 다각화를 M&A 등 효율적 자본 배분으로 채울지는 이건 확인이 필요한 부분입니다.",
        "011200": "HMM (김경배): 팬데믹 현금(안전마진)으로 극저PBR이나, 운임 하락 시 효율적인 잉여현금 활용과 민영화 성공 여부는 이건 확인이 필요한 부분입니다.",
        "034020": "두산에너빌리티 (박지원): 글로벌 원전 르네상스 수혜이나, 지배구조(물적분할 등) 문제로 훼손된 주주 신뢰 완전 회복은 이건 확인이 필요한 부분입니다.",
        "034730": "SK (장동현): 첨단 산업 투자를 주도하나, 중복 상장으로 굳어진 고질적 지주사 디스카운트 근본적 해결 의지는 이건 확인이 필요한 부분입니다.",
        "259960": "크래프톤 (김창한): PUBG 현금흐름이 압도적이나, 다중화/백업 시스템(신작 파이프라인) 성공을 통한 원히트 원더 탈피는 이건 확인이 필요한 부분입니다.",
        "012450": "한화에어로스페이스 (손재일): K-방산 복리 성장을 증명하고 있으나, 지정학 사이클 이후의 수익성 유지 및 자본 배분 효율성은 이건 확인이 필요한 부분입니다.",
        "018260": "삼성SDS (황성우): 막대한 현금성 자산을 보유한 저PBR이나, 클라우드/AI 파급력 대비 소극적인 주주환원 자본 배치의 변화 가능성은 이건 확인이 필요한 부분입니다.",
        "402340": "SK스퀘어 (한명진): SK하이닉스 지분 바탕의 강력한 주주환원을 약속하나, 11번가 등 부진 포트폴리오 구조조정 성공 여부는 이건 확인이 필요한 부분입니다.",
        "003550": "LG (구광모): 순자산가치 대비 심각하게 할인된(저PBR) 지주사이나, 지배구조 관련 리스크 극복 및 소액주주 위한 파격적 자본 배분은 이건 확인이 필요한 부분입니다.",
        "024110": "기업은행 (김성태): 압도적인 배당수익률을 제공하나, 불황 시 중소기업 부실 방어력 및 배당 정책 관치 리스크 완전 탈피 여부는 이건 확인이 필요한 부분입니다.",
        "090430": "아모레퍼시픽 (서경배): 북미 포트폴리오 재편 등 방향성은 올바르나, 잃어버린 중국의 공백을 장기 복리 성장으로 메울지는 이건 확인이 필요한 부분입니다.",
        "017670": "SK텔레콤 (유영상): 독과점 비즈니스로 안정적인 현금을 창출하나, AI 컴퍼니 전환 자본 투자가 순수 주주환원보다 효율적일지는 이건 확인이 필요한 부분입니다.",
        "003670": "포스코퓨처엠 (유병옥): 양음극재 생산 능력을 갖췄으나, 판가 하락 장기화 시 막대한 CAPEX를 감당할 영업이익 창출력은 이건 확인이 필요한 부분입니다.",
        "030200": "KT (김영섭): 비용 구조조정과 주주환원을 정직하게 실행 중이나, 정치권 낙하산 논란 등 관치 리스크로부터 영구 독립 여부는 이건 확인이 필요한 부분입니다.",
        "086280": "현대글로비스 (이규복): 물류망 기반 ROIC가 우수하나, 그룹 지배구조 개편 과정에서 오너십 결정으로 소액주주 가치 침해 가능성은 이건 확인이 필요한 부분입니다.",
        "003490": "대한항공 (조원태): 가격 결정력을 훌륭하게 증명했으나, 아시아나 인수합병 재무 부담 관리와 오너 도덕적 신뢰(거버넌스) 유지는 이건 확인이 필요한 부분입니다.",
        "009540": "HD한국조선해양 (김성준): 지주사 디스카운트가 심각하며, 친환경 선박 R&D 자본 배분이 모회사 소액주주 가치로 실질 환원될지는 이건 확인이 필요한 부분입니다.",
        "000100": "유한양행 (조욱제): 정직함이 돋보이는 전문경영인 체제이나, 렉라자 이후 막대한 잉여현금을 다시 파이프라인에 효과적으로 재배치할지는 이건 확인이 필요한 부분입니다.",
        "042660": "한화오션 (권혁웅): 대규모 특수선 확장 투자는 훌륭하나, 인수 초기 노사 갈등 수습 및 투입 자본 대비 기대되는 ROIC 달성 가능성은 이건 확인이 필요한 부분입니다.",
        "010950": "S-Oil (안와르 알 히자지): 든든한 대주주 자본력으로 초대형 설비 짓고 있으나, 친환경 전환 시기에 장기적 밸류트랩(저PBR 고착화) 전락 여부는 이건 확인이 필요한 부분입니다.",
        "323410": "카카오뱅크 (윤호영): 플랫폼 밸류에이션(PBR)을 방어 중이나, 대주주 사법 리스크 및 금리 사이클을 이길 비이자이익 장기 창출 여부는 이건 확인이 필요한 부분입니다.",
        "051900": "LG생활건강 (이정애): 뷰티/생활 포트폴리오 턴어라운드를 애쓰고 있으나, 훼손된 브랜드 파워 복구와 자본 배분을 통한 이익률 개선은 이건 확인이 필요한 부분입니다.",
        "251270": "넷마블 (권영식): 외부 IP 의존 및 M&A 여파로 효율성이 악화된 바 있으며, 자체 IP 확대를 통한 구조적 잉여현금흐름 개선 여부는 이건 확인이 필요한 부분입니다.",
        "036570": "엔씨소프트 (김택진/박병무): 수익 모델 도덕성 논란으로 극저PBR 상태이며, 경영진의 정직한 체질 개선과 외부 커뮤니티 신뢰 회복 가능성은 이건 확인이 필요한 부분입니다.",
        "097950": "CJ제일제당 (강신호): K-푸드 세계화로 가격 결정력이 있으나, 과거 무리한 외형 확장 부채 완화 및 실질적인 잉여현금흐름 증가는 이건 확인이 필요한 부분입니다.",
        "247540": "에코프로비엠 (최문호): 양극재 시장에서 훌륭한 성장이나, 밸류에이션(고PBR) 부담을 해소할 만한 장기적인 전기차 수요 회복 팩트체크는 이건 확인이 필요한 부분입니다.",
        "086520": "에코프로 (송호준): 지주사로서 막대한 자본 조달 성과가 있으나, 과도한 프리미엄 정당화 및 경영진 과거 사법 리스크 극복(도덕성 회복)은 이건 확인이 필요한 부분입니다.",
        "042700": "한미반도체 (곽동신): HBM 장비 독점력으로 자사주 매입 등 자본 배분이 훌륭하나, 경쟁사 진입 방어를 통한 고PBR 유지는 이건 확인이 필요한 부분입니다.",
        "028300": "HLB (진양곤): 오랜 기간 신약 비전을 이끌었으나, 실질적인 현금흐름 창출로 현재의 극단적 고PBR을 온전히 증명해 낼지는 이건 확인이 필요한 부분입니다.",
        "196170": "알테오젠 (박순재): SC 제형 기술의 독보적 경쟁력으로 지지를 받으나, 기술 수출 이후 파이프라인 다각화를 통한 장기 복리 성장 증명은 이건 확인이 필요한 부분입니다.",
        "015760": "한국전력 (김동철): 극단적인 저PBR 자산주이나, 요금 통제 관치 리스크와 막대한 부채 구조를 자체 의지로 돌파할 수 있을지는 이건 확인이 필요한 부분입니다.",
        "267260": "HD현대일렉트릭 (조석): 전력망 인프라 슈퍼 사이클 수주가 탁월하나, 투자 피크아웃 이후에도 우수한 마진과 PBR 방어력을 유지할지는 이건 확인이 필요한 부분입니다.",
        "241560": "두산밥캣 (스캇 박): 뛰어난 이익률을 지닌 훌륭한 저PBR 기업이나, 모그룹(두산) 지배구조(쪼개기 합병 등) 개편 시 소액주주 가치 침해 리스크는 이건 확인이 필요한 부분입니다.",
        "006260": "LS (명노현): 전력 케이블 수요 확대로 저PBR 매력이 부각되나, 자회사들의 공격적인 자본 지출이 실질적인 잉여현금흐름 증가로 이어질지는 이건 확인이 필요한 부분입니다.",
        "009830": "한화솔루션 (이구영 외): 태양광 밸류체인에 선제적 자본 배분을 했으나, 중국 과잉 공급 방어 및 정부 보조금 축소 시 자력 흑자 달성은 이건 확인이 필요한 부분입니다.",
        "047050": "포스코인터내셔널 (이계인): 에너지 통합으로 외형을 키웠으나, 대규모 친환경 설비 전환 자본 배분의 장기 투하자본수익률(ROIC) 증명은 이건 확인이 필요한 부분입니다.",
        "010120": "LS ELECTRIC (구자균): 전력 인프라 확대 직접 수혜로 규모화를 이뤘으나, 공급업체와의 장기적 상생 및 글로벌 고객사 확충은 이건 확인이 필요한 부분입니다.",
        "010140": "삼성중공업 (최성안): 오랜 적자를 끊고 턴어라운드에 훌륭히 성공했으나, 조선업 숙련 노동자 인력난 극복 및 악성 재고 리스크 완전 해소는 이건 확인이 필요한 부분입니다.",
        "047810": "한국항공우주(KAI) (강구영): 국방 예산 기반 훌륭한 비즈니스이나, 민간 수출 시장 가격 결정력 확보와 관치 경영 탈피를 통한 PBR 개선은 이건 확인이 필요한 부분입니다.",
        "079550": "LIG넥스원 (신익현): 유도무기 특화로 압도적 수주 성과를 내고 있으나, K-방산 사이클 둔화 시 R&D 투자를 통한 자력 성장이 가능할지는 이건 확인이 필요한 부분입니다.",
        "128940": "한미약품 (박재현): 우수한 R&D와 정직한 제약 본업 집중도를 보이나, 오너 일가의 장기 경영권 분쟁으로 인한 자본 배분의 훼손 리스크 봉합은 이건 확인이 필요한 부분입니다.",
        "000720": "현대건설 (윤영준): 막대한 수주 잔고 대비 극도의 저PBR 매력을 갖췄으나, 부동산 PF 부실 방어와 원자재 인플레이션 이익률 훼손 극복은 이건 확인이 필요한 부분입니다.",
        "021240": "코웨이 (서장원): 강력한 렌털 현금흐름으로 자본을 쌓고 있으나, 최대 주주(넷마블)의 유동성 확보를 위한 무리한 배당 압박 리스크는 이건 확인이 필요한 부분입니다.",
        "005830": "DB손해보험 (정종표): 안정적인 손해율 관리로 방어력을 확실히 증명하나, 의료 파업 등 외부 변수로 인한 실손보험 적자 구조의 획기적 개선은 이건 확인이 필요한 부분입니다.",
        "011780": "금호석유 (백종훈): 라텍스 중심 우수한 현금흐름을 증명한 저PBR 기업이나, 경영권 분쟁 불씨 및 석유화학 다운사이클 장기화 완전 극복은 이건 확인이 필요한 부분입니다.",
        "352820": "하이브 (박지원): 멀티 레이블로 리스크 다중화 백업 시스템을 꾀했으나, 자회사 사태 등 내부 거버넌스 충돌 리스크의 완전한 상생 봉합은 이건 확인이 필요한 부분입니다.",
        "271560": "오리온 (이승준): 철저한 현지화로 압도적 이익률을 훌륭히 증명했으나, 이종 산업(레고켐바이오) 인수라는 자본 배분의 실질적 수익 성공은 이건 확인이 필요한 부분입니다.",
        "078930": "GS (허태수): 꾸준히 이익을 내는 극저PBR 지주사이나, 지나치게 보수적인 오너 경영 하에서 밸류업을 위한 획기적이고 정직한 자본 배분 변화는 이건 확인이 필요한 부분입니다.",
        "282330": "BGF리테일 (민승배): 독과점 체제로 훌륭한 ROIC를 내나, 국내 출점 포화 시 잉여현금을 어떻게 효율적으로 해외 등에 분산 투자할지는 이건 확인이 필요한 부분입니다.",
        "064350": "현대로템 (이용배): 글로벌 방산 수주로 극적인 턴어라운드에 성공했으나, 과거 수익을 깎던 철도 부문의 적자 근절 및 완전한 체질 개선은 이건 확인이 필요한 부분입니다.",
        "141080": "리가켐바이오(레고켐바이오) (김용주): ADC 플랫폼으로 독보적 기술력을 증명했으나, 대기업(오리온) 피인수 이후 R&D 핵심 인력 엑소더스 방어는 이건 확인이 필요한 부분입니다.",
        "003230": "삼양식품 (김동찬): 단일 IP의 폭발적 현금 창출력은 압도적이나, 오너 리스크의 완전한 근절과 라면 외 포트폴리오를 향한 현금 재배치는 이건 확인이 필요한 부분입니다.",
        "041510": "에스엠(SM Ent.) (장철혁): 카카오 편입 이후 체질을 개선 중이나, 최대 주주의 사법 리스크가 회사 자본 배치 및 임직원 평판에 미칠 장기적 파급력은 이건 확인이 필요한 부분입니다.",
        "377300": "카카오페이 (신원근): 락인된 강력한 플랫폼 해자는 있으나, 경영진 과거 주식 먹튀 논란으로 훼손된 도덕적 신뢰 회복과 유의미한 흑자 전환은 이건 확인이 필요한 부분입니다.",
        "139480": "이마트 (한채양): 훌륭한 부동산 자산을 가진 전형적 저PBR 기업이나, 과거 이커머스 고가 M&A 등 거대한 자본 배분 오류에서 벗어나 온전한 현금을 복구할지는 이건 확인이 필요한 부분입니다.",
        "001450": "현대해상 (조용일/이성재): 강력한 영업망 기반으로 꾸준히 현금을 창출하는 저PBR이나, IFRS17 이후 예실차(예상-실제 차이) 변동성에 따른 안정성은 이건 확인이 필요한 부분입니다.",
        "018880": "한온시스템 (너달 쿠추카야): 열관리 1위의 훌륭한 해자를 가졌으나, 막대한 부채와 대주주(한국타이어) 변경 이후의 실질적인 유기적 시너지 성과는 이건 확인이 필요한 부분입니다.",
        "000120": "CJ대한통운 (신영수): 물류 독과점 구조로 훌륭한 현금흐름을 내나, 쿠팡 등 유통 공룡 직접 진출로부터 기존 가격 결정력을 장기적으로 방어할지는 이건 확인이 필요한 부분입니다.",
        "028670": "팬오션 (안중호): 벌크선 시장의 안정적 이익을 내는 극저PBR 기업이나, 모기업(하림) 무리한 M&A 자금줄로 전락해 소액주주 가치 훼손 거버넌스 리스크 해소는 이건 확인이 필요한 부분입니다.",
        "035900": "JYP Ent. (정욱): 모범적 시스템으로 엔터 최고 마진을 유지 중이나, 신규 아티스트 개발 파이프라인에 투자된 자본이 글로벌 ROIC로 증명될지는 이건 확인이 필요한 부분입니다.",
        "011210": "현대위아 (정재욱): 부품 중심의 안정적인 저PBR 기업이나, 열관리 등 신규 전기차 전환 비즈니스 안착 및 잃어버린 영업이익률 턴어라운드는 이건 확인이 필요한 부분입니다.",
        "036460": "한국가스공사 (최연혜): 가치 투자 관점의 전형적인 극단적 저PBR이나, 천문학적 미수금 해결과 이를 위한 정치권 관치 리스크의 원천적 해소는 이건 확인이 필요한 부분입니다.",
        "112610": "씨에스윈드 (김성권): 글로벌 1위 풍력 해자와 훌륭한 투자를 보이나, 정책 보조금 축소 시 자체 가격 결정력으로 잉여현금을 방어할 자생력 유지는 이건 확인이 필요한 부분입니다.",
        "067160": "아프리카TV(SOOP) (정찬용): 독점 생태계 장악으로 이익 복리를 훌륭히 창출하나, 핵심 스트리머 이탈 방어 및 사회적 윤리 리스크 관련 팩트 체크는 이건 확인이 필요한 부분입니다.",
        "011170": "롯데케미칼 (이훈기): 석유화학 침체로 극심한 저PBR이나, 과거 배터리 소재(일진머티리얼즈) 고가 인수 등 자본 배분 오류의 후유증 극복 및 부채 감소 여부는 이건 확인이 필요한 부분입니다.",
        "004170": "신세계 (박주형): 백화점 부동산의 자산가치(저PBR)는 훌륭하나, 면세점 부진 턴어라운드 및 지배구조(계열 분리) 승계 과정에서의 주주가치 훼손 방어는 이건 확인이 필요한 부분입니다.",
        "004370": "농심 (이병학): K-푸드 훈풍과 확고한 라면 해자를 지닌 우량 기업이나, 밀가루 원자재 가격 급등 시 이를 제품가로 정직하게 전가하는 마진 방어력은 이건 확인이 필요한 부분입니다.",
        "088980": "맥쿼리인프라 (서범식): 통행료 기반 효율적 자본 회수와 정직한 배당은 탁월하나, 금리 인하 지연 시 상대적 배당 매력 저하 및 채권금리 대비 메리트는 이건 확인이 필요한 부분입니다.",
        "000250": "삼천당제약 (전인석): 바이오시밀러로 주가 방어를 훌륭히 해내고 있으나, 글로벌 대형 제약사 틈바구니에서 실질적인 상업화 안착 및 현금 창출 증명은 이건 확인이 필요한 부분입니다.",
        "192820": "코스맥스 (이병만): 탁월한 ODM 제조 기술력으로 압도적 이익을 내나, 해외 핵심 자회사 상장(쪼개기 상장) 시도 시 모회사 주주가치 훼손 리스크 영구 해소는 이건 확인이 필요한 부분입니다.",
        "010620": "HD현대미포(현대미포조선) (김형관): 중형 선박 시장 1위를 지배하며 훌륭한 수주를 보이나, 하청 노동자 부족 현상이 선박 인도 지연(리스크) 및 마진 훼손으로 번질지는 이건 확인이 필요한 부분입니다.",
        "383220": "F&F (김창수): 탁월한 브랜드 라이선싱(기획력)으로 고마진을 달성했으나, 내수 의류 침체 시 막대한 잉여현금을 M&A 등 다른 자산에 정직하게 배분할지는 이건 확인이 필요한 부분입니다.",
        "035250": "강원랜드 (최철규): 카지노 독점권 기반의 막대한 현금 자산을 지닌 심각한 저PBR이나, 밸류업 배당 확대가 정부(관치) 주도 하에 장기적이고 일관성 있게 유지될지는 이건 확인이 필요한 부분입니다.",
        "298020": "효성티앤씨 (김치형): 스판덱스 부문 압도적 규모의 경제(해자)를 증명했으나, 모그룹의 잦은 인적분할에 따른 거버넌스 피로감 및 부채 축소를 위한 자본 통제력은 이건 확인이 필요한 부분입니다.",
        "002790": "아모레G (서경배): 훌륭한 브랜드 자산을 보유한 저PBR 지주사이나, 자회사들의 턴어라운드 속에서 기존의 소극적인 주주환원(자본 배치) 획기적 선회 여부는 이건 확인이 필요한 부분입니다."
    }
    
    for key, text in db.items():
        if key in tk_clean or (len(cd_clean) == 6 and key == cd_clean):
            return text
            
    return f"{ceo_name} 경영진 - 위키 및 공공 기록 스크리닝 결과, 해당 경영진에 대한 사법적 리스크나 중범죄 이력은 두드러지지 않습니다. 다만 가치투자 관점에서 과도한 자본 배분 오류 및 노사 갈등 여부는 투자 전 추가 교차 검증이 필요합니다. (이건 확인이 필요한 부분입니다)"

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

def calc_custom_dcf(fcf, sh, p, ty, g, is_financial=False):
    if is_financial: return 0, 0, t("금융/보험주 DCF 평가 제외 (PBR 대체 분석 진행)", "DCF N/A for Financials (Evaluated via PBR instead)")
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

def get_implied_g(fcf, sh, p, ty):
    if not fcf or fcf <= 0 or not sh or sh <= 0 or not p or p <= 0: return None
    low, high = -0.5, 1.0 
    dr = max(ty / 100, 0.09)
    for _ in range(40):
        mid = (low + high) / 2
        cv = fcf
        fut_sum = 0
        for y in range(1, 11):
            cv *= (1 + mid)
            fut_sum += cv / ((1 + dr) ** y)
        tv = (cv * 1.02) / (dr - 0.02)
        dtv = tv / ((1 + dr) ** 10)
        iv = (fut_sum + dtv) / sh
        if iv > p:
            high = mid
        else:
            low = mid
    return (low + high) / 2

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
    eps_trend = f"<span style='color:#8b949e'>{t('데이터 부족', 'Insufficient Data')}</span>"
    bps_trend = f"<span style='color:#8b949e'>{t('데이터 부족', 'Insufficient Data')}</span>"
    if stk is None: return eps_trend, bps_trend
    try:
        inc, bs = stk.income_stmt, stk.balance_sheet
        if inc is not None and not inc.empty:
            target_col = 'Basic EPS' if 'Basic EPS' in inc.index else ('Diluted EPS' if 'Diluted EPS' in inc.index else None)
            if target_col:
                eps_vals = inc.loc[target_col].dropna().values[:4][::-1] 
                if len(eps_vals) >= 3:
                    if all(eps_vals[i] <= eps_vals[i+1] for i in range(len(eps_vals)-1)) and eps_vals[0] < eps_vals[-1]: 
                        eps_trend = f"<span class='good'>{t('[합격] 4년 지속 상승 추세', '[Pass] 4Y Consistent Upward Trend')}</span>"
                    else: 
                        eps_trend = f"<span class='highlight'>{t('[주의] 변동/하락', '[Warning] Fluctuating/Declining')}</span>"
        if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index:
            eq_vals = bs.loc['Stockholders Equity'].dropna().values[:4][::-1]
            if len(eq_vals) >= 3:
                if all(eq_vals[i] <= eq_vals[i+1] for i in range(len(eq_vals)-1)) and eq_vals[0] < eq_vals[-1]: 
                    bps_trend = f"<span class='good'>{t('[합격] 4년 자본 지속 증가', '[Pass] 4Y Consistent Equity Growth')}</span>"
                else: 
                    bps_trend = f"<span class='highlight'>{t('[주의] 자본 변동/감소', '[Warning] Equity Fluctuating/Declining')}</span>"
    except: pass
    return eps_trend, bps_trend

def get_comprehensive_investment_opinion(mos, pmos, roe, roic, erp, final_g, ceo_text, is_financial=False, pbr=0.0):
    score = 0
    ceo_score = 0
    
    strong_pos = ["역사상 가장 신뢰받는", "탁월한 자본 배분", "주주환원", "자사주 매입", "자사주 소각", "정직함", "전액 주주환원", "압도적", "투명한", "복리 성장", "정직하게", "우수", "훌륭"]
    good_pos = ["검증된 경영자", "안정적", "선점", "실행력", "지배적 지위", "독보적", "결단력 있는", "턴어라운드", "직원 중심", "효율적인 M&A", "비용 통제", "가격 결정력", "현금흐름 중심"]
    strong_neg = ["구속", "횡령", "사법 리스크", "사법적 리스크", "배임", "파산", "회계 처리 논란", "물적분할", "쪼개기 상장", "주주가치 훼손", "거버넌스 불신", "관치", "안전 문제 은폐", "리베이트", "엑소더스", "경영권 분쟁", "금융 사고"]
    bad_neg = ["관료주의", "지정학적", "노조", "마진 압박", "침체", "수요 둔화", "부채 부담", "파업", "변동성", "둔화", "위축", "차등의결권", "지배력 유지", "자본 배분 비효율", "반독점", "독점 규제", "합병 규제", "불만", "이탈", "소송 리스크", "번아웃", "불신", "공실률", "낙하산", "밸류트랩", "인력난"]
    
    if any(k in ceo_text for k in strong_pos): ceo_score += 20
    elif any(k in ceo_text for k in good_pos): ceo_score += 10
    else: ceo_score += 5 
        
    if any(k in ceo_text for k in strong_neg): ceo_score -= 25
    if any(k in ceo_text for k in bad_neg): ceo_score -= 15
        
    score += max(-20, min(20, ceo_score))
        
    if pmos > 15: score += 20
    elif pmos > 0: score += 10
    elif pmos < -15: score -= 20
    else: score -= 10

    if is_financial:
        if roe >= 10: score += 20
        elif roe < 7: score -= 10
        if pbr > 0 and pbr < 0.7: score += 20
        elif pbr >= 0.7 and pbr < 1.1: score += 10
        elif pbr >= 1.5: score -= 20
    else:
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
        title, color, reason = t("적극적 할인 (Deep Discount)", "Deep Discount"), "#09ab3b", t("경영진, 자본효율(ROE), 모든 가격 지표(PER/ERP/PBR)가 균일하게 완벽한 초저평가 할인 구간을 가리키고 있습니다.", "All evenly weighted metrics indicate a deep discount.")
    elif score >= 40:
        title, color, reason = t("할인 (Discount)", "Discount"), "#3fb950", t("모든 평가 지표들이 고르게 양호하며, 펀더멘털과 밸류에이션 종합 점수 기준 충분한 안전마진이 확보되었습니다.", "All metrics are consistently solid, showing a sufficient margin of safety across fundamentals and valuation.")
    elif score >= 15:
        title, color, reason = t("약간 할인 (Slight Discount)", "Slight Discount"), "#85e89d", t("적정 가치 대비 약간 저렴한 구간으로, 긍정적인 투자 매력도를 보입니다.", "Slightly undervalued compared to fair value, showing positive investment appeal.")
    elif score >= -15:
        title, color, reason = t("적정 가치 (Fair Value)", "Fair Value"), "#e3b341", t("핵심 가치 지표들이 상호 상쇄되며 주가가 기업의 본질 가치에 딱 부합하게 거래 중입니다.", "Trading closely to intrinsic value. Not a clear discount.")
    elif score >= -40:
        title, color, reason = t("약간 할증 (Slight Premium)", "Slight Premium"), "#d29922", t("펀더멘털 대비 주가가 약간 비싸게 형성되어 있어, 안전마진이 다소 부족합니다.", "Priced at a slight premium with limited margin of safety.")
    elif score >= -70:
        title, color, reason = t("할증 (Premium)", "Premium"), "#ff7b72", t("펀더멘털 지표 대비 가격 지표들이 전반적으로 비싸게 형성되어 있어, 국채 대비 기대수익률이 열위에 있는 할증 구간입니다.", "Price metrics are uniformly expensive relative to yields.")
    else:
        title, color, reason = t("과도한 할증 (Excessive Premium)", "Excessive Premium"), "#da3633", t("치명적인 경영진 리스크나 펀더멘털 취약성 등 종합적인 악재에도 불구하고 주가가 비상식적으로 과열된 투기적 위험 구간입니다.", "Dangerous speculative territory due to severe management criticism or overvaluation.")

    if is_cyclical:
        reason += t(" (⚠️ 시클리컬 기업 감점 적용됨: 실적 변동성으로 인한 가치평가 신뢰도 하락)", " (⚠️ Cyclical Penalty Applied: Lower valuation reliability due to earnings volatility)")
    if is_financial:
        reason += t(" (🏦 금융/보험주 특수 로직 적용됨: ROIC 및 DCF 연산 왜곡을 제거하고 ROE와 장부가 가치 PBR 분석으로 고도화 평가 완료)", " (🏦 Financial Mode Active: Switched from FCF/ROIC to asset-backed ROE/PBR screening)")

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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t("개별 기업 가치분석", "Company Value Analysis"), 
    t("유명 가치투자자 13F", "Guru 13F Portfolios"),
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

        st_container = st.empty()
        with st_container.container():
            st.toast(t("데이터를 불러오는 중입니다...", "Fetching data..."), icon="⏳")
            stk, p, i, kr = get_data(tk)
            
            if p:
                try: ty = safe_float(macro_data["10Y Treasury"]["p"], 4.4)
                except: ty = 4.4
                if ty == 0.0: ty = 4.4

                if i is None:
                    i = {}

                is_financial = i.get('sector') == 'Financial Services' or i.get('industry') in ['Banks - Regional', 'Banks - Diversified', 'Capital Markets', 'Credit Services', 'Insurance - Specialists', 'Insurance - Life', 'Insurance - Property & Casualty', 'Insurance Brokers', 'Insurance - Diversified']
                
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

                t_eps = safe_float(i.get('trailingEps'))
                f_eps = safe_float(i.get('forwardEps'))
                if t_eps == 0 and t_pe > 0: t_eps = p / t_pe
                if f_eps == 0 and f_pe > 0: f_eps = p / f_pe
                
                has_eps_g = False
                if t_eps > 0 and f_eps > 0:
                    eps_g_val = ((f_eps - t_eps) / t_eps) * 100
                    eps_g_str = f"+{eps_g_val:.1f}%" if eps_g_val > 0 else f"{eps_g_val:.1f}%"
                    eps_col = "#3fb950" if eps_g_val > 0 else "#ff7b72"
                    has_eps_g = True
                elif t_eps < 0 and f_eps > 0:
                    eps_g_str = t("흑자전환", "Turnaround")
                    eps_col = "#3fb950"
                elif t_eps > 0 and f_eps < 0:
                    eps_g_str = t("적자전환", "Turn to Loss")
                    eps_col = "#ff7b72"
                elif t_eps < 0 and f_eps < 0:
                    eps_g_str = t("적자지속", "Continued Loss")
                    eps_col = "#ff7b72"
                else:
                    eps_g_str = t("확인불가", "N/A")
                    eps_col = "#8b949e"
                    
                has_ytd = False
                try:
                    hist_ytd = stk.history(period="ytd")
                    if not hist_ytd.empty and len(hist_ytd) >= 2:
                        ytd_start = hist_ytd['Close'].iloc[0]
                        ytd_ret = ((p - ytd_start) / ytd_start) * 100
                        ytd_str = f"+{ytd_ret:.1f}%" if ytd_ret > 0 else f"{ytd_ret:.1f}%"
                        ytd_col = "#3fb950" if ytd_ret > 0 else "#ff7b72"
                        has_ytd = True
                    else:
                        ytd_str = "N/A"
                        ytd_col = "#8b949e"
                except:
                    ytd_str = "N/A"
                    ytd_col = "#8b949e"

                gap_text = ""
                if has_eps_g and has_ytd:
                    gap = ytd_ret - eps_g_val
                    if gap > 0:
                        txt_ko = f"[주가 {gap:.1f}%p 초과 상승 - 과열 유의]"
                        txt_en = f"[Price outpaced by {gap:.1f}%p - Watch for overheating]"
                        gap_text = f" ➔ <span class='highlight'>{t(txt_ko, txt_en)}</span>"
                    elif gap < 0:
                        txt_ko = f"[주가 {abs(gap):.1f}%p 덜 오름 - 기회 가능성]"
                        txt_en = f"[Price lagged by {abs(gap):.1f}%p - Potential opportunity]"
                        gap_text = f" ➔ <span class='good'>{t(txt_ko, txt_en)}</span>"
                    else:
                        gap_text = f" ➔ <span>{t('[기대치와 주가 일치]', '[In line with expectations]')}</span>"
                else:
                    gap_text = f" ➔ <span style='color:#8b949e'>{t('[비교 불가]', '[N/A]')}</span>"
                
                part1 = f"<span style='color:{eps_col}; font-weight:bold;'>{eps_g_str}</span>"
                part2 = f"<span style='color:{ytd_col}; font-weight:bold;'>{ytd_str}</span>"
                eps_vs_ytd_html = part1 + t(" (예상 실적 성장률) vs ", " (Expected EPS Growth) vs ") + part2 + t(" (올해 실제 주가 상승·변동률)", " (YTD Actual Return)") + gap_text

                eps_trend, bps_trend = analyze_trends(stk)
                
                bio_eval = f"<span style='color:#8b949e'>{t('재무제표 데이터 부족으로 확인 불가.', 'Unable to verify due to missing financial data.')}</span>"
                try:
                    bs = stk.balance_sheet
                    if bs is not None and not bs.empty:
                        debt_col = 'Total Debt' if 'Total Debt' in bs.index else ('Total Liabilities Net Minority Interest' if 'Total Liabilities Net Minority Interest' in bs.index else None)
                        eq_col = 'Stockholders Equity' if 'Stockholders Equity' in bs.index else ('Total Equity Gross Minority Interest' if 'Total Equity Gross Minority Interest' in bs.index else None)
                        
                        if debt_col and eq_col:
                            debts = bs.loc[debt_col].dropna().values[:4][::-1]
                            equities = bs.loc[eq_col].dropna().values[:4][::-1]
                            
                            if len(debts) > 0 and len(equities) > 0:
                                curr_d = debts[-1]
                                curr_e = equities[-1]
                                
                                if curr_e > 0:
                                    curr_de = (curr_d / curr_e) * 100
                                    
                                    trend_text = ""
                                    if len(debts) >= 2 and len(equities) >= 2:
                                        past_e = equities[0]
                                        past_d = debts[0]
                                        if past_e > 0:
                                            past_de = (past_d / past_e) * 100
                                            if curr_de < past_de - 5:
                                                trend_text = t(f"최근 {len(debts)}년 부채 감소 추세", f"{len(debts)}Y Declining debt")
                                            elif curr_de > past_de + 5:
                                                trend_text = t(f"최근 {len(debts)}년 부채 증가 추세", f"{len(debts)}Y Increasing debt")
                                            else:
                                                trend_text = t(f"최근 {len(debts)}년 부채 유지", f"{len(debts)}Y Stable debt")
                                        else:
                                            trend_text = t("추세 확인 불가", "Trend N/A")
                                    else:
                                        trend_text = t("단기 데이터", "Short-term data")

                                    if is_financial:
                                        t_ko = f"[특수] 금융/보험주는 고객 예치금이 부채로 잡혀 부채비율({curr_de:.1f}%) 분석이 무의미합니다."
                                        t_en = f"[N/A] D/E ({curr_de:.1f}%) is irrelevant for Financials due to deposits."
                                        bio_eval = "<span style='color:#e3b341;'>" + t(t_ko, t_en) + "</span>"
                                    else:
                                        if curr_de < 50:
                                            t_ko = f"[합격] 현재 부채비율 {curr_de:.1f}% ({trend_text}). 외부 충격에 매우 강한 다윈주의적 생존력을 갖췄습니다."
                                            t_en = f"[Pass] D/E {curr_de:.1f}% ({trend_text}). Strong Darwinian survivability."
                                            bio_eval = "<span class='good'>" + t(t_ko, t_en) + "</span>"
                                        elif curr_de < 120:
                                            t_ko = f"[양호] 현재 부채비율 {curr_de:.1f}% ({trend_text}). 무난한 생존력을 유지 중입니다."
                                            t_en = f"[Good] D/E {curr_de:.1f}% ({trend_text}). Adequate survivability."
                                            bio_eval = "<span style='color:#58a6ff;'>" + t(t_ko, t_en) + "</span>"
                                        else:
                                            t_ko = f"[경고] 현재 부채비율 {curr_de:.1f}% ({trend_text}). 과도한 레버리지로 위기 시 치명적 생존 위협이 존재합니다."
                                            t_en = f"[Warning] D/E {curr_de:.1f}% ({trend_text}). High leverage poses fatal survival risk."
                                            bio_eval = "<span class='highlight'>" + t(t_ko, t_en) + "</span>"
                                else:
                                    t_ko = "[위험] 자본잠식 상태입니다. 생존에 치명적인 위협이 존재합니다."
                                    t_en = "[Danger] Capital impairment detected. Fatal survival risk."
                                    bio_eval = "<span class='highlight'>" + t(t_ko, t_en) + "</span>"
                except:
                    pass

                iv, mos_val, err = calc_custom_dcf(base_fcf, sh, p, ty, final_g, is_financial)
                mos_val = safe_float(mos_val)
                
                iv_best, mos_best, _ = calc_custom_dcf(base_fcf, sh, p, ty, min(final_g * 1.5, 0.25), is_financial)
                iv_worst, mos_worst, _ = calc_custom_dcf(base_fcf, sh, p, ty, max(final_g * 0.5, 0.0), is_financial)
                
                roic_val = real_roic if real_roic is not None else 0
                
                op_title, op_color, op_reason = get_comprehensive_investment_opinion(mos_val, pmos_val, roe, roic_val, erp, final_g, criticism_text, is_financial, pbr)

                st.markdown(f"""
                <div translate="no" style="padding: 18px 20px; border-radius: 8px; border-left: 6px solid {op_color}; background-color: #1c2128; color: #e6edf3; margin-bottom: 25px; margin-top: 10px;">
                    <h3 style="margin: 0 0 12px 0; color: {op_color}; font-size: 1.4rem;">[AI 종합 투자의견] : {op_title}</h3>
                    <span style="color: #c9d1d9; font-size: 0.95rem; display: block; margin-top: 8px;">{op_reason}</span>
                </div>
                """, unsafe_allow_html=True)

                st.divider()

                if is_financial:
                    beginner_summary = t(
                        f"💡 <b>초보자 가이드:</b> 내가 <b>{p_str}</b>을 주고 이 금융/보험사를 사면, 본전을 찾는 데 <b>{f_pe:.1f}년</b>이 걸릴 것으로 예상되며(Fwd PER), 회사는 장사를 통해 내 돈을 1년에 <b>{roe:.1f}%</b>씩(ROE) 불려주고 있습니다. 현재 기업의 장부상 자산 가치 대비 <b>{pbr:.2f}배</b>(PBR)의 가격표가 붙어 있습니다.",
                        f"💡 <b>Beginner Guide:</b> It takes <b>{f_pe:.1f} yrs</b> to break even (Fwd PE), equity grows at <b>{roe:.1f}%/yr</b> (ROE), and priced at <b>{pbr:.2f}x</b> its book value (PBR)."
                    )
                else:
                    beginner_summary = t(
                        f"💡 <b>초보자 가이드:</b> 내가 <b>{p_str}</b>을 주고 이 회사를 사면, 본전을 찾는 데 <b>{f_pe:.1f}년</b>이 걸릴 것으로 예상되며(Fwd PER), 회사는 장사를 통해 내 돈을 1년에 <b>{roe:.1f}%</b>씩(ROE) 불려주고 있습니다.",
                        f"💡 <b>Beginner Guide:</b> It takes <b>{f_pe:.1f} yrs</b> to break even (Fwd PE), and the company grows your money at <b>{roe:.1f}%/yr</b> (ROE)."
                    )

                st.subheader(t("1. 핵심 밸류에이션 지표", "1. Core Valuation Metrics"))
                st.markdown(f"<div style='background-color:#2d333b; padding:12px; border-radius:8px; margin-bottom:15px; font-size:0.95rem; color:#adbac7;'>{beginner_summary}</div>", unsafe_allow_html=True)
                
                if pmos_val > 0:
                    per_mos_str = f"<span class='good'>+[합격] {pmos_val:.1f}% (과거 평균 {a_pe:.1f}배 대비 현재 {f_pe:.1f}배로 저렴하여 할인 구간)</span>"
                elif pmos_val < 0:
                    per_mos_str = f"<span class='highlight'>[주의] {pmos_val:.1f}% (과거 평균 {a_pe:.1f}배 대비 현재 {f_pe:.1f}배로 비싸서 할증 구간)</span>"
                else:
                    per_mos_str = f"확인 필요"

                if is_financial:
                    if roe >= 10: rr_eval = f"<span class='good'>{t('훌륭함 (금융/보험주 기준 탁월한 자본 효율성)', 'Excellent (Great for Financials)')}</span>"
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

                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"- **{t('현재 주가', 'Current Price')}:** {p_str}")
                    st.markdown(f"- **{t('배당 추이', 'Dividend Trend')}:** {div:.2f}% ({div_trend})", unsafe_allow_html=True)
                    st.markdown(f"- **ROE {t('(내 돈 굴리는 이자율)', '(Equity Return)')} / ROIC {t('(진짜 수익률)', '(True Return)')}:** {roe:.2f}% / {roic_str} ➔ {rr_eval}", unsafe_allow_html=True)
                    st.write(f"- **{t('현재 PER (본전 회수 기간)', 'Current PE (Payback Period)')}:** {t_pe:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('Fwd PER (미래 1년 기준)', 'Fwd PE (Next 1Y)')}:** {f_pe:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('5~10년 평균 PER', '5-10Y Avg PE')}:** {a_pe:.2f}{t('배', 'x')}")
                with c2:
                    st.markdown(f"- **{t('PER 안전마진', 'PE Margin of Safety')}:** {per_mos_str}", unsafe_allow_html=True)
                    st.write(f"- **PBR {t('(청산 가치 대비 배수)', '(Price to Book)')}:** {pbr:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('10년물 미국채 금리 (안전 자산)', '10Y US Treasury Yield (Risk-free)')}:** {ty:.2f}%")
                    st.markdown(f"- **{t('예상 이익수익률 (주식의 연간 기대 이자율)', 'Expected Earnings Yield')}:** {ey_str}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('EPS 추세 (최근 4년 1주당 순이익 / 기업의 진짜 벌이 체력)', 'EPS Trend (4 Years / Net Income per Share)')}:** {eps_trend}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('자본/BPS 추세 (최근 4년 1주당 순자산 / 기업의 덩치와 재산 성장)', 'Equity Trend (4 Years / Book Value per Share)')}:** {bps_trend}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('올해시장(eps)컨센서스 vs 실제 주가 괴리', 'Consensus vs YTD Price Gap')}:** {eps_vs_ytd_html}", unsafe_allow_html=True)

                st.divider()
                
                st.subheader(t("2. 10년 DCF (내재가치 3가지 시나리오)", "2. 10-Year DCF (3 Scenarios)"))
                if is_financial:
                    st.write(f"- **{t('추정 적정가 (DCF)', 'Estimated Fair Value (DCF)')}:** {t('🏦 금융 및 보험주는 사업 특성상 고객 예치금/지급준비금이 현금흐름표에 대규모로 부채 처리되어 FCF의 기형적 왜곡이나 착시 적자가 발생합니다. 따라서 본 분석기에서는 무의미한 DCF 연산을 강제 차단하고, PBR 기반 자산가치 필터링 시스템으로 완벽 대체하여 의견을 도출했습니다.', 'DCF model disabled due to financial accounting distortions. Intrinsic worth cross-evaluated using PBR metrics instead.')}")
                elif iv:
                    implied_g = get_implied_g(base_fcf, sh, p, ty)
                    if implied_g is not None:
                        implied_g_str = f"{implied_g*100:.1f}%"
                        implied_text = f"<br><span style='color:#e3b341;'><b>※ 현재 주가({p_str}) 정당화 조건 (역산 DCF):</b> 향후 10년간 매년 <b>{implied_g_str}</b>씩 현금을 더 벌어야 현재 주가가 합리적이라고 볼 수 있습니다. 이 수치가 해당 기업의 한계치를 넘는다면 비상식적 고평가 상태입니다.</span>"
                    else:
                        implied_text = ""

                    st.markdown(f"**[{t('DCF 기본 가정', 'DCF Base Assumptions')}]** {t('할인율', 'Discount Rate')}: {max(ty, 9.0):.1f}% | {dcf_source_txt}{implied_text}", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    c_w, c_b, c_e = st.columns(3)
                    str_g = t("성장률", "Growth")
                    str_fv = t("적정가", "Fair Val")
                    str_mos = t("안전마진", "MoS")
                    
                    val_w = f"{int(iv_worst):,}원" if kr else f"${iv_worst:,.2f}"
                    val_b = f"{int(iv):,}원" if kr else f"${iv:,.2f}"
                    val_e = f"{int(iv_best):,}원" if kr else f"${iv_best:,.2f}"
                    
                    # f-string 중첩을 피하기 위해 안전하게 문자열 포맷팅
                    mos_w_col = '#3fb950' if mos_worst > 0 else '#ff7b72'
                    mos_b_col = '#3fb950' if mos_val > 0 else '#ff7b72'
                    mos_e_col = '#3fb950' if mos_best > 0 else '#ff7b72'
                    
                    html_w = f"<div translate='no' style='background-color:#21262d; color:#e6edf3; padding:15px; border-radius:8px; border-top:4px solid #ff7b72;'><b>{t('📉 최악 (Worst)', '📉 Worst Case')}</b><br>{str_g}: {max(final_g*0.5, 0.0)*100:.1f}%<br>{str_fv}: {val_w}<br>{str_mos}: <span style='color:{mos_w_col}'>{mos_worst:.1f}%</span></div>"
                    html_b = f"<div translate='no' style='background-color:#21262d; color:#e6edf3; padding:15px; border-radius:8px; border-top:4px solid #e3b341;'><b>⚖️ 평균 (Base)</b><br>{str_g}: {final_g*100:.1f}%<br>{str_fv}: {val_b}<br>{str_mos}: <span style='color:{mos_b_col}'>{mos_val:.1f}%</span></div>"
                    html_e = f"<div translate='no' style='background-color:#21262d; color:#e6edf3; padding:15px; border-radius:8px; border-top:4px solid #3fb950;'><b>🚀 최상 (Best)</b><br>{str_g}: {min(final_g*1.5, 0.25)*100:.1f}%<br>{str_fv}: {val_e}<br>{str_mos}: <span style='color:{mos_e_col}'>{mos_best:.1f}%</span></div>"

                    with c_w:
                        st.markdown(html_w, unsafe_allow_html=True)
                    with c_b:
                        st.markdown(html_b, unsafe_allow_html=True)
                    with c_e:
                        st.markdown(html_e, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
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
                        
                        def scale_vals(data_lists, is_kr):
                            all_v = []
                            for lst in data_lists: all_v.extend([abs(x) for x in lst if pd.notna(x)])
                            mv = max(all_v) if all_v else 0
                            
                            if is_kr:
                                if mv >= 1e12: return 1e12, t("(단위: 조 원)", "(Unit: Trillion KRW)")
                                elif mv >= 1e8: return 1e8, t("(단위: 억 원)", "(Unit: 100M KRW)")
                                else: return 1, t("(단위: 원)", "(Unit: KRW)")
                            else:
                                if mv >= 1e9: return 1e9, t("(단위: 10억 달러 [B])", "(Unit: Billion USD)")
                                elif mv >= 1e6: return 1e6, t("(단위: 백만 달러 [M])", "(Unit: Million USD)")
                                else: return 1, t("(단위: 달러)", "(Unit: USD)")

                        c_v1, c_v2 = st.columns(2)
                        with c_v1:
                            if len(rev) == len(years) and len(ni) == len(years):
                                div, u_str = scale_vals([rev, ni], kr)
                                df_rev_ni = pd.DataFrame({t('매출액', 'Revenue'): [x/div for x in rev], t('순이익', 'Net Income'): [x/div for x in ni]}, index=years)
                                st.write(t(f"**[최근 4년 매출 및 순이익]** {u_str}", f"**[4Y Rev & NI Trend]** {u_str}"))
                                st.bar_chart(df_rev_ni, color=["#58a6ff", "#3fb950"], height=300)
                            else:
                                st.caption(t("매출/순이익 시각화 데이터가 부족합니다.", "Insufficient Revenue/Net Income data for visualization."))
                        with c_v2:
                            if len(fcf_chart) == len(years):
                                div, u_str = scale_vals([fcf_chart], kr)
                                df_fcf = pd.DataFrame({t('잉여현금흐름(FCF)', 'Free Cash Flow'): [x/div for x in fcf_chart]}, index=years)
                                st.write(t(f"**[최근 4년 잉여현금흐름(FCF)]** {u_str}", f"**[4Y FCF Trend]** {u_str}"))
                                st.bar_chart(df_fcf, color="#e3b341", height=300)
                            else:
                                st.caption(t("FCF 시각화 데이터가 부족합니다.", "Insufficient FCF data for visualization."))
                except Exception as e:
                    st.caption(t("시각화 데이터를 불러오는 데 실패했습니다.", "Failed to load visualization data."))

                st.divider()

                st.subheader(t("4. 질적 분석 및 리스크 스크리닝", "4. Qualitative Analysis & Risk Screening"))
                
                st.markdown(f"- **CEO:** {ceo_cleaned}")
                
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
                
                if is_financial:
                    if pbr < 0.8: p_txt += f"- PBR: <span class='good'>[합격] ({pbr:.2f}배 - 청산가치 대비 극심한 저평가 상태)</span>"
                    elif pbr < 1.2: p_txt += f"- PBR: <span style='color:#e3b341;'>[적정 가치] ({pbr:.2f}배)</span>"
                    else: p_txt += f"- PBR: <span class='highlight'>[주의] ({pbr:.2f}배 - 장부가 대비 프리미엄 리스크)</span>"
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
                st.markdown(f"- **{t('생물학 (생존력):', 'Biology (Survivability):')}** {bio_eval}", unsafe_allow_html=True)
                st.write(f"- **{t('심리학 (오판 점검):', 'Psychology (Misjudgment):')}** {t('희망 회로나 확증 편향에 빠진 매수가 아닌지 점검하십시오.', 'Check for confirmation bias or wishful thinking.')}")
                st.write(f"- **{t('파급력:', 'Impact:')}** {t('기술 변화가 이 기업에 득인가 독인가?', 'Is technological change a boon or bane for this company?')}")

                st.divider()

                st.subheader(t("7. 비상탈출 (오직 다음 경우에만 할증 시 매도)", "7. Exit Strategy (Sell ONLY if:)"))
                
                # 안전한 문자열 처리
                txt_s_ko = "1. 기업 분석에 치명적인 실수가 있었음을 깨달았을 때.<br>2. 밸류에이션(PBR/PER)이 비상식적으로 지나치게 과열(할증)되었을 때.<br>3. 더 확실하고 안전한 기회(기회비용 고려)를 발견했을 때."
                txt_s_en = "1. You realize a fatal mistake in your initial analysis.<br>2. Valuation (PER/PBR) becomes irrationally overheated (premium).<br>3. You find a much safer and better opportunity (Opportunity Cost)."
                sell_rules = t(txt_s_ko, txt_s_en)
                
                st.markdown(f"<div class='guru-quote'>{sell_rules}</div>", unsafe_allow_html=True)

                st.divider()

                st.subheader(t("거장들의 철학 한마디", "Guru's Philosophy Quotes"))
                st.caption(t("**워런 버핏 (소유권):** 주식은 종이가 아니라 '기업의 소유권'입니다. 내가 지분 100%를 인수한다고 가정하고 분석하십시오.", "**Warren Buffett (Ownership):** Stocks are 'ownership of a business'. Analyze as if you are buying 100% of it."))
                st.caption(t("**워런 버핏 (안전마진):** 1만 파운드 트럭이 지나갈 다리를 지을 때, 3만 파운드를 견디도록 설계하는 것이 바로 안전마진입니다.", "**Warren Buffett (Margin of Safety):** When you build a bridge, you insist it can carry 30,000 pounds, but you only drive 10,000 pound trucks across it."))
                st.caption(t("**찰리 멍거 (훌륭한 기업):** 훌륭한 기업이 현저히 싼 가격에 거래되는 일은 거의 없습니다. 적당한 기업을 훌륭한 가격에 사는 것보다, 훌륭한 기업을 적당한 가격에 사는 것이 훨씬 낫습니다.", "**Charlie Munger (Great Business):** It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price."))
                st.caption(t("**찰리 멍거 (능력범위):** 당신의 '능력 범위'를 명확히 아는 것이 가장 중요합니다. 전문가의 반론에 논리적으로 재반박할 수 없다면, 그것은 당신의 능력 밖입니다.", "**Charlie Munger (Circle of Competence):** Knowing what you don't know is more useful than being brilliant. If you can't logically refute an expert's counterargument, it's outside your circle."))
                st.caption(t("**필립 피셔 (타이밍):** 가장 좋은 매수 타이밍은 상업화 초기 단계의 일시적 문제, 미스터 마켓의 우울증, 그리고 일시적이고 해결 가능한 경영상의 악재가 발생했을 때입니다.", "**Philip Fisher (Timing):** The best time to buy is when there are temporary problems in early commercialization, market depression, or temporary/solvable management issues."))

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
            
            if (df["비중(%)"] == 0.0).any():
                st.caption(t("※ 비중이 0.00%로 표기된 종목은 비중 미상이거나 전량 매도된 종목입니다. (이건 확인이 필요한 부분입니다)", "※ Stocks with 0.00% weight are unknown or fully sold. (Needs verification)"))
            
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
# 탭 3: 시가총액 랭킹 TOP 30
# ==========================================
with tab3:
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
# 탭 4: 주식 용어 사전 
# ==========================================
with tab4:
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
# 탭 5: VALUE 철학
# ==========================================
with tab5:
    phil_title1 = t("가치투자의 진정한 의미와 의의: 투기(Speculation) vs 투자(Investment)", "The True Meaning of Value Investing: Speculation vs. Investment")
    phil_p1 = t("주식 시장에는 두 부류의 참여자가 있습니다. 가격 변동에 베팅하며 누군가 나보다 더 비싼 가격에 사주기만을 바라는 '투기자(Speculator)', 그리고 기업의 비즈니스 모델과 내재가치를 분석하여 성장을 함께 나누고자 하는 '투자자(Investor)'입니다.", "There are two types of participants in the stock market: 'Speculators' who bet on price fluctuations, hoping someone will buy at a higher price, and 'Investors' who analyze business models and intrinsic value to share in the company's growth.")
    phil_p2 = t("가치투자(Value Investing)는 매일같이 요동치는 주가의 이면을 꿰뚫어 보고, 그 기업이 실제로 창출하는 현금흐름과 자산에 집중하는 행위입니다. 시장의 광기나 패닉에 휩쓸리지 않고, '가격(Price)은 우리가 지불하는 것이며, 가치(Value)는 우리가 얻는 것'이라는 확고한 믿음을 실천하는 것이 가치투자의 진정한 의의입니다.", "Value investing focuses on the cash flows and assets a company actually generates, seeing through daily price fluctuations. It is the practice of maintaining the firm belief that 'Price is what you pay, Value is what you get,' without being swept away by market mania or panic.")
    phil_title2 = t("워런 버핏과 찰리 멍거의 핵심 철학", "Core Philosophy of Warren Buffett & Charlie Munger")
    phil_li1 = t("**기업의 소유권 (Business Ownership):** 주식은 단순한 거래의 수단이나 종이가 아닙니다. 주식을 산다는 것은 기업의 지분을 인수하여 진정한 '동업자'가 되는 것입니다. 지분 100%를 인수한다는 마음가짐으로 비즈니스를 해부해야 합니다.", "**Business Ownership:** Stocks are not just trading instruments or pieces of paper. Buying a stock means acquiring an equity stake and becoming a true 'partner'. You must dissect the business as if you were buying 100% of it.")
    phil_li2 = t("**미스터 마켓 (Mr. Market):** 시장은 매일 기분에 따라 터무니없이 비싼 가격이나 싼 가격을 부르는 변덕스러운 동업자일 뿐입니다. 시장은 선생님이 아니라, 가격이 내재가치보다 현저히 낮을 때만 이용해야 하는 도구입니다.", "**Mr. Market:** The market is merely a fickle partner who quotes absurdly high or low prices depending on its daily mood. The market is not your teacher, but a tool to be used only when prices are significantly below intrinsic value.")
    phil_li3 = t("**경영진의 정직성 (Integrity of Management):** 재무적 성과만큼이나 중요한 것이 경영진의 도덕성입니다. 비즈니스 모델이 훌륭해도 경영진의 정직성에 의구심이 든다면 미련 없이 동업을 끝내야 합니다. 신뢰할 수 없는 사람과는 좋은 거래 파트너가 될 수 없습니다.", "**Integrity of Management:** Management's morality is just as important as financial performance. Even if the business is great, if you doubt their integrity, you must walk away. You cannot make a good deal with a bad person.")
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
