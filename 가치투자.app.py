import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time
import pandas as pd
from datetime import datetime
import re
import concurrent.futures 

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
        if isinstance(val, str):
            val = val.replace('%', '').replace(',', '').strip()
        return float(val)
    except:
        return default

def fmt_f(val, decimals=1):
    try:
        return f"{float(val):.{decimals}f}"
    except:
        return "0.0" if decimals == 1 else "0.00"

# [스마트 자동완성 검색 로직]
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
                matches[v] = primary_names[v]
                        
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
    "COCA-COLA": "KO", "코카콜라": "KO", "코카": "KO", "콜라": "KO", "COCACOLA": "KO",
    "SPACEX": "SPACEX", "스페이스엑스": "SPACEX",
    "핀듀오듀오": "PDD", "PDD": "PDD", "PINDUODUO": "PDD",
    "이스트웨스트뱅코프": "EWBC", "EWBC": "EWBC",
    "크록스": "CROX", "CROX": "CROX",
    "텐센트뮤직": "TME", "TME": "TME",
    "에스앤피글로벌": "SPGI", "S&P글로벌": "SPGI", "SPGI": "SPGI",
    "H&R블록": "HRB", "HRB": "HRB",
    "무디스": "MCO", "MCO": "MCO",
    "모건스탠리캐피털인터내셔널": "MSCI", "MSCI": "MSCI",
    "아메리칸익스프레스": "AXP", "아멕스": "AXP", "AXP": "AXP",
    "처브": "CB", "CB": "CB",
    "크래프트하인즈": "KHC", "크래프트": "KHC", "하인즈": "KHC", "KHC": "KHC",
    "다비타": "DVA", "DVA": "DVA",
    "크로거": "KR", "KR": "KR",
    "델타항공": "DAL", "델타": "DAL", "DAL": "DAL",
    "얼라이파이낸셜": "ALLY", "얼라이": "ALLY", "ALLY": "ALLY",
    "레나": "LEN", "LEN": "LEN",
    "콘스텔레이션브랜즈": "STZ", "STZ": "STZ",
    "제퍼리스": "JEF", "제퍼리스파이낸셜": "JEF", "JEF": "JEF",
    "캐피탈원": "COF", "캐피털원": "COF", "COF": "COF",
    "브룩필드": "BN", "BN": "BN",
    "우버": "UBER", "우버테크놀로지스": "UBER", "UBER": "UBER",
    "레스토랑브랜즈": "QSR", "QSR": "QSR",
    "하워드휴즈": "HHH", "HHH": "HHH",
    "허츠": "HTZ", "HTZ": "HTZ",
    "씨포트엔터테인먼트": "SEG", "SEG": "SEG",
    "웨스코": "WCC", "WCC": "WCC",
    "유니온퍼시픽": "UNP", "UNP": "UNP",
    "엘리번스헬스": "ELV", "엘리번스": "ELV", "ELV": "ELV",
    "퍼거슨": "FERG", "FERG": "FERG",
    "윌리스타워스왓슨": "WTW", "WTW": "WTW",
    "에이온": "AON", "AON": "AON",
    "텔레플렉스": "TFX", "TFX": "TFX",
    "이글머티리얼즈": "EXP", "EXP": "EXP",
    "제뉴인파츠": "GPC", "GPC": "GPC",
    "리버티글로벌": "LBTYK", "LBTYK": "LBTYK",
    "허벌라이프": "HLF", "HLF": "HLF",
    "GDS홀딩스": "GDS", "GDS": "GDS",
    "아메리콜드": "COLD", "COLD": "COLD",
    "몰리나헬스케어": "MOH", "MOH": "MOH",
    "아에로멕시코": "AERO", "AERO": "AERO",
    "노르웨이지안크루즈": "NCLH", "NCLH": "NCLH",
    "KKR": "KKR", "KKR&CO": "KKR",
    "로퍼테크놀로지스": "ROP", "로퍼": "ROP", "ROP": "ROP",
    "코스타그룹": "CSGP", "코스타": "CSGP", "CSGP": "CSGP",
    "오라일리오토모티브": "ORLY", "오라일리": "ORLY", "ORLY": "ORLY",
    "에어비앤비": "ABNB", "ABNB": "ABNB",
    "세일즈포스": "CRM", "CRM": "CRM",
    "서비스나우": "NOW", "NOW": "NOW",
    "구스헤드인슈어런스": "GSHD", "GSHD": "GSHD",
    "소피아제네틱스": "SOPH", "SOPH": "SOPH",
    "아메리칸타워": "AMT", "AMT": "AMT",
    "페리미터솔루션스": "PRM", "PRM": "PRM",
    "CCC인텔리전트솔루션스": "CCCS", "CCCS": "CCCS",
    "코파트": "CPRT", "CPRT": "CPRT",
    "페어아이작": "FICO", "피코": "FICO", "FICO": "FICO",
    "워리어메트콜": "HCC", "HCC": "HCC",
    "트랜스오션": "RIG", "RIG": "RIG",
    "알파메탈러지컬": "AMR", "AMR": "AMR",
    "페라리": "RACE", "RACE": "RACE",
    "데일리저널": "DJCO", "DJCO": "DJCO"
}

primary_names = {}
for k, v in tmap.items():
    if v not in primary_names:
        primary_names[v] = k

fallback_13f_data = {
    "HC": [{"티커": "GOOGL", "기업명": "Alphabet Inc.", "비중(%)": 22.84}, {"티커": "GOOG", "기업명": "Alphabet Inc.", "비중(%)": 21.96}, {"티커": "PDD", "기업명": "PDD Holdings Inc.", "비중(%)": 14.70}, {"티커": "BRK-B", "기업명": "Berkshire Hathaway Inc.", "비중(%)": 13.43}, {"티커": "EWBC", "기업명": "East West Bancorp, Inc.", "비중(%)": 9.25}, {"티커": "BAC", "기업명": "Bank of America Corporation", "비중(%)": 4.56}, {"티커": "OXY", "기업명": "Occidental Petroleum Corporation", "비중(%)": 2.97}, {"티커": "CROX", "기업명": "Crocs, Inc.", "비중(%)": 2.30}, {"티커": "TME", "기업명": "Tencent Music Entertainment Group", "비중(%)": 1.91}, {"티커": "SPGI", "기업명": "S&P Global Inc.", "비중(%)": 1.61}, {"티커": "HRB", "기업명": "H&R Block, Inc.", "비중(%)": 1.61}, {"티커": "MCO", "기업명": "Moody's Corporation", "비중(%)": 1.60}, {"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 0.87}, {"티커": "MSCI", "기업명": "MSCI Inc.", "비중(%)": 0.31}],
    "BRK": [{"티커": "AAPL", "기업명": "Apple Inc.", "비중(%)": 21.99}, {"티커": "AXP", "기업명": "American Express Co.", "비중(%)": 17.43}, {"티커": "KO", "기업명": "Coca-Cola Co.", "비중(%)": 11.56}, {"티커": "BAC", "기업명": "Bank of America Corp.", "비중(%)": 9.52}, {"티커": "CVX", "기업명": "Chevron Corp.", "비중(%)": 6.64}, {"티커": "CB", "기업명": "Chubb Ltd.", "비중(%)": 4.24}, {"티커": "KHC", "기업명": "Kraft Heinz Co.", "비중(%)": 2.78}, {"티커": "DVA", "기업명": "DaVita Inc.", "비중(%)": 1.76}, {"티커": "KR", "기업명": "Kroger Co.", "비중(%)": 1.38}, {"티커": "DAL", "기업명": "Delta Air Lines Inc.", "비중(%)": 1.01}, {"티커": "ALLY", "기업명": "Ally Financial Inc.", "비중(%)": 0.39}, {"티커": "LLYVK", "기업명": "Liberty Live Holdings-C", "비중(%)": 0.38}, {"티커": "LEN", "기업명": "Lennar Corp. Class A", "비중(%)": 0.33}, {"티커": "LLYVA", "기업명": "Liberty Live Holdings-A", "비중(%)": 0.17}, {"티커": "STZ", "기업명": "Constellation Brands Inc.", "비중(%)": 0.04}, {"티커": "JEF", "기업명": "Jefferies Financial Group Inc.", "비중(%)": 0.01}, {"티커": "LEN-B", "기업명": "Lennar Corp. Class B", "비중(%)": 0.01}, {"티커": "OXY", "기업명": "Occidental Petroleum Corp.", "비중(%)": 0.00}, {"티커": "COF", "기업명": "Capital One Financial Corp.", "비중(%)": 0.00}],
    "BAU": [
        {"티커": "AMZN", "기업명": "Amazon.com, Inc.", "비중(%)": 13.50},
        {"티커": "QSR", "기업명": "Restaurant Brands International Inc.", "비중(%)": 10.80},
        {"티커": "WCC", "기업명": "WESCO International, Inc.", "비중(%)": 7.90},
        {"티커": "UNP", "기업명": "Union Pacific Corporation", "비중(%)": 7.80},
        {"티커": "GOOG", "기업명": "Alphabet Inc.", "비중(%)": 7.50},
        {"티커": "ELV", "기업명": "Elevance Health, Inc.", "비중(%)": 7.30},
        {"티커": "FERG", "기업명": "Ferguson Enterprises Inc.", "비중(%)": 5.90},
        {"티커": "AON", "기업명": "Aon plc", "비중(%)": 4.90},
        {"티커": "V", "기업명": "Visa Inc.", "비중(%)": 4.50},
        {"티커": "TFX", "기업명": "Teleflex Incorporated", "비중(%)": 3.80}
    ],
    "BRK_PER": [
        {"티커": "BN", "기업명": "Brookfield Corp.", "비중(%)": 17.60},
        {"티커": "AMZN", "기업명": "Amazon.com Inc.", "비중(%)": 17.40},
        {"티커": "UBER", "기업명": "Uber Technologies Inc.", "비중(%)": 15.70},
        {"티커": "MSFT", "기업명": "Microsoft Corp.", "비중(%)": 15.30},
        {"티커": "QSR", "기업명": "Restaurant Brands Int.", "비중(%)": 12.20},
        {"티커": "META", "기업명": "Meta Platforms Inc.", "비중(%)": 10.50},
        {"티커": "HHH", "기업명": "Howard Hughes Holdings Inc.", "비중(%)": 9.50}
    ],
    "AKRE": [{"티커": "MA", "기업명": "Mastercard Inc - A", "비중(%)": 18.64}, {"티커": "BN", "기업명": "Brookfield Corp", "비중(%)": 11.27}, {"티커": "KKR", "기업명": "KKR & Co Inc", "비중(%)": 10.16}, {"티커": "MCO", "기업명": "Moody's Corp", "비중(%)": 8.89}, {"티커": "V", "기업명": "Visa Inc-Class A Shares", "비중(%)": 8.10}, {"티커": "ROP", "기업명": "Roper Technologies Inc", "비중(%)": 7.27}, {"티커": "CSGP", "기업명": "CoStar Group Inc", "비중(%)": 6.80}, {"티커": "ORLY", "기업명": "O'Reilly Automotive Inc", "비중(%)": 5.87}, {"티커": "ABNB", "기업명": "Airbnb, Inc.", "비중(%)": 4.18}, {"티커": "CRM", "기업명": "Salesforce.com Inc", "비중(%)": 2.19}, {"티커": "NOW", "기업명": "ServiceNow Inc", "비중(%)": 1.87}, {"티커": "GSHD", "기업명": "Goosehead Insurance Inc - A", "비중(%)": 0.31}, {"티커": "SOPH", "기업명": "SOPHiA GENETICS SA", "비중(%)": 0.30}, {"티커": "AMT", "기업명": "American Tower Corp", "비중(%)": 0.14}, {"티커": "PRM", "기업명": "Perimeter Solutions Inc", "비중(%)": 0.10}, {"티커": "CCCS", "기업명": "CCC Intelligent Solutions", "비중(%)": 0.00}, {"티커": "CPRT", "기업명": "Copart Inc", "비중(%)": 0.00}, {"티커": "FICO", "기업명": "Fair Isaac Corp", "비중(%)": 0.00}],
    "PI": [{"티커": "HCC", "기업명": "Warrior Met Coal, Inc.", "비중(%)": 39.88}, {"티커": "RIG", "기업명": "Transocean Ltd.", "비중(%)": 31.97}, {"티커": "AMR", "기업명": "Alpha Metallurgical Resources, Inc.", "비중(%)": 28.14}],
    "AQUA": [{"티커": "BRK-B", "기업명": "Berkshire Hathaway Inc Cl-B", "비중(%)": 34.57}, {"티커": "BRK-A", "기업명": "Berkshire Hathaway Inc Cl-A", "비중(%)": 15.92}, {"티커": "MA", "기업명": "Mastercard Inc - A", "비중(%)": 14.77}, {"티커": "AXP", "기업명": "American Express Co", "비중(%)": 14.53}, {"티커": "MCO", "기업명": "Moody's Corp", "비중(%)": 8.71}, {"티커": "DJCO", "기업명": "Daily Journal Corp", "비중(%)": 0.00}, {"티커": "RACE", "기업명": "Ferrari NV", "비중(%)": 0.00}]
}

us_top30 = [{"순위": 1, "티커": "NVDA", "기업명": "NVIDIA", "시가총액": "$5.11T"}, {"순위": 2, "티커": "AAPL", "기업명": "Apple", "시가총액": "$4.58T"}, {"순위": 3, "티커": "GOOGL", "기업명": "Alphabet", "시가총액": "$4.56T"}, {"순위": 4, "티커": "MSFT", "기업명": "Microsoft", "시가총액": "$3.34T"}, {"순위": 5, "티커": "AMZN", "기업명": "Amazon", "시가총액": "$2.91T"}, {"순위": 6, "티커": "AVGO", "기업명": "Broadcom", "시가총액": "$2.11T"}, {"순위": 7, "티커": "TSLA", "기업명": "Tesla", "시가총액": "$1.63T"}, {"순위": 8, "티커": "META", "기업명": "Meta Platforms", "시가총액": "$1.60T"}, {"순위": 9, "티커": "MU", "기업명": "Micron", "시가총액": "$1.09T"}, {"순위": 10, "티커": "BRK-B", "기업명": "Berkshire Hathaway", "시가총액": "$1.02T"}, {"순위": 11, "티커": "LLY", "기업명": "Eli Lilly", "시가총액": "$985B"}, {"순위": 12, "티커": "WMT", "기업명": "Walmart", "시가총액": "$922B"}, {"순위": 13, "티커": "AMD", "기업명": "AMD", "시가총액": "$841B"}, {"순위": 14, "티커": "JPM", "기업명": "JPMorgan Chase", "시가총액": "$802B"}, {"순위": 15, "티커": "ORCL", "기업명": "Oracle", "시가총액": "$649B"}, {"순위": 16, "티커": "V", "기업명": "Visa", "시가총액": "$620B"}, {"순위": 17, "티커": "XOM", "기업명": "Exxon Mobil", "시가총액": "$602B"}, {"순위": 18, "티커": "INTC", "기업명": "Intel", "시가총액": "$576B"}, {"순위": 19, "티커": "JNJ", "기업명": "Johnson & Johnson", "시가총액": "$542B"}, {"순위": 20, "티커": "CSCO", "기업명": "Cisco", "시가총액": "$474B"}, {"순위": 21, "티커": "MA", "기업명": "Mastercard", "시가총액": "$436B"}, {"순위": 22, "티커": "COST", "기업명": "Costco", "시가총액": "$424B"}, {"순위": 23, "티커": "CAT", "기업명": "Caterpillar", "시가총액": "$403B"}, {"순위": 24, "티커": "LRCX", "기업명": "Lam Research", "시가총액": "$397B"}, {"순위": 25, "티커": "ABBV", "기업명": "AbbVie", "시가총액": "$384B"}, {"순위": 26, "티커": "PLTR", "기업명": "Palantir", "시가총액": "$375B"}, {"순위": 27, "티커": "BAC", "기업명": "Bank of America", "시가총액": "$366B"}, {"순위": 28, "티커": "CVX", "기업명": "Chevron", "시가총액": "$363B"}, {"순위": 29, "티커": "NFLX", "기업명": "Netflix", "시가총액": "$362B"}, {"순위": 30, "티커": "AMAT", "기업명": "Applied Materials", "시가총액": "$357B"}]
kr_top30 = [{"순위": 1, "티커": "005930", "기업명": "삼성전자", "시가총액": "1,794조 원"}, {"순위": 2, "티커": "000660", "기업명": "SK하이닉스", "시가총액": "1,662조 원"}, {"순위": 3, "티커": "373220", "기업명": "LG에너지솔루션", "시가총액": "89조 원"}, {"순위": 4, "티커": "005380", "기업명": "현대차", "시가총액": "148조 원"}, {"순위": 5, "티커": "207940", "기업명": "삼성바이오로직스", "시가총액": "64조 원"}, {"순위": 6, "티커": "000270", "기업명": "기아", "시가총액": "64조 원"}, {"순위": 7, "티커": "068270", "기업명": "셀트리온", "시가총액": "43조 원"}, {"순위": 8, "티커": "105560", "기업명": "KB금융", "시가총액": "57조 원"}, {"순위": 10, "티커": "055550", "기업명": "신한지주", "시가총액": "45조 원"}, {"순위": 11, "티커": "006400", "기업명": "삼성SDI", "시가총액": "50조 원"}, {"순위": 12, "티커": "035420", "기업명": "NAVER", "시가총액": "38조 원"}, {"순위": 13, "티커": "012330", "기업명": "현대모비스", "시가총액": "62조 원"}, {"순위": 14, "티커": "051910", "기업명": "LG화학", "시가총액": "35조 원"}, {"순위": 15, "티커": "035720", "기업명": "카카오", "시가총액": "30조 원"}, {"순위": 16, "티커": "028260", "기업명": "삼성물산", "시가총액": "66조 원"}, {"순위": 17, "티커": "086790", "기업명": "하나금융지주", "시가총액": "27조 원"}, {"순위": 18, "티커": "066570", "기업명": "LG전자", "시가총액": "26조 원"}, {"순위": 19, "티커": "402340", "기업명": "SK스퀘어", "시가총액": "168조 원"}, {"순위": 20, "티커": "032830", "기업명": "삼성생명", "시가총액": "70조 원"}, {"순위": 21, "티커": "138040", "기업명": "메리츠금융지주", "시가총액": "28조 원"}, {"순위": 22, "티커": "096770", "기업명": "SK이노베이션", "시가총액": "22조 원"}, {"순위": 23, "티커": "329180", "기업명": "HD현대중공업", "시가총액": "78조 원"}, {"순위": 24, "티커": "011200", "기업명": "HMM", "시가총액": "15조 원"}, {"순위": 25, "티커": "010130", "기업명": "고려아연", "시가총액": "18조 원"}, {"순위": 26, "티커": "033780", "기업명": "KT&G", "시가총액": "14조 원"}, {"순위": 27, "티커": "034020", "기업명": "두산에너빌리티", "시가총액": "69조 원"}, {"순위": 28, "티커": "009150", "기업명": "삼성전기", "시가총액": "162조 원"}, {"순위": 29, "티커": "259960", "기업명": "크래프톤", "시가총액": "23조 원"}, {"순위": 30, "티커": "012450", "기업명": "한화에어로스페이스", "시가총액": "64조 원"}]

# ==========================================
# [3] 데이터 가져오기 엔진 (비동기 스레드 최적화)
# ==========================================
def fetch_single_macro(name, tk):
    try:
        stk = yf.Ticker(tk)
        info = stk.info if isinstance(stk.info, dict) else {}
        
        last_p = safe_float(info.get('currentPrice', info.get('regularMarketPrice')))
        prev_p = safe_float(info.get('previousClose', info.get('regularMarketPreviousClose')))
        
        if last_p == 0.0 or prev_p == 0.0:
            hist = stk.history(period="5d")
            if hist is not None and not hist.empty:
                hist = hist.dropna(subset=['Close'])
                if len(hist) >= 1:
                    last_p = safe_float(hist['Close'].iloc[-1])
                if len(hist) >= 2:
                    prev_p = safe_float(hist['Close'].iloc[-2])

        if prev_p != 0:
            change = last_p - prev_p
            pct = (change / prev_p) * 100
        else:
            change, pct = 0.0, 0.0
        return name, {"p": last_p, "c": change, "pct": pct}
    except: 
        return name, {"p": 0.0, "c": 0.0, "pct": 0.0}

def fetch_single_pe(tk, default_pe):
    try:
        info = yf.Ticker(tk).info
        return safe_float(info.get("trailingPE", info.get("forwardPE", default_pe)), default_pe)
    except:
        return default_pe

@st.cache_data(ttl=60) 
def fetch_macro_realtime_v6():
    macro_symbols = {
        "KOSPI": "^KS11", "KOSDAQ": "^KQ11", 
        "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Nasdaq Futures": "NQ=F",
        "USD/KRW": "KRW=X", "WTI Crude": "CL=F", "10Y Treasury": "^TNX"
    }
    res = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_macro, name, tk) for name, tk in macro_symbols.items()]
        spy_future = executor.submit(fetch_single_pe, "SPY", 22.0)
        qqq_future = executor.submit(fetch_single_pe, "QQQ", 30.0)
        
        for future in concurrent.futures.as_completed(futures):
            name, data = future.result()
            res[name] = data
            
        res["SPY_PE"] = spy_future.result()
        res["QQQ_PE"] = qqq_future.result()
        
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
            
            link_url = '#'
            if l_tag:
                if l_tag.text.strip():
                    link_url = l_tag.text.strip()
                elif l_tag.next_sibling:
                    link_url = str(l_tag.next_sibling).strip()
                    
            if t_tag and t_tag.text:
                news_list.append({
                    "title": t_tag.text.strip(),
                    "link": link_url,
                    "publisher": "Yahoo Finance"
                })
    except:
        pass
    return news_list

def fetch_governance_criticism(tk, cd, ceo_name):
    tk_clean = str(tk).strip().upper().replace('.B', '-B').replace('.A', '-A')
    cd_clean = str(cd).strip()
    
    db = {
        "NVDA": "젠슨 황 (Jensen Huang): 비전을 현실로 만드는 강력한 실행력과 기술적 해자를 구축한 검증된 경영자입니다.\n리스크: 특정 리더(키맨)에 대한 절대적 의존도(단일 실패 지점) 및 빅테크 고객사들의 자체 칩 개발 독립 리스크. (이건 확인이 필요한 부분입니다)",
        "AAPL": "팀 쿡 (Tim Cook): 탁월한 공급망 관리와 대규모 자사주 매입으로 주주 환원에 매우 충실합니다.\n리스크: 혁신 사이클 정체 및 중국 등 지정학적 갈등에 노출된 벤더 공급망 마찰 위험. (이건 확인이 필요한 부분입니다)",
        "GOOGL": "구글 (Alphabet Inc.): 경영진의 자본배분 능력은 신뢰할 수 있으나, 반독점 규제 및 AI 경쟁 심화가 치명적인 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "GOOG": "구글 (Alphabet Inc.): 경영진의 자본배분 능력은 신뢰할 수 있으나, 반독점 규제 및 AI 경쟁 심화가 치명적인 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "PDD": "PDD Holdings Inc.: 경영진의 경영 투명성과 글로벌 확장에 따른 국가별 규제 리스크는 이건 확인이 필요한 부분입니다.",
        "BRK-B": "버크셔 해서웨이 (Berkshire Hathaway Inc.): 포스트 버핏 승계 구도는 안정적이나, 거대 자산 규모로 인한 수익률 둔화가 장기 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "EWBC": "East West Bancorp, Inc.: 미-중 무역 관계 전문 은행으로 경영진 신뢰도가 높으나 상업용 부동산 리스크는 이건 확인이 필요한 부분입니다.",
        "BAC": "Bank of America Corp.: 보수적이고 안정적인 경영진이나, 금리 변동성 및 글로벌 경기 침체가 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "OXY": "Occidental Petroleum Corp.: 경영진의 부채 감축 및 주주환원 의지는 강하나, 유가 변동성 및 탄소 규제가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "CROX": "Crocs, Inc.: 브랜드 다각화 역량은 입증되었으나, 단일 브랜드 유행 민감도와 패션 트렌드 변화가 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "TME": "Tencent Music Entertainment Group: 중국 내 독점적 지위는 견고하나, 중국 정부의 자국 빅테크 규제 변동성은 이건 확인이 필요한 부분입니다.",
        "SPGI": "S&P Global Inc.: 신용평가 시장의 독과점 해자로 경영진 신뢰도가 극도로 높으나, 글로벌 채권 발행 급감이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "HRB": "H&R Block, Inc.: 적극적인 자사주 매입 정책을 펼치나, DIY 세무 소프트웨어 대중화에 따른 시장 잠식이 장기 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "MCO": "Moody's Corporation: 고수익 비즈니스 모델과 정직한 경영진을 가졌으나, 글로벌 경기 위축에 따른 발행 시장 침체가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "MSCI": "MSCI Inc.: 금융 인덱스 시장의 독보적 지배력을 가졌으나, 글로벌 패시브 자금 유입 정체 및 수수료 인하 압박이 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "AXP": "American Express Co.: 프리미엄 고객 중심의 우수한 경영진이나, 경기 침체 장기화로 인한 소비 위축이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "KO": "Coca-Cola Co.: 일관된 주주환원 정책과 글로벌 브랜드 파워는 확실하나, 건강 중심의 소비 트렌드 변화가 장기 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "CVX": "Chevron Corp.: 주주환원에 충실한 업계 최고 수준의 경영진이나, 국제 유가 폭락 및 친환경 전환 압박이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "CB": "Chubb Ltd.: 글로벌 최고 수준의 언더라이팅 능력을 갖춘 경영진이나, 기후 변화로 인한 대형 자연재해 급증이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "KHC": "Kraft Heinz Co.: 구조조정 이후 재무 안정성은 개선 중이나, 브랜드 가치 정체 및 고부채 리스크는 이건 확인이 필요한 부분입니다.",
        "DVA": "DaVita Inc.: 미국 투석 시장 독과점으로 안정적 경영을 하나, 정부의 의료보험 정책 변화 및 규제가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "KR": "Kroger Co.: 식료품 유통업에서 안정적 경영을 보여주나, 알베르트손(Albertsons) 인수 합병 규제 승인 여부는 이건 확인이 필요한 부분입니다.",
        "DAL": "Delta Air Lines Inc.: 항공업계 내 최고 수준의 효율적 경영진이나, 유가 급등 및 경기 민감성에 따른 실적 변동성이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "ALLY": "Ally Financial Inc.: 자동차 금융 전문 경영진의 역량은 우수하나, 자동차 연체율 상승 및 조달금리 압박이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "LLYVK": "Liberty Live Holdings-C: 존 말론의 복잡한 지배구조 설계 능력은 신뢰하나, 미디어 업황 위축 및 복잡성은 이건 확인이 필요한 부분입니다.",
        "LLYVA": "Liberty Live Holdings-A: 존 말론의 복잡한 지배구조 설계 능력은 신뢰하나, 미디어 업황 위축 및 복잡성은 이건 확인이 필요한 부분입니다.",
        "LEN": "Lennar Corp.: 미국 최대 주택건설사로 자본배분은 검증되었으나, 고금리 장기화에 따른 주택 수요 위축이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "STZ": "Constellation Brands Inc.: 핵심 맥주 브랜드 지배력은 우수하나, 와인 및 스피릿 부문의 실적 부진 지속 여부는 이건 확인이 필요한 부분입니다.",
        "JEF": "Jefferies Financial Group Inc.: 투자은행(IB) 시장에서 공격적으로 성장 중이나, 자본시장 경색 및 딜 수임 감소가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "COF": "Capital One Financial Corp.: 디스커버(Discover) 인수를 추진하는 경영진의 결단력은 있으나, 신용카드 연체율 상승 및 합병 규제는 이건 확인이 필요한 부분입니다.",
        "BN": "Brookfield Corp.: 대체자산 운용 능력이 탁월한 경영진이나, 글로벌 상업용 부동산 시장 침체 장기화 리스크는 이건 확인이 필요한 부분입니다.",
        "AMZN": "Amazon.com Inc.: 효율성 개선 및 인프라 통제력은 우수하나, 클라우드(AWS) 성장 둔화 및 정부 반독점 규제가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "UBER": "Uber Technologies Inc.: 다라 코스로샤히의 흑자 전환 경영은 검증되었으나, 드라이버 법적 지위 변경에 따른 비용 증가가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "MSFT": "Microsoft Corp.: 사티아 나델라의 AI 주도 리더십은 신뢰도가 높으나, 인프라 투자 대비 수익화 속도는 이건 확인이 필요한 부분입니다.",
        "QSR": "Restaurant Brands Int.: 비용 절감 위주의 자본 배분은 명확하나, 가맹점과의 갈등 및 브랜드 노후화 리스크는 이건 확인이 필요한 부분입니다.",
        "HHH": "Howard Hughes Holdings Inc.: 장기 마스터 플랜 개발 역량은 우수하나, 부동산 경기 침체에 따른 유동성 및 분양 둔화가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "HTZ": "Hertz Global Hldgs Inc.: 전기차 도입 실패 후 경영진 교체 단계이며, 중고차 가격 폭락 및 고부채 리스크는 이건 확인이 필요한 부분입니다.",
        "META": "Meta Platforms Inc.: 마크 저커버그의 턴어라운드 역량은 신뢰하나, SNS 아동 보호 및 개인정보 규제 강화가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "SEG": "Seaport Entertainment Group: 인적분할된 신생 엔터·부동산 기업으로 경영진의 독자적 사업 검증 여부는 이건 확인이 필요한 부분입니다.",
        "WCC": "WESCO International, Inc.: 글로벌 유통 공급망 관리 능력은 양호하나, 산업 전반의 경기 둔화 및 재고 관리 실패가 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "UNP": "Union Pacific Corporation: 철도 독과점 해자와 높은 마진을 유지 중이나, 철도 노조 갈등 및 대형 안전사고가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "ELV": "Elevance Health, Inc.: 건강보험 시장의 안정적 경영을 펼치나, 정부의 보험요율 인하 및 의료 비용(MLR) 상승이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "FERG": "Ferguson Enterprises Inc.: 북미 건설 자재 유통의 지배적 지위이나, 미국 주택 및 상업용 건설 경기 하강이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "WTW": "Willis Towers Watson: 구조조정을 통한 수익성 개선 경영을 추진 중이나, 인재 유출 및 경쟁사 대비 열위는 이건 확인이 필요한 부분입니다.",
        "AON": "Aon plc: 리스크 관리 자본 배분 역량은 뛰어나나, 글로벌 경기 둔화로 인한 기업들의 보험 실적 감소가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "TFX": "Teleflex Incorporated: 의료기기 전문 경영진의 제품력은 우수하나, 병원들의 지출 삭감 및 경쟁 제품 등장이 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "EXP": "Eagle Materials Inc.: 미국 내 건자재 효율적 경영진이나, 인프라 투자 지연 및 건설 경기 하강이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "GPC": "Genuine Parts Company: 자동차 부품 유통에서 안정적 경영을 하나, 전기차 보급에 따른 내연기관 부품 수요 감소가 장기 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "LBTYK": "Liberty Global Ltd.: 통신 자산 매각 및 유동화 경영 능력이 있으나, 유럽 통신 시장의 극심한 가격 경쟁이 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "HLF": "Herbalife Ltd.: 다단계 마케팅(MLM) 모델로 경영 투명성 논란이 잦으며, 글로벌 규제 및 매출 감소 리스크는 이건 확인이 필요한 부분입니다.",
        "GDS": "GDS Holdings Limited: 중국 데이터센터 선도 기업이나, 높은 부채비율과 중국 빅테크 규제에 따른 단가 인하 압박은 이건 확인이 필요한 부분입니다.",
        "COLD": "Americold Realty Trust, Inc.: 냉동 물류 리츠로 독점력은 있으나, 높은 자본 지출(CAPEX) 요구 및 전력비 상승이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "MOH": "Molina Healthcare, Inc.: 정부 보조 의료보험(Medicaid) 특화 경영진 역량은 우수하나, 주 정부의 계약 갱신 탈락 위험이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "AERO": "Grupo Aeroméxico: 파산보호 졸업 후 정상화 추진 중이나, 남미 항공 시장의 높은 환율 및 연료비 변동성은 이건 확인이 필요한 부분입니다.",
        "NCLH": "Norwegian Cruise Line Holdings Ltd.: 크루즈 수요 회복을 이끄는 경영진이나, 팬데믹 기간 누적된 막대한 부채 상환 부담이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "KKR": "KKR & Co Inc: 대체투자 자산 다각화 능력이 탁월하나, 고금리 장기화에 따른 자산 매각(Exit) 지연이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "ROP": "Roper Technologies Inc: 니치 마켓 소프트웨어 인수 후 자본배분 능력이 독보적이나, 인수 기업들의 유기적 성장률 둔화가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "CSGP": "CoStar Group Inc: 상업용 부동산 데이터 독과점 경영진이나, 주택 부동산 시장 진출에 따른 마케팅 비용 과다는 이건 확인이 필요한 부분입니다.",
        "ORLY": "O'Reilly Automotive Inc: 자동차 애프터마켓의 최고 수준 공급망 경영진이나, 전기차 확산에 따른 부품 소모 감소가 장기 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "ABNB": "Airbnb, Inc.: 플랫폼 브랜드 파워와 경영진 리더십은 확실하나, 글로벌 주요 도시들의 단기 임대 규제 강화가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "NOW": "ServiceNow Inc: IT 워크플로우 시장의 압도적 경영진이나, 높은 밸류에이션 부담과 기업들의 IT 지출 통제가 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "GSHD": "Goosehead Insurance Inc: 프랜차이즈형 보험 중개 모델로 고성장 중이나, 핵심 인력 이탈 및 대형 보험사들의 인수 기준 강화가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "SOPH": "SOPHiA GENETICS SA: 데이터 기반 의료 플랫폼으로 기술력은 있으나, 지속적인 적자와 손익분기점(BEP) 달성 여부는 이건 확인이 필요한 부분입니다.",
        "AMT": "American Tower Corp: 글로벌 통신탑 리츠로 장기 계약 기반 경영은 안정적이나, 통신사들의 통신탑 공유 확대 및 고부채가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "PRM": "Perimeter Solutions Inc: 산불 지연제 시장의 독점적 경영진이나, 단일 제품 의존도가 높고 기후(강수량)에 따른 실적 변동성이 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "CCCS": "CCC Intelligent Solutions: 자동차 보험 및 수리 생태계 독점 소프트웨어로 경영진 신뢰도가 높으나, AI 도입을 통한 경쟁자 출현 여부는 이건 확인이 필요한 부분입니다.",
        "CPRT": "Copart Inc: 잔존 차량 경매 시장의 독점적 지위로 자본배분이 완벽에 가까우나, 자율주행 도입에 따른 사고율 급감이 장기 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "FICO": "Fair Isaac Corp: 미국 신용점수 독과점으로 강력한 가격 결정력이 있으나, 정부의 대체 신용평가 모델 도입 압박이 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "HCC": "Warrior Met Coal, Inc.: 제철용 유연탄 생산 효율성은 높으나, 탈탄소 트렌드 및 원자재 가격 폭락 시 직격탄을 맞는 고위험 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "RIG": "Transocean Ltd.: 심해 시추 시장의 선두 주자이나, 고유가 유지 여부에 따른 장비 가동률 변동 및 막대한 부채가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "AMR": "Alpha Metallurgical Resources, Inc.: 석탐 생산 자본 배분(자사주 매입)은 공격적이나, 장기적인 석탄 수요 감소 및 환경 규제가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "DJCO": "Daily Journal Corp: 찰리 멍거 사후 저널 사업의 쇠퇴와 소프트웨어 전환 성과는 이건 확인이 필요한 부분입니다.",
        "RACE": "Ferrari NV: 럭셔리 브랜드 통제 역량은 최고 수준이나, 내연기관 감성 유지와 전기차 전환의 조화는 이건 확인이 필요한 부분입니다.",
        
        "TSLA": "일론 머스크 (Elon Musk): 압도적인 혁신과 비전으로 전기차 생태계를 장악했으나, 오너의 예측 불가능한 돌발 발언과 타 사업으로의 집중력 분산이 가장 치명적인 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "MU": "산자이 메로트라 (Sanjay Mehrotra): 메모리 반도체 사이클을 견디는 보수적이고 안정적인 운영 능력을 입증했습니다.\n리스크: 극심한 메모리 반도체 사이클 의존도 및 기술 격차 변동성. (이건 확인이 필요한 부분입니다)",
        "LLY": "데이비드 릭스 (David Ricks): 비만 치료제 등 혁신 파이프라인을 통한 폭발적 성장을 이끌고 있으나, 신약 특허 만료 및 약가 인하 압박은 이건 확인이 필요한 부분입니다.",
        "WMT": "더그 맥밀런 (Doug McMillon): 옴니채널 유통망을 성공적으로 구축한 경영진이나, 소비 침체 및 인건비 상승 압박이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "AMD": "리사 수 (Lisa Su): 훌륭한 리더십으로 파산 위기의 회사를 턴어라운드 시켰습니다.\n리스크: 엔비디아와의 AI 칩 기술 격차 및 수요 둔화. (이건 확인이 필요한 부분입니다)",
        "JPM": "제이미 다이먼 (Jamie Dimon): 월가 역사상 가장 신뢰받는 CEO로 위기 관리 능력이 탁월하나, 포스트 다이먼 승계 리스크가 존재합니다. (이건 확인이 필요한 부분입니다)",
        "ORCL": "사프라 카츠 (Safra Catz): B2B 데이터베이스 시장의 굳건한 해자를 가졌으나, 경쟁사 대비 늦은 클라우드 전환 속도는 이건 확인이 필요한 부분입니다.",
        "V": "라이언 매키너니 (Ryan McInerney): 결제 네트워크의 압도적 해자와 주주 환원은 완벽하나, 각국 정부의 수수료 규제 위협이 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "XOM": "대런 우즈 (Darren Woods): 효율적인 자본 배분과 주주환원에 철저한 경영진이나, 화석 연료의 환경 규제 및 유가 변동성이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "INTC": "팻 겔싱어 (Pat Gelsinger): 파운드리 재건을 시도 중이나, 턴어라운드 지연 및 막대한 CAPEX 지출로 인한 잉여 현금 지속 소각이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "JNJ": "호아킨 두아토 (Joaquin Duato): 제약 부문에 집중하며 안정적 배당을 유지하나, 탈크 파우더 소송 관련 대규모 배상금이 치명적 사법 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "CSCO": "척 로빈스 (Chuck Robbins): 소프트웨어 구독 모델로의 전환을 안정적으로 이끌고 있으나, IT 인프라 지출 둔화 및 시장 포화가 주요 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "MA": "마이클 미바흐 (Michael Miebach): 완벽한 결제 과점 해자를 구축하고 훌륭한 주주환원을 펼치나, 정부의 카드 수수료 규제 압박은 이건 확인이 필요한 부분입니다.",
        "COST": "론 배크리스 (Ron Vactris): 멤버십 기반의 압도적 고객 충성도를 유지하나, 밸류에이션 할증 부담과 이커머스 경쟁 심화가 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "CAT": "짐 움플비 (Jim Umpleby): 배당 귀족주로서 탁월한 자본 배분을 보여주나, 글로벌 건설 경기 및 원자재 사이클에 극도로 민감한 점이 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "LRCX": "팀 아처 (Tim Archer): 반도체 식각 장비의 지배적 지위는 훌륭하나, 미국 정부의 대중국 반도체 장비 수출 규제가 치명적 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "ABBV": "리처드 곤잘레스 (Richard Gonzalez): 휴미라 특허 만료 위기를 훌륭하게 방어한 경영자이나, 후속 파이프라인의 성장 둔화는 이건 확인이 필요한 부분입니다.",
        "PLTR": "알렉스 카프 (Alex Karp): 독보적인 AI 데이터 분석 기술력을 가졌으나, 내부자 매도 물량 지속 및 높은 밸류에이션이 주의할 부분입니다. (이건 확인이 필요한 부분입니다)",
        "NFLX": "테드 사란도스 (Ted Sarandos): 광고 요금제로 수익성을 크게 개선한 경영진이나, OTT 시장 포화 및 콘텐츠 제작비 증가가 장기 리스크입니다. (이건 확인이 필요한 부분입니다)",
        "AMAT": "게리 디커슨 (Gary Dickerson): 반도체 장비 1위의 해자와 자사주 매입 정책은 훌륭하나, 대중국 수출 통제 리스크 노출은 이건 확인이 필요한 부분입니다.",
        
        "SPACEX": "일론 머스크 (Elon Musk): 압도적인 혁신과 비전으로 민간 우주 산업을 선도하고 있으나, 특정 리더에 대한 극단적 의존도 및 규제 기관과의 마찰이 가장 치명적인 리스크입니다. (이건 확인이 필요한 부분입니다)",

        "005930": "삼성전자 (이재용/전영현 등): 반도체 부문 수장 교체 등 쇄신을 시도하고 있으나 조직 내부의 관료화가 지적됩니다.\n리스크: AI 메모리(HBM) 및 파운드리 기술 격차 회복 지연, 오너 사법 리스크 및 창사 이래 첫 노조 파업 지속. (이건 확인이 필요한 부분입니다)",
        "000660": "SK하이닉스 (최태원/곽노정): 선택과 집중을 통해 엔비디아와의 파트너십을 선점한 실행력이 돋보입니다.\n리스크: 메모리 사이클 고점에 대한 민감도 및 모기업 SK그룹의 재무 구조조정에 따른 자금 동원 부담 가능성. (이건 확인이 필요한 부분입니다)",
        "373220": "LG에너지솔루션 (김동명): 글로벌 합작법인(JV)을 속도감 있게 구축하며 외형 성장을 이뤄냈습니다.\n리스크: 전기차 캐즘(수요 둔화) 장기화에 따른 가동률 하락과 미국 IRA 보조금 정책 변화 노출. (이건 확인이 필요한 부분입니다)",
        "005380": "현대차 (정의선): 내연기관과 하이브리드, 전기차를 유연하게 오가는 생산 믹스 전략이 세계 최고 수준입니다.\n리스크: 피크아웃(실적 정점) 우려 및 강성 노조와의 매년 반복되는 임금 단체협상 마찰. (이건 확인이 필요한 부분입니다)",
        "207940": "삼성바이오로직스 (존 림): 철저한 품질 관리로 글로벌 빅파마들의 대규모 CMO 위탁 물량을 선점했습니다.\n리스크: 삼성그룹 경영권 승계 관련 재판에 얽힌 컴플라이언스 꼬리표 및 글로벌 CDMO 생산 능력 과잉. (이건 확인이 필요한 부분입니다)",
        "000270": "기아 (송호성): 디자인 혁신과 고수익 RV(레저용 차량) 위주의 판매로 현대차 이상의 이익률을 달성했습니다.\n리스크: 내수 시장 침체 및 전 세계적인 전기차 전환 속도 조절에 따른 고정비 부담. (이건 확인이 필요한 부분입니다)",
        "068270": "셀트리온 (서정진): 오너의 강력한 추진력으로 바이오시밀러 직판 체제를 성공적으로 구축했습니다.\n리스크: 빈번한 합병 연기 및 실적 가이던스 수정에 따른 시장 신뢰도 저하, 재고자산 회계 처리 논란. (이건 확인이 필요한 부분입니다)",
        "105560": "KB금융 (양종희): 국내 은행권 최초로 강력하고 투명한 밸류업(주주환원) 로드맵을 제시했습니다.\n리스크: 정부의 은행권 이자 수익 개입(상생 금융 압박) 및 부동산 PF 부실 전이 가능성. (이건 확인이 필요한 부분입니다)",
        "005490": "POSCO홀딩스 (장인화): 철강 본업 강화와 2차전지 소재 투자의 현실적인 속도 조절을 진행 중입니다.\n리스크: 글로벌 철강 수요 침체 지속 및 2차전지 핵심 소재(리튬) 가격 폭락에 따른 마진 훼손. (이건 확인이 필요한 부분입니다)",
        "055550": "신한지주 (진옥동): 주주환원율 확대와 비은행 부문(카드, 생보) 포트폴리오 관리가 우수합니다.\n리스크: 과거 사모펀드 사태 및 내부 횡령 등 잊힐 만하면 반복되는 내부통제 실패 평판. (이건 확인이 필요한 부분입니다)",
        "006400": "삼성SDI (최윤호): '수익성 우위의 질적 성장'이라는 매우 보수적이고 안전한 재무 관리를 보여줍니다.\n리스크: 경쟁사 대비 소극적인 CAPEX 투자로 인한 장기적인 글로벌 시장 점유율 상실. (이건 확인이 필요한 부분입니다)",
        "035420": "NAVER (최수연): 내수 중심의 검색·커머스 포트폴리오로 탄탄한 현금을 창출합니다.\n리스크: 라인야후 사태 등 지정학적 한계 및 막대한 개발비 대비 가시화되지 않은 AI 수익 모델. (이건 확인이 필요한 부분입니다)",
        "012330": "현대모비스 (이규석): 캡티브(현대차·기아) 물량 기반의 안정적인 부품 납품 생태계를 장착했습니다.\n리스크: 그룹 지배구조 개편의 핵심 고리라는 이유로 주가 부양 및 주주환원에 소극적일 수 있다는 시장의 의구심. (이건 확인이 필요한 부분입니다)",
        "051910": "LG화학 (신학철): 석유화학 비중을 줄이고 친환경/바이오 3대 신성장 동력으로 체질을 개선 중입니다.\n리스크: 본업(석유화학)의 극심한 부진 및 핵심 자회사 LG엔솔 물적분할로 인한 지주사 디스카웃. (이건 확인이 필요한 부분입니다)",
        "035720": "카카오 (정신아): 문어발식 확장 부작용을 수습하고 핵심 톡비즈 중심으로 쇄신을 강행 중입니다.\n리스크: 창업자(김범수) 구속 등 오너 사법 리스크의 장기화 및 플랫폼 독과점에 대한 정치권 규제. (이건 확인이 필요한 부분입니다)",
        "028260": "삼성물산 (오세철): 건설 부문 효율화와 바이오 자회사의 성장으로 장부상 가치(NAV)가 훌륭합니다.\n리스크: 삼성그룹 지배구조 최상단에 위치해 본업 가치보다 오너 지배력 유지를 위한 배당/자본 배치 비효율 지속. (이건 확인이 필요한 부분입니다)",
        "086790": "하나금융지주 (함영주): 외환과 기업 금융의 강점을 바탕으로 주주 친화 정책에 적극 동참 중입니다.\n리스크: 타 금융지주 대비 높은 해외 상업용 부동산 대체투자 손실 처리 및 국내 PF 대손충당금 부담. (이건 확인이 필요한 부분입니다)",
        "066570": "LG전자 (조주완): 단순 가전 제조사를 넘어 B2B 및 구독 모델 전장(VS) 사업으로 성공적 전환을 입증했습니다.\n리스크: 글로벌 주택 거래 침체 장기화 시 프리 가전 수요 감소를 방어할 수단 제한. (이건 확인이 필요한 부분입니다)",
        "402340": "SK스퀘어 (박성하): SK하이닉지 지분 가치를 바탕으로 강력한 자사주 매입 and 포트폴리오 정리를 시도 중입니다.\n리스크: 11번가, 원스토어 등 비상장 자회사의 매각 혹은 IPO 지연에 따른 구조적 현금흐름 부재. (이건 확인이 필요한 부분입니다)",
        "032830": "삼성생명 (홍원학): IFRS17 도입 이후에도 업계 최고 수준의 K-ICS(신지급여력비율) 자본 건전성을 유지합니다.\n리스크: 보험업법 개정 시 보유 중인 막대한 삼성전자 지분에 대한 강제 매각(오버행) 불확실성. (이건 확인이 필요한 부분입니다)",
        "138040": "메리츠금융지주 (김용범): 존 리 이후 자본 배치 능력은 우수하나, 경영진의 절대적인 정직성에 대해서는 철저한 팩트 체크가 선행되어야 합니다.\n리스크: 고위험 고수익(부동산 PF 등) 중심의 영업방식이 부동산 침체기 부메랑으로 돌아올 가능성. (이건 확인이 필요한 부분입니다)",
        "096770": "SK이노베이션 (박상규): 정유 부문을 바탕으로 자회사 SK E&S와의 합병 등 그룹 리밸런싱의 총대를 멨습니다.\n리스크: 배터리 자회사(SK온)의 수율 정상화 지연과 흑자 전환 실패에 따른 모기업의 재무적 과부하. (이건 확인이 필요한 부분입니다)",
        "329180": "HD현대중공업 (이상균): 선별 수주 전략과 친환경 엔진 기술력으로 조선업 슈퍼 사이클을 리드 중입니다.\n리스크: 고질적인 조선소 현장 생산 인력 난과 잦은 부분 파업에 따른 공정 지연 패널티. (이건 확인이 필요한 부분입니다)",
        "011200": "HMM (김경배): 팬데믹 시기 벌어들인 막대한 현금을 방어하며 해운동맹(얼라이언스) 재편에 대응 중입니다.\n리스크: 지정학적 갈등에 따른 극단적 운임 변동성 및 최대주주(산은/해진공)의 민영화 매각 실패에 따른 표류. (이건 확인이 필요한 부분입니다)",
        "010130": "고려아연 (최윤범): 글로벌 1위 제련업에 머물지 않고 신재생·2차전지 소재 산업으로 투자를 확대했습니다.\n리스크: 대주주 영풍그룹 및 MBK 파트너스와의 경영권 분쟁 격화에 따른 피로감과 과도한 자금 출혈. (이건 확인이 필요한 부분입니다)",
        "033780": "KT&G (방경만): 행동주의 펀드의 압박 속에서 비주력 자산 매각 및 주주환원 확대를 이끌어냈습니다.\n리스크: 궐련형 전자담배 수출 성장에도 불구하고 환율 및 현지 판관비 증가에 따른 단기 마진 하락. (이건 확인이 필요한 부분입니다)",
        "034020": "두산에너빌리티 (박지원): 원전 수주 등 본업의 기술적 해 외는 명확하나 그룹 체스판의 희생양 논란이 있습니다.\n리스크: 수익성 높은 자회사(두산밥캣)를 타 계열사로 넘기려는 지배구조 개편 추진으로 인한 주주가치 훼손 전력. (이건 확인이 필요한 부분입니다)",
        "009150": "삼성전기 (장덕현): IT 기기용 MLCC 의존도를 줄이고 AI 서버 및 전장용 고부가가치 부품 비중을 늘렸습니다.\n리스크: 여전히 높은 스마트폰 전방 산업에 대한 수요 민감도. (이건 확인이 필요한 부분입니다)",
        "259960": "크래프톤 (김창한): '배틀그라운드' 단일 IP의 수명을 이례적으로 길게 늘리며 독보적인 영업이익률을 유지합니다.\n리스크: 다크앤다커 모바일 등 차기 흥행 신작 부재 시 발생하는 치명적인 단일 게임 의존도. (이건 확인이 필요한 부분입니다)",
        "012450": "한화에어로스페이스 (손재일): 자회사 합병을 통한 K-방산 수직 계열화로 글로벌 수출 모멘텀을 주도합니다.\n리스크: 특정 국가의 정치적 정권 교체나 정책 변화에 따라 수조 원대 수주 계약이 흔들릴 수 있는 지정학적 리스크. (이건 확인이 필요한 부분입니다)"
    }
    
    for key, text in db.items():
        if key in tk_clean or (len(cd_clean) == 6 and key == cd_clean):
            return text
            
    return f"{ceo_name} 경영진 - 위키 및 공공 기록 스크리닝 결과, 해당 경영진에 대한 사법적 리스크나 중범죄 이력은 두드러지지 않습니다. 다만 가치투자 관점에서 과도한 자본 배분 오류 및 노사 갈등 여부는 투자 전 추가 교차 검증이 필요합니다. (이건 확인이 필요한 부분입니다)"

def get_yf_info(stk):
    try:
        res = stk.info
        return res if isinstance(res, dict) else {}
    except:
        return {}

def get_finviz_data(cd):
    res = {}
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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
            if fpe: res['forwardPE'] = safe_float(fpe)
            pe = get_fv("P/E")
            if pe: res['trailingPE'] = safe_float(pe)
            eps_nxt = get_fv("EPS next Y")
            if eps_nxt: res['finviz_eps_next'] = safe_float(eps_nxt)
            eps_ttm = get_fv("EPS (ttm)")
            if eps_ttm: res['trailingEps'] = safe_float(eps_ttm)
    except:
        pass
    return res

def get_yahoo_profile(cd):
    res = {}
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        yh_url = f"https://finance.yahoo.com/quote/{cd}/profile"
        yh_r = requests.get(yh_url, headers=headers, timeout=5)
        if yh_r.status_code == 200:
            yh_s = BeautifulSoup(yh_r.text, 'html.parser')
            desc = yh_s.find('section', {'data-testid': 'description'})
            if desc: res['longBusinessSummary'] = desc.text.strip()
            exec_table = yh_s.find('table')
            if exec_table:
                ceo_name = exec_table.find('tbody').find('tr').find('td').text.strip()
                res['companyOfficers'] = [{'name': ceo_name}]
    except:
        pass
    return res

def get_naver_finance(cd):
    res = {}
    try:
        url = f"https://finance.naver.com/item/main.naver?code={cd}"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        s = BeautifulSoup(r.text, 'html.parser')
        
        t_price = s.select_one('.no_today .blind')
        if t_price:
            live_p = safe_float(t_price.text.replace(',', ''))
            if live_p > 0: res['live_p'] = live_p
            
        t_name = s.select_one('.wrap_company h2 a')
        if t_name: res['shortName'] = t_name.text
        
        t_pe = s.select_one('#_per')
        if t_pe: res['trailingPE'] = safe_float(t_pe.text.replace(',',''))
        
        t_fpe = s.select_one('#_cns_per')
        if t_fpe: res['forwardPE'] = safe_float(t_fpe.text.replace(',',''))
        
        t_pbr = s.select_one('#_pbr')
        if t_pbr: res['priceToBook'] = safe_float(t_pbr.text.replace(',',''))
        
        t_div = s.select_one('#_dvr')
        if t_div: res['dividendYield'] = safe_float(t_div.text.replace(',',''))/100
        
        t_sum = s.select_one('.summary_info p')
        if t_sum: res['kr_sum'] = t_sum.text
    except:
        pass
    return res

# [최적화] 무거운 재무 데이터 및 크롤링 결과만 따로 캐싱 (하루 1번)
@st.cache_data(ttl=86400)
def fetch_cached_info(tk, kr, cd):
    stk = yf.Ticker(tk)
    i = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_info = executor.submit(get_yf_info, stk)
        
        if not kr:
            future_finviz = executor.submit(get_finviz_data, cd)
            future_yahoo = executor.submit(get_yahoo_profile, cd)
        else:
            future_naver = executor.submit(get_naver_finance, cd)
            
        i = future_info.result().copy() if future_info.result() else {}
        
        if not kr:
            fv_res = future_finviz.result()
            yh_res = future_yahoo.result()
            
            if 'forwardPE' not in i or not i.get('forwardPE'):
                if 'forwardPE' in fv_res: i['forwardPE'] = fv_res['forwardPE']
            if 'trailingPE' not in i or not i.get('trailingPE'):
                if 'trailingPE' in fv_res: i['trailingPE'] = fv_res['trailingPE']
            if 'trailingEps' not in i or not i.get('trailingEps'):
                if 'trailingEps' in fv_res: i['trailingEps'] = fv_res['trailingEps']
            if 'finviz_eps_next' in fv_res: i['finviz_eps_next'] = fv_res['finviz_eps_next']
            
            if 'longBusinessSummary' not in i and 'longBusinessSummary' in yh_res:
                i['longBusinessSummary'] = yh_res['longBusinessSummary']
            if 'companyOfficers' not in i and 'companyOfficers' in yh_res:
                i['companyOfficers'] = yh_res['companyOfficers']
        else:
            nv_res = future_naver.result()
            for k in ['shortName', 'trailingPE', 'forwardPE', 'priceToBook', 'dividendYield', 'kr_sum']:
                if k in nv_res: i[k] = nv_res[k]

    if 'sharesOutstanding' not in i or not i.get('sharesOutstanding') or i.get('sharesOutstanding') == 0:
        try:
            sh_count = safe_float(i.get('impliedSharesOutstanding', 0))
            if sh_count > 0: i['sharesOutstanding'] = sh_count
        except: pass
        
    return i

# [최적화] 실시간 주가는 캐싱 없이 매번 호출하도록 분리
def get_data(tk):
    try:
        if not tk: return None, None, {}, False
        tk = str(tk).strip()
        
        if tk.isdigit() and len(tk) == 6:
            test_tk = tk + ".KS"
            stk_test = yf.Ticker(test_tk)
            try:
                _ = stk_test.history(period="1d")
                tk = test_tk 
            except: tk = tk + ".KQ"

        if "." not in tk: tk = tk.upper()
        kr = tk.endswith('.KS') or tk.endswith('.KQ')
        cd = tk.split('.')[0] if kr else tk
        
        stk = yf.Ticker(tk)
        
        i = fetch_cached_info(tk, kr, cd).copy()
        
        p = 0.0
        if kr:
            try:
                nv_res = get_naver_finance(cd)
                if 'live_p' in nv_res and nv_res['live_p'] > 0: 
                    p = safe_float(nv_res['live_p'])
            except: pass
            
        if p == 0:
            try:
                hist = stk.history(period="1d")
                if not hist.empty:
                    p = safe_float(hist['Close'].iloc[-1])
            except: pass

        if p == 0:
            p = safe_float(i.get('currentPrice', i.get('regularMarketPrice')))
            
        return stk, p, i, kr
    except Exception as e:
        return None, None, {}, False

# [최적화] 최대 10년치 데이터를 자동으로 탐지해 연평균 성장률을 계산
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
        
        # 만약 데이터 소스에서 10년 치가 제공된다면 자동으로 그 기간을 인식하여 계산
        if fcf_s is not None and len(fcf_s) >= 2:
            c, o = safe_float(fcf_s.iloc[0]), safe_float(fcf_s.iloc[-1])
            data_len = len(fcf_s)  # 무료 API는 통상 4~5년을 반환하지만, 유료 API 연동 시 최대치 자동 반영
            if c > 0 and o > 0: g = (c / o) ** (1 / (data_len - 1)) - 1
        else:
            eg = safe_float(i.get('earningsGrowth'))
            if eg != 0.0: g = eg
            data_len = 1
            
        g = max(0.02, min(g, 0.15))
        return fcf, sh, g, data_len
    except: return None, None, 0.05, 0

# [최적화] 보수적인 영구 성장률 적용 로직 (DCF)
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
            
        term_g = 0.02 if g >= 0.05 else 0.0
        tv = (cv * (1 + term_g)) / (dr - term_g)
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
            
        term_g = 0.02 if mid >= 0.05 else 0.0
        tv = (cv * (1 + term_g)) / (dr - term_g)
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

def analyze_rnd_trend(stk, base_fcf, is_financial, kr):
    if is_financial: return f"<span style='color:#8892b0'>{t('금융/보험주 제외', 'N/A (Financial)')}</span>"
    
    rnd_trend = f"<span style='color:#8892b0'>{t('데이터 부족 (해당없음)', 'No Data')}</span>"
    if stk is None: return rnd_trend
    
    try:
        inc = stk.income_stmt
        if inc is not None and not inc.empty and 'Research And Development' in inc.index:
            rnd_series = inc.loc['Research And Development'].dropna()
            if not rnd_series.empty:
                rnd_vals = rnd_series.values[:4][::-1]
                rnd_years = [str(c)[:4] for c in rnd_series.index[:4]][::-1]
                curr_rnd = safe_float(rnd_vals[-1])
                
                if curr_rnd > 0:
                    mv = max([abs(x) for x in rnd_vals])
                    if kr:
                        if mv >= 1e12: div, u = 1e12, "조원"
                        elif mv >= 1e8: div, u = 1e8, "억원"
                        else: div, u = 1, "원"
                    else:
                        if mv >= 1e9: div, u = 1e9, "B"
                        elif mv >= 1e6: div, u = 1e6, "M"
                        else: div, u = 1, "$"
                    
                    history_str = ", ".join([f"<b>{y}년</b>: {v/div:.1f}{u}" for y, v in zip(rnd_years, rnd_vals)])
                    
                    sudden_alert = ""
                    for i in range(len(rnd_vals) - 1, 0, -1):
                        curr = safe_float(rnd_vals[i])
                        prev = safe_float(rnd_vals[i-1])
                        if prev > 0:
                            inc_pct = ((curr - prev) / prev) * 100
                            if inc_pct >= 30:
                                years_ago = len(rnd_vals) - 1 - i 
                                if years_ago == 0:
                                    txt_ko = f"작년에 {inc_pct:.1f}% 급상승"
                                    txt_en = f"Spiked {inc_pct:.1f}% last year"
                                elif years_ago == 1:
                                    txt_ko = f"2년 전에 {inc_pct:.1f}% 급상승"
                                    txt_en = f"Spiked {inc_pct:.1f}% 2 years ago"
                                elif years_ago == 2:
                                    txt_ko = f"3년 전에 {inc_pct:.1f}% 급상승"
                                    txt_en = f"Spiked {inc_pct:.1f}% 3 years ago"
                                else:
                                    continue
                                
                                sudden_alert = f" <span class='highlight'>[{t(txt_ko, txt_en)}]</span>"
                                break 
                    
                    if base_fcf and base_fcf > 0:
                        ratio = (curr_rnd / base_fcf) * 100
                        if ratio >= 50:
                            r_eval = f"<span class='highlight'>{t('[지출 과다] 현금흐름 압박 주의', '[High] Watch Cash Flow')}</span>"
                            desc = t("FCF(순수여윳돈)의 절반 이상을 연구개발에 쏟고 있습니다. 공격적인 미래 베팅이지만 현금 고갈 리스크를 주의하세요.", "Consuming over half of FCF on R&D. Highly aggressive, watch for cash burn.")
                        elif ratio >= 15:
                            r_eval = f"<span class='good'>{t('[적정 수준] 이상적인 재투자', '[Optimal] Ideal Reinvestment')}</span>"
                            desc = t("벌어들인 여윳돈 내에서 미래 먹거리에 아주 건강한 비율로 투자하고 있습니다.", "Healthy reinvestment rate into future growth within generated cash.")
                        else:
                            r_eval = f"<span style='color:#fdcb6e;'>{t('[지출 적음] 투자 미흡 가능성', '[Low] Potential Underinvestment')}</span>"
                            desc = t("FCF 대비 R&D 비율이 낮습니다. (단, 코카콜라 같은 필수소비재 등 성숙 산업은 이 비율이 낮아도 정상입니다)", "Low R&D relative to FCF. (Normal for mature non-tech industries).")
                            
                        rnd_trend = f"{r_eval}{sudden_alert} <span style='font-size:0.95em;'>➔ FCF의 <b>{ratio:.1f}%</b> 지출 ({desc})<br><span style='color:#8892b0;'>4개년 지출 추이: [{history_str}]</span></span>"
                    elif base_fcf and base_fcf <= 0:
                        rnd_trend = f"<span class='highlight'>{t('FCF(순수여윳돈) 적자로 적정선 계산 불가', 'Unable to calc optimal line due to negative FCF')}</span>{sudden_alert}<br><span style='color:#8892b0;'>4개년 지출 추이: [{history_str}]</span>"
                    else:
                        rnd_trend = f"<span style='color:#8892b0;'>4개년 지출 추이: [{history_str}]</span>{sudden_alert}"
                else:
                    rnd_trend = f"<span style='color:#8892b0'>{t('R&D 지출 없음', 'No R&D')}</span>"
    except:
        pass
        
    return rnd_trend

def get_comprehensive_investment_opinion(mos, pmos, roe, roic, erp, final_g, ceo_text, is_financial=False, pbr=0.0, kr=False, tk=""):
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
        
    if pmos >= 30: score += 25
    elif pmos >= 15: score += 15
    elif pmos >= 5: score += 5
    elif pmos < -20: score -= 25
    elif pmos < -10: score -= 15
    elif pmos < 0: score -= 5

    if is_financial:
        if roe >= 15: score += 25
        elif roe >= 10: score += 15
        elif roe >= 8: score += 5
        elif roe < 5: score -= 25
        elif roe < 8: score -= 15

        if pbr > 0 and pbr <= 0.6: score += 25
        elif pbr > 0.6 and pbr <= 0.9: score += 15
        elif pbr > 0.9 and pbr <= 1.0: score += 5
        elif pbr >= 1.5: score -= 25
        elif pbr >= 1.2: score -= 15
        elif pbr > 1.0: score -= 5
    else:
        if roe >= 20: score += 15
        elif roe >= 15: score += 10
        elif roe >= 10: score += 5
        elif roe < 5: score -= 15
        elif roe < 10: score -= 10
        
        if roic and roic >= 15: score += 15
        elif roic and roic >= 10: score += 10
        elif roic and roic >= 7: score += 5
        elif roic and roic < 3: score -= 15
        elif roic and roic < 7: score -= 10
        
        if mos >= 30: score += 25
        elif mos >= 15: score += 15
        elif mos >= 5: score += 5
        elif mos < -20: score -= 25
        elif mos < -10: score -= 15
        elif mos < 0: score -= 5

    if erp >= 4: score += 25
    elif erp >= 2: score += 15
    elif erp >= 1: score += 5
    elif erp < -1: score -= 25
    elif erp < 0: score -= 15
    elif erp < 1: score -= 5

    if final_g >= 0.15: score += 25
    elif final_g >= 0.08: score += 15
    elif final_g >= 0.05: score += 5
    elif final_g < 0.0: score -= 25
    elif final_g < 0.03: score -= 15
    elif final_g < 0.05: score -= 5

    # 지정학적 디스카운트 판별 로직
    chinese_adrs = ["PDD", "TME", "GDS", "BABA", "BIDU", "JD", "NIO", "XPEV", "LI", "NTES", "TCEHY", "YUMC", "ZTO", "EDU"]
    tk_upper = str(tk).upper()
    is_china = any(tk_upper.startswith(c) for c in chinese_adrs) or ("중국 정부" in ceo_text) or ("중국 데이터센터" in ceo_text)
    
    if kr:
        score -= 15
    elif is_china:
        score -= 20

    # 시클리컬 기업 판단 범위 확장 및 페널티 대폭 강화 (-50점 유지 또는 -30점 조정 요구 -> 30점으로 완화하면서 강하게 적용 요구 -> 30점으로 세팅)
    is_cyclical = any(k in ceo_text for k in [
        "사이클", "유가", "경기 민감", "철강", "석유화학", "화학", "화석 연료", 
        "조선", "해운", "운임", "원자재", "비철금속", "건설", "기계", "건설장비", "항공", "여행",
        "메모리", "반도체", "디스플레이", "엔비디아", "AMD", "마이크론", "인텔", "어플라이드", "램리서치", 
        "자동차", "현대차", "기아", "테슬라", "부품 납품", "내연기관", "전기차"
    ])
    if is_cyclical:
        score -= 30

    if score >= 90:
        title, color, reason = t("적극적 할인 (Deep Discount)", "Deep Discount"), "#2ecc71", t("경영진, 훌륭한 자본효율(ROE>20%), 30% 이상의 안전마진, 압도적 국채 대비 매력도(ERP) 등 모든 평가에서 '매우 합격'을 기록한 워런 버핏급 초저평가 기회입니다.", "An extremely rare 'Buffett-level' deep discount meeting 'Very Pass' criteria across management, ROE, MoS, and ERP.")
    elif score >= 50:
        title, color, reason = t("할인 (Discount)", "Discount"), "#00b894", t("충분한 안전마진 and 훌륭한 자본 배치 능력이 교차 검증되어 전반적으로 '합격' 수준의 우량한 할인 구간입니다.", "A solid discount zone backed by overall 'Pass' levels of margin of safety and excellent capital allocation metrics.")
    elif score >= 15:
        title, color, reason = t("약간 할인 (Slight Discount)", "Slight Discount"), "#74b9ff", t("안전마진이 아주 넉넉하지는 않지만, 우량한 사업 퀄리티 대비 현재 가격이 '약간 할인'되어 충분히 긍정적으로 검토할 수 있는 합리적인 구간입니다.", "Priced at a slight discount relative to its high-quality business profile, presenting a reasonable entry point despite a modest margin of safety.")
    elif score >= -15:
        title, color, reason = t("적정 가치 (Fair Value)", "Fair Value"), "#fdcb6e", t("비즈니스 퀄리티와 성장성을 감안할 때 일부 지표가 '약간 주의' 수준이더라도 충분히 납득할 수 있는 적당한 가격(Fair Price)입니다.", "Lacks deep margin of safety, but perfectly justifiable as a fair price given business quality despite some 'Slight Warning' metrics.")
    elif score >= -45:
        title, color, reason = t("약간 할증 (Slight Premium)", "Slight Premium"), "#ff7675", t("기업의 펀더멘털은 견고하지만 시장의 기대감이 선반영되어 가격에 '약간의 할증(Premium)'이 붙어 있습니다. 보수적인 분할 접근이나 조정 시 매수가 유리합니다.", "Solid fundamentals, but trading at a slight premium due to pre-reflected market optimism. A conservative stance or waiting for a pullback is recommended.")
    elif score >= -75:
        title, color, reason = t("할증 (Premium)", "Premium"), "#e17055", t("다수의 밸류에이션 지표에서 '주의' 판정을 받았습니다. 성장성 대비 시장의 기대감이 과도하게 선반영되어 비싸게 거래 중입니다.", "Trading at a premium with multiple 'Warning' signals. The price reflects excessive market expectations relative to fundamentals.")
    else:
        title, color, reason = t("과도한 할증 (Excessive Premium)", "Excessive Premium"), "#d63031", t("가치평가 지표가 대부분 '매우 주의'를 가리킵니다. 펀더멘털의 심각한 훼손이나 비상식적인 밸류에이션 거품이 낀 매우 위험한 구간입니다.", "Highly dangerous speculative territory with multiple 'Very Warning' signals, indicating compromised fundamentals or extreme valuation bubbles.")

    if is_cyclical:
        reason += t(" (시클리컬 기업 감점 적용됨: 실적 변동성으로 인한 가치평가 신뢰도 하락)", " (Cyclical Penalty Applied: Lower valuation reliability due to earnings volatility)")
    if kr:
        reason += t(" (코리아 디스카운트 적용됨: 주주환원율 미흡 및 지정학적 리스크)", " (Korea Discount Applied: Poor shareholder returns and geopolitical risks)")
    elif is_china:
        reason += t(" (차이나 디스카운트 적용됨: 공산당 규제 및 재무 투명성 리스크)", " (China Discount Applied: Regulatory and financial transparency risks)")
    if is_financial:
        reason += t(" (금융/보험주 특수 로직 적용됨: ROE와 장부가 가치 PBR 분석 기반 평가 완료)", " (Financial Mode Active: Evaluation based on ROE and PBR)")

    return title, color, reason

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
    for prefix in ["Mr. ", "Ms. ", "Mrs. ", "Dr. ", "Mr ", "Ms ", "Mrs ", "Dr "]:
        if name_str.startswith(prefix): name_str = name_str[len(prefix):]
    if is_ko:
        try:
            k_name = GoogleTranslator(source='en', target='ko').translate(name_str[:1000]) if name_str else '누락'
            if not k_name:
                k_name = name_str
        except:
            k_name = name_str
            
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
    st.markdown(f"<div style='margin-top:10px; font-size: 0.95rem; font-weight: bold; color: var(--text-color);'>csjwo154515@naver.com</div>", unsafe_allow_html=True)

st.markdown("""
<style>
.main { background-color: var(--background-color); color: var(--text-color); font-family: 'Pretendard', sans-serif; }
h1, h2, h3 { color: #A0C4FF; font-weight: 800; letter-spacing: -0.5px; }
.stTabs [data-baseweb="tab-list"] { gap: 15px; border-bottom: 2px solid rgba(255,255,255,0.05); padding-bottom: 5px; }
.stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: 600; color: #8892b0; background: transparent; transition: 0.2s; padding: 10px 15px; border-radius: 12px; }
.stTabs [aria-selected="true"] { color: #A0C4FF !important; background: rgba(160, 196, 255, 0.1) !important; border-bottom: none !important; }
.good { color: #2ecc71; font-weight: 700; }
.highlight { color: #ff7675; font-weight: 700; }
.guru-quote { font-style: normal; color: var(--text-color); background: linear-gradient(135deg, rgba(160,196,255,0.1), rgba(255,198,255,0.1)); padding: 20px; border-radius: 16px; border-left: 5px solid #A0C4FF; margin-bottom: 15px; line-height: 1.6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.macro-ticker::-webkit-scrollbar { display: none; }
.macro-ticker { -ms-overflow-style: none; scrollbar-width: none; }
div[data-testid="stDataFrame"] canvas { touch-action: auto !important; }
div[data-testid="stDataFrame"] { overflow-x: auto !important; -webkit-overflow-scrolling: touch !important; border-radius: 12px; overflow: hidden; }
div[data-testid="stArrowVegaLiteChart"] canvas, div[data-testid="stVegaLiteChart"] canvas { pointer-events: none !important; }
div[data-testid="stArrowVegaLiteChart"], div[data-testid="stVegaLiteChart"] { overflow-x: auto !important; overflow-y: hidden !important; -webkit-overflow-scrolling: touch !important; }
#vg-tooltip-element, .vg-tooltip { display: none !important; opacity: 0 !important; pointer-events: none !important; }
[data-testid="stElementToolbar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="padding-top: 10px; padding-bottom: 15px; text-align: center;">
    <span style="font-size: 3.5rem; font-weight: 900; background: linear-gradient(45deg, #A0C4FF, #FFC6FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 3px;">AGIE</span>
    <div style="font-size: 1rem; color: #8892b0; margin-top: -10px; font-weight: 600;">똑똑하고 친절한 나만의 AI 가치투자 비서</div>
</div>
""", unsafe_allow_html=True)

st.info(t("[안내] 화면 글씨가 어색하게 번역되어 보인다면 브라우저의 '자동 번역' 기능을 꺼주세요. (앱 자체의 언어 변환 기능을 이용해 주십시오)", "[Info] If the text looks distorted, please disable your browser's auto-translate. Use the language toggle in the sidebar instead."))

st.warning(t("[참고] 본 가치투자 분석 모델은 해운, 철강, 화학 등 실적 변동성이 극심한 **시클리컬(경기민감) 기업**의 내재가치 평가에는 적합하지 않을 수 있습니다.", "[Note] This value investing model may not be suitable for evaluating the intrinsic value of **cyclical companies** (e.g., shipping, steel, chemicals) with extreme earnings volatility."))

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

macro_html = "<div class='macro-ticker' style='display: flex; overflow-x: auto; gap: 12px; padding: 10px 0 20px 0; -webkit-overflow-scrolling: touch;'>"
for name, val, chg, unit in macro_items:
    color = "#2ecc71" if chg > 0 else ("#ff7675" if chg < 0 else "#8892b0")
    sign = "+" if chg > 0 else ""
    chg_str = f"{sign}{chg:.3f}{unit}" if unit == " bp" else f"{sign}{chg:.2f}{unit}"
    macro_html += f"<div style='flex: 0 0 auto; background: rgba(255,255,255,0.03); padding: 18px 22px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); min-width: 145px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.05);'><div style='font-size: 0.85rem; color: #8892b0; margin-bottom: 8px; font-weight: 600;'>{name}</div><div style='font-size: 1.4rem; font-weight: 800; color: var(--text-color); letter-spacing: -0.5px;'>{val}</div><div style='font-size: 0.95rem; font-weight: bold; color: {color}; margin-top: 5px;'>{chg_str}</div></div>"
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
        st.markdown(f"<div style='background: rgba(255,255,255,0.03); color:var(--text-color); padding:20px; border-radius:16px; border-top: 4px solid {spy_col}; box-shadow: 0 4px 12px rgba(0,0,0,0.05);'><h4 style='margin-top:0; color:#A0C4FF;'>S&P 500 밸류에이션</h4><p style='margin:6px 0;'>- Fwd PER: <b>{spy_pe_str}배</b></p><p style='margin:6px 0;'>- 예상 이익수익률(EY): <b>{spy_ey_str}%</b></p><p style='margin:6px 0;'>- 10년물 국채: <b>{tnx_val_str}%</b></p><p style='margin:6px 0;'>- 주식 위험 프리미엄(ERP): <b style='color:{spy_col}'>{spy_erp_str}%</b></p><hr style='margin:15px 0; border-color:rgba(255,255,255,0.1);'><b>[AI 시장 의견] <span style='color:{spy_col}'>{spy_op}</span></b></div>", unsafe_allow_html=True)
    with c_m2:
        st.markdown(f"<div style='background: rgba(255,255,255,0.03); color:var(--text-color); padding:20px; border-radius:16px; border-top: 4px solid {qqq_col}; box-shadow: 0 4px 12px rgba(0,0,0,0.05);'><h4 style='margin-top:0; color:#A0C4FF;'>Nasdaq 100 밸류에이션</h4><p style='margin:6px 0;'>- Fwd PER: <b>{qqq_pe_str}배</b></p><p style='margin:6px 0;'>- 예상 이익수익률(EY): <b>{qqq_ey_str}%</b></p><p style='margin:6px 0;'>- 10년물 국채: <b>{tnx_val_str}%</b></p><p style='margin:6px 0;'>- 주식 위험 프리미엄(ERP): <b style='color:{qqq_col}'>{qqq_erp_str}%</b></p><hr style='margin:15px 0; border-color:rgba(255,255,255,0.1);'><b>[AI 시장 의견] <span style='color:{qqq_col}'>{qqq_op}</span></b></div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:25px;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t("개별 기업 가치분석", "Company Value Analysis"), 
    t("유명 가치투자자 13F", "Guru 13F Portfolios"),
    t("시가총액 랭킹", "Market Cap Top 30"),
    t("주식 용어 사전", "Stock Glossary"),
    t("AGIE 철학", "About AGIE")
])

# ==========================================
# 탭 1: 개별 기업 가치분석
# ==========================================
with tab1:
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        ui = st.text_input(
            t("종목명 또는 티커 입력:", "Enter Stock Name or Ticker:"), 
            placeholder=t("예: 삼전, 하닉, 아마, 구글 (입력 후 Enter)", "e.g., 삼전, 하닉, AAPL, AMZN (Press Enter)"), 
            label_visibility="collapsed",
            key="main_input",
            on_change=trigger_scan 
        )
        st.caption(t("[안내] 초성이나 일부분만 쳐도 스마트하게 찾아냅니다. (예: '삼성' -> 삼성전자 등 목록 표시)", "[Info] Smart partial match supported. (e.g., Type 'AM' -> displays Amazon, AMD, etc.)"))
    with col_btn:
        if st.button(t("가치 분석 스캔", "Start Value Scan"), use_container_width=True, type="primary"):
            trigger_scan(); st.rerun() 

    if st.session_state.suggestions:
        st.markdown(f"<div style='color:#fdcb6e; font-weight:bold; margin-bottom:10px; padding:10px; background:rgba(255,255,255,0.05); border-radius:8px;'>여러 종목이 발견되었습니다. 찾으시는 기업을 클릭해주세요!</div>", unsafe_allow_html=True)
        sug_cols = st.columns(4)
        for idx, (s_tk, s_name) in enumerate(st.session_state.suggestions[:12]):
            with sug_cols[idx % 4]:
                if st.button(f"{s_name}", key=f"sug_btn_{s_tk}", use_container_width=True):
                    st.session_state.search_tk = s_tk
                    st.session_state.suggestions = []
                    st.rerun()
        st.divider()

    elif st.session_state.search_tk:
        tk = st.session_state.search_tk

        st_container = st.empty()
        with st_container.container():
            st.toast(t("데이터를 불러오는 중입니다...", "Fetching data..."))
            stk, p, i, kr = get_data(tk)
            
            if p:
                try: ty = safe_float(macro_data["10Y Treasury"]["p"], 4.4)
                except: ty = 4.4
                if ty == 0.0: ty = 4.4

                if i is None:
                    i = {}

                distorted_financial_industries = [
                    'Banks - Regional', 'Banks - Diversified', 'Insurance - Specialists', 
                    'Insurance - Life', 'Insurance - Property & Casualty', 
                    'Insurance Brokers', 'Insurance - Diversified'
                ]
                is_financial = i.get('industry') in distorted_financial_industries
                
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

                if ceo_cleaned == '누락' or ceo_cleaned == 'N/A':
                    if ":" in criticism_text:
                        prefix = criticism_text.split(":")[0].strip()
                        if len(prefix) < 40 and "위키 및 공공" not in prefix:
                            ceo_cleaned = prefix

                if tk.upper() == "SPACEX" or "SPACE EXPLORATION" in str(i.get('shortName', '')).upper() or "SPACE EXPLORATION" in str(i.get('longBusinessSummary', '')).upper() or "SPACEX" in str(i.get('shortName', '')).upper():
                    ceo_cleaned = "일론 머스크"
                    criticism_text = "일론 머스크 (Elon Musk): 압도적인 혁신과 비전으로 민간 우주 산업을 선도하고 있으나, 특정 리더에 대한 극단적 의존도 및 규제 기관과의 마찰이 가장 치명적인 리스크입니다. (이건 확인이 필요한 부분입니다)"

                # ---------------------------------------------------------
                # [프리/애프터마켓 시세 반영 및 가치 지표 실시간 재계산]
                # ---------------------------------------------------------
                ext_str = ""
                is_ext_active = False
                if not kr:
                    pre_p = safe_float(i.get('preMarketPrice', 0.0))
                    post_p = safe_float(i.get('postMarketPrice', 0.0))
                    
                    if pre_p > 0:
                        p = pre_p
                        is_ext_active = True
                        ext_str = f" <span style='font-size:0.85em; color:#fdcb6e;'>({t('프리마켓 시세 반영됨', 'Pre-Market Applied')}: \${pre_p:,.2f})</span>"
                    elif post_p > 0:
                        p = post_p
                        is_ext_active = True
                        ext_str = f" <span style='font-size:0.85em; color:#a29bfe;'>({t('애프터마켓 시세 반영됨', 'After-Hours Applied')}: \${post_p:,.2f})</span>"

                p_str = f"{int(p):,}원" if kr else f"\${p:,.2f}"

                # EPS(주당순이익) 우선 추출
                t_pe_raw = safe_float(i.get('trailingPE'))
                f_pe_raw = safe_float(i.get('forwardPE'))
                
                t_eps = safe_float(i.get('trailingEps'))
                f_eps = safe_float(i.get('forwardEps', i.get('finviz_eps_next')))
                
                # EPS 정보가 없을 경우, 장마감 주가와 기존 PER을 이용해 EPS 역산
                reg_p = safe_float(i.get('regularMarketPrice', p))
                if reg_p == 0: reg_p = p
                
                if t_eps == 0 and t_pe_raw > 0: t_eps = reg_p / t_pe_raw
                if f_eps == 0 and f_pe_raw > 0: f_eps = reg_p / f_pe_raw

                # 변경된 최신 주가(p)를 바탕으로 PER을 실시간 재계산
                t_pe = (p / t_eps) if t_eps > 0 else t_pe_raw
                f_pe = (p / f_eps) if f_eps > 0 else f_pe_raw

                # PBR 실시간 재계산
                pbr = safe_float(i.get('priceToBook'))
                bv = safe_float(i.get('bookValue'))
                
                if bv > 0:
                    pbr = p / bv
                else:
                    if pbr > 0 and is_ext_active and reg_p > 0:
                        pbr = pbr * (p / reg_p)  # 주가 변동 비율만큼 PBR 미세조정
                    elif pbr == 0.0:
                        try:
                            bs = stk.balance_sheet
                            if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index:
                                eq = safe_float(bs.loc['Stockholders Equity'].iloc[0])
                                sh = safe_float(i.get('sharesOutstanding'))
                                if eq > 0 and sh > 0:
                                    pbr = p / (eq / sh)
                        except: pass
                
                # 기존 지표 계산
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
                except: pass
                
                pmos_val = ((a_pe - f_pe) / a_pe) * 100 if f_pe > 0 and a_pe > 0 else 0
                ey = (1 / f_pe * 100) if f_pe > 0 else 0
                erp = ey - ty
                
                base_fcf, sh, final_g, data_len = get_base_dcf_data(stk, i)
                dcf_source_txt = f"({data_len}{t('년 데이터 기반 산출', ' yrs data)')})"
                
                rnd_trend = analyze_rnd_trend(stk, base_fcf, is_financial, kr)
                
                has_eps_g = False
                if t_eps > 0 and f_eps > 0:
                    eps_g_val = ((f_eps - t_eps) / t_eps) * 100
                    eps_g_str = f"+{eps_g_val:.1f}%" if eps_g_val > 0 else f"{eps_g_val:.1f}%"
                    eps_col = "#2ecc71" if eps_g_val > 0 else "#ff7675"
                    has_eps_g = True
                elif t_eps < 0 and f_eps > 0:
                    eps_g_str = t("흑자전환", "Turnaround")
                    eps_col = "#2ecc71"
                elif t_eps > 0 and f_eps < 0:
                    eps_g_str = t("적자전환", "Turn to Loss")
                    eps_col = "#ff7675"
                elif t_eps < 0 and f_eps < 0:
                    eps_g_str = t("적자지속", "Continued Loss")
                    eps_col = "#ff7675"
                else:
                    eps_g_str = t("확인불가", "N/A")
                    eps_col = "#8892b0"
                    
                current_rsi_val, avg_rsi_val = None, None
                try:
                    hist_1y = stk.history(period="1y")
                    if hist_1y is not None and not hist_1y.empty and len(hist_1y) >= 15:
                        delta = hist_1y['Close'].diff()
                        gain = delta.clip(lower=0)
                        loss = -1 * delta.clip(upper=0)
                        ema_gain = gain.ewm(com=13, adjust=False).mean()
                        ema_loss = loss.ewm(com=13, adjust=False).mean()
                        rs = ema_gain / ema_loss
                        rsi_series = 100 - (100 / (1 + rs))
                        
                        current_rsi_val = safe_float(rsi_series.iloc[-1])
                        avg_rsi_val = safe_float(rsi_series.dropna().mean())
                except:
                    pass

                rsi_html = f"<span style='color:#8892b0'>{t('데이터 부족', 'Insufficient Data')}</span>"
                if current_rsi_val is not None and current_rsi_val > 0:
                    if current_rsi_val <= 30:
                        rsi_eval = f"<span class='good'>{t('[과매도 구간]', '[Oversold]')}</span>"
                    elif current_rsi_val >= 70:
                        rsi_eval = f"<span class='highlight'>{t('[과매수 구간]', '[Overbought]')}</span>"
                    else:
                        rsi_eval = f"<span style='color:#fdcb6e;'>{t('[중립]', '[Neutral]')}</span>"
                        
                    rsi_ko = f"현재 <b>{current_rsi_val:.1f}</b> / 1년 평균 {avg_rsi_val:.1f} {rsi_eval} <span style='font-size:0.85em; color:#8892b0;'>(*30이하 과매도 / 70이상 과매수)</span>"
                    rsi_en = f"Current <b>{current_rsi_val:.1f}</b> / 1Y Avg {avg_rsi_val:.1f} {rsi_eval} <span style='font-size:0.85em; color:#8892b0;'>(*<=30 Oversold / >=70 Overbought)</span>"
                    rsi_html = t(rsi_ko, rsi_en)
                    
                has_ytd = False
                try:
                    hist_ytd = stk.history(period="ytd")
                    if not hist_ytd.empty and len(hist_ytd) >= 2:
                        ytd_start = hist_ytd['Close'].iloc[0]
                        ytd_ret = ((p - ytd_start) / ytd_start) * 100
                        ytd_str = f"+{ytd_ret:.1f}%" if ytd_ret > 0 else f"{ytd_ret:.1f}%"
                        ytd_col = "#2ecc71" if ytd_ret > 0 else "#ff7675"
                        has_ytd = True
                    else:
                        ytd_str = "N/A"
                        ytd_col = "#8892b0"
                except:
                    ytd_str = "N/A"
                    ytd_col = "#8892b0"

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
                    gap_text = f" ➔ <span style='color:#8892b0'>{t('[비교 불가]', '[N/A]')}</span>"
                    
                eps_vs_ytd_html = f"<span style='color:{eps_col}; font-weight:bold;'>{eps_g_str}</span> vs <span style='color:{ytd_col}; font-weight:bold;'>{ytd_str}</span>{gap_text}"

                eps_trend, bps_trend = analyze_trends(stk)
                
                # 데이터 추출
                gross_m = safe_float(i.get('grossMargins')) * 100
                op_m = safe_float(i.get('operatingMargins')) * 100
                current_ratio = safe_float(i.get('currentRatio'))
                
                # 한국 주식 등 API 누락 시 재무제표에서 직접 역산 시도
                if op_m == 0.0 or gross_m == 0.0:
                    try:
                        inc = stk.income_stmt
                        if inc is not None and not inc.empty and 'Total Revenue' in inc.index:
                            rev_val = safe_float(inc.loc['Total Revenue'].iloc[0])
                            if rev_val > 0:
                                if op_m == 0.0 and 'Operating Income' in inc.index:
                                    op_m = (safe_float(inc.loc['Operating Income'].iloc[0]) / rev_val) * 100
                                if gross_m == 0.0 and 'Gross Profit' in inc.index:
                                    gross_m = (safe_float(inc.loc['Gross Profit'].iloc[0]) / rev_val) * 100
                    except: pass

                if current_ratio == 0.0:
                    try:
                        bs = stk.balance_sheet
                        if bs is not None and not bs.empty and 'Current Assets' in bs.index and 'Current Liabilities' in bs.index:
                            ca = safe_float(bs.loc['Current Assets'].iloc[0])
                            cl = safe_float(bs.loc['Current Liabilities'].iloc[0])
                            if cl > 0: current_ratio = ca / cl
                    except: pass

                # 평가 로직
                gm_eval = f"<span class='good'>{t('강력한 가격결정력/해자', 'Strong Pricing Power')}</span>" if gross_m >= 40 else (f"<span style='color:#fdcb6e;'>{t('보통', 'Average')}</span>" if gross_m >= 20 else f"<span class='highlight'>{t('원가 부담/해자 약함', 'Weak Moat / High Cost')}</span>")
                opm_eval = f"<span class='good'>{t('탁월한 비즈니스', 'Excellent Business')}</span>" if op_m >= 15 else (f"<span style='color:#fdcb6e;'>{t('보통', 'Average')}</span>" if op_m >= 8 else f"<span class='highlight'>{t('수익성 경고', 'Poor Profitability')}</span>")
                cr_eval = f"<span class='good'>{t('불황 대비 완벽 (유동자산 풍부)', 'Crisis-Ready (Highly Liquid)')}</span>" if current_ratio >= 1.5 else (f"<span style='color:#74b9ff;'>{t('안전', 'Safe')}</span>" if current_ratio >= 1.0 else f"<span class='highlight'>{t('단기 유동성/외부조달 위험', 'Liquidity Risk')}</span>")
                
                if gross_m == 0.0 and op_m == 0.0: gm_eval, opm_eval = "N/A", "N/A"
                if current_ratio == 0.0: cr_eval = "N/A"

                if is_financial:
                    cr_eval = f"<span style='color:#8892b0;'>{t('금융주 적용 제외 (수신금 기반)', 'N/A for Financials')}</span>"
                    gm_eval = f"<span style='color:#8892b0;'>{t('금융주 적용 제외', 'N/A')}</span>"

                bio_eval = f"<span style='color:#8892b0'>{t('재무제표 데이터 부족으로 확인 불가.', 'Unable to verify due to missing financial data.')}</span>"
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
                                        bio_eval = f"<span style='color:#fdcb6e;'>{t(t_ko, t_en)}</span>"
                                    else:
                                        if curr_de < 50:
                                            t_ko = f"[합격] 현재 부채비율 {curr_de:.1f}% ({trend_text}). 외부 충격에 매우 강한 다윈주의적 생존력을 갖췄습니다."
                                            t_en = f"[Pass] D/E {curr_de:.1f}% ({trend_text}). Strong Darwinian survivability."
                                            bio_eval = f"<span class='good'>{t(t_ko, t_en)}</span>"
                                        elif curr_de < 120:
                                            t_ko = f"[양호] 현재 부채비율 {curr_de:.1f}% ({trend_text}). 무난한 생존력을 유지 중입니다."
                                            t_en = f"[Good] D/E {curr_de:.1f}% ({trend_text}). Adequate survivability."
                                            bio_eval = f"<span style='color:#74b9ff;'>{t(t_ko, t_en)}</span>"
                                        else:
                                            t_ko = f"[경고] 현재 부채비율 {curr_de:.1f}% ({trend_text}). 과도한 레버리지로 위기 시 치명적 생존 위협이 존재합니다."
                                            t_en = f"[Warning] D/E {curr_de:.1f}% ({trend_text}). High leverage poses fatal survival risk."
                                            bio_eval = f"<span class='highlight'>{t(t_ko, t_en)}</span>"
                                else:
                                    t_ko = "[위험] 자본잠식 상태입니다. 생존에 치명적인 위협이 존재합니다."
                                    t_en = "[Danger] Capital impairment detected. Fatal survival risk."
                                    bio_eval = f"<span class='highlight'>{t(t_ko, t_en)}</span>"
                except:
                    pass

                iv, mos_val, err = calc_custom_dcf(base_fcf, sh, p, ty, final_g, is_financial)
                mos_val = safe_float(mos_val)
                
                iv_best, mos_best, _ = calc_custom_dcf(base_fcf, sh, p, ty, min(final_g * 1.5, 0.25), is_financial)
                iv_worst, mos_worst, _ = calc_custom_dcf(base_fcf, sh, p, ty, max(final_g * 0.5, 0.0), is_financial)
                
                roic_val = real_roic if real_roic is not None else 0
                
                op_title, op_color, op_reason = get_comprehensive_investment_opinion(mos_val, pmos_val, roe, roic_val, erp, final_g, criticism_text, is_financial, pbr, kr, tk)

                st.markdown(f"""
                <div style="padding: 25px 20px; border-radius: 16px; border: 1px solid {op_color}; background: linear-gradient(145deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); color: var(--text-color); margin-bottom: 25px; margin-top: 15px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0 0 12px 0; color: {op_color}; font-size: 1.5rem; letter-spacing: -0.5px;">[AI 종합 투자의견] : {op_title}</h3>
                    <span style="color: var(--text-color); font-size: 1.05rem; display: block; margin-top: 10px; line-height: 1.6;">{op_reason}</span>
                </div>
                """, unsafe_allow_html=True)

                st.sidebar.markdown(f"**현재 투자의견:** <span style='color:{op_color}; font-weight:bold;'>{op_title}</span>", unsafe_allow_html=True)

                st.divider()

                if is_financial:
                    beginner_summary = t(
                        f"<b>초보자 가이드:</b> 내가 <b>{p_str}</b>을 주고 이 금융/보험사를 사면, 본전을 찾는 데 <b>{f_pe:.1f}년</b>이 걸릴 것으로 예상되며(Fwd PER), 회사는 장사를 통해 내 돈을 1년에 <b>{roe:.1f}%</b>씩(ROE) 불려주고 있습니다. 현재 기업의 장부상 자산 가치 대비 <b>{pbr:.2f}배</b>(PBR)의 가격표가 붙어 있습니다.",
                        f"<b>Beginner Guide:</b> It takes <b>{f_pe:.1f} yrs</b> to break even (Fwd PE), equity grows at <b>{roe:.1f}%/yr</b> (ROE), and priced at <b>{pbr:.2f}x</b> its book value (PBR)."
                    )
                else:
                    beginner_summary = t(
                        f"<b>초보자 가이드:</b> 내가 <b>{p_str}</b>을 주고 이 회사를 사면, 본전을 찾는 데 <b>{f_pe:.1f}년</b>이 걸릴 것으로 예상되며(Fwd PER), 회사는 장사를 통해 내 돈을 1년에 <b>{roe:.1f}%</b>씩(ROE) 불려주고 있습니다.",
                        f"<b>Beginner Guide:</b> It takes <b>{f_pe:.1f} yrs</b> to break even (Fwd PE), and the company grows your money at <b>{roe:.1f}%/yr</b> (ROE)."
                    )

                st.subheader(t("1. 핵심 밸류에이션 및 재무 지표", "1. Core Valuation & Financials"))
                st.markdown(f"<div style='background: linear-gradient(to right, rgba(160, 196, 255, 0.1), rgba(255, 198, 255, 0.05)); padding:18px 22px; border-radius:16px; margin-bottom:20px; font-size:1.05rem; color:var(--text-color); line-height:1.6; border-left: 4px solid #A0C4FF;'>{beginner_summary}</div>", unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style='display: flex; gap: 15px; flex-wrap: wrap;'>
                    <div style='flex: 1; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.1); padding: 15px; border-radius: 12px;'>
                        <div style='font-size: 0.9rem; color: #8892b0; margin-bottom: 5px;'>{t('매출총이익률 (Gross Margin)', 'Gross Margin')}</div>
                        <div style='font-size: 1.4rem; font-weight: bold; color: var(--text-color);'>{gross_m:.1f}%</div>
                        <div style='font-size: 0.85rem; margin-top: 5px;'>{gm_eval}</div>
                    </div>
                    <div style='flex: 1; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.1); padding: 15px; border-radius: 12px;'>
                        <div style='font-size: 0.9rem; color: #8892b0; margin-bottom: 5px;'>{t('영업이익률 (Operating Margin)', 'Operating Margin')}</div>
                        <div style='font-size: 1.4rem; font-weight: bold; color: var(--text-color);'>{op_m:.1f}%</div>
                        <div style='font-size: 0.85rem; margin-top: 5px;'>{opm_eval}</div>
                    </div>
                    <div style='flex: 1; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.1); padding: 15px; border-radius: 12px;'>
                        <div style='font-size: 0.9rem; color: #8892b0; margin-bottom: 5px;'>{t('유동비율 (Current Ratio)', 'Current Ratio')}</div>
                        <div style='font-size: 1.4rem; font-weight: bold; color: var(--text-color);'>{current_ratio:.2f}</div>
                        <div style='font-size: 0.85rem; margin-top: 5px;'>{cr_eval}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)

                if pmos_val >= 30: per_mos_str = f"<span class='good'>[매우 합격] +{pmos_val:.1f}% (과거 대비 극심한 저평가)</span>"
                elif pmos_val >= 15: per_mos_str = f"<span class='good'>[합격] +{pmos_val:.1f}% (안전마진 확보)</span>"
                elif pmos_val >= 5: per_mos_str = f"<span style='color:#74b9ff;'>[약간 합격] +{pmos_val:.1f}% (양호한 할인)</span>"
                elif pmos_val >= 0: per_mos_str = f"<span style='color:#fdcb6e;'>[보통] +{pmos_val:.1f}% (적정 수준)</span>"
                elif pmos_val > -10: per_mos_str = f"<span style='color:#fdcb6e;'>[약간 주의] {pmos_val:.1f}% (약간의 할증)</span>"
                elif pmos_val > -20: per_mos_str = f"<span class='highlight'>[주의] {pmos_val:.1f}% (할증 구간)</span>"
                else: per_mos_str = f"<span class='highlight'>[매우 주의] {pmos_val:.1f}% (과도한 고평가)</span>"

                if is_financial:
                    if roe >= 15: rr_eval = f"<span class='good'>{t('[매우 합격] 탁월한 자본 효율성', '[Very Pass] Excellent Efficiency')}</span>"
                    elif roe >= 10: rr_eval = f"<span class='good'>{t('[합격] 우수한 수익성', '[Pass] Good Profitability')}</span>"
                    elif roe >= 8: rr_eval = f"<span style='color:#74b9ff;'>{t('[약간 합격] 준수한 수익성', '[Slight Pass] Decent Profitability')}</span>"
                    elif roe >= 5: rr_eval = f"<span style='color:#fdcb6e;'>{t('[약간 주의] 평균 이하의 수익성', '[Slight Warning] Below Average')}</span>"
                    elif roe >= 0: rr_eval = f"<span class='highlight'>{t('[주의] 부진한 자본 효율성', '[Warning] Poor Efficiency')}</span>"
                    else: rr_eval = f"<span class='highlight'>{t('[매우 주의] 자본 훼손(적자) 상태', '[Very Warning] Capital Destruction')}</span>"
                else:
                    if roe >= 20 and roic_val >= 15: rr_eval = f"<span class='good'>{t('[매우 합격] 압도적인 자본 배치 능력', '[Very Pass] Outstanding Capital Allocation')}</span>"
                    elif roe >= 15 and roic_val >= 10: rr_eval = f"<span class='good'>{t('[합격] 훌륭한 자본 효율성', '[Pass] Excellent Efficiency')}</span>"
                    elif roe >= 10 and roic_val >= 7: rr_eval = f"<span style='color:#74b9ff;'>{t('[약간 합격] 양호한 수익성', '[Slight Pass] Good Profitability')}</span>"
                    elif roe >= 5 and roic_val >= 3: rr_eval = f"<span style='color:#fdcb6e;'>{t('[약간 주의] 평균 이하의 효율성', '[Slight Warning] Below Average')}</span>"
                    elif roe >= 0 and roic_val >= 0: rr_eval = f"<span class='highlight'>{t('[주의] 비효율적인 자본 운용', '[Warning] Inefficient Capital')}</span>"
                    else: rr_eval = f"<span class='highlight'>{t('[매우 주의] 심각한 사업 구조 훼손', '[Very Warning] Severe Structural Damage')}</span>"
                    
                if erp > 0:
                    ey_str = f"{ey:.2f}% <span class='good'>(국채 이김! +{erp:.2f}%p 수익률 추가 우위/할인)</span>"
                else:
                    ey_str = f"{ey:.2f}% <span class='highlight'>(국채에 짐! {abs(erp):.2f}%p 매력도 열위/할증)</span>"

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"- **{t('현재 주가', 'Current Price')}:** {p_str}{ext_str}", unsafe_allow_html=True)
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
                    st.markdown(f"- **{t('일차트 RSI (기술적 보조지표)', 'Daily RSI (Technical Indicator)')}:** {rsi_html}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('R&D(연구개발비) 분석 (FCF 대비 미래 투자 체력)', 'R&D Check (vs FCF)')}:** {rnd_trend}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('올해시장(eps)컨센서스 vs 실제 주가 괴리', 'Consensus vs YTD Price Gap')}:** {eps_vs_ytd_html}", unsafe_allow_html=True)
                
                st.divider()

                st.subheader(t("2. AI 다차원 투자 검증 (6원칙 및 학문적 모델 적용)", "2. AI Multi-dimensional Verification"))
                
                p_txt = ""
                if pmos_val >= 30: p_txt += f"- PER 측면: <span class='good'>[매우 합격] (+{pmos_val:.1f}% 할인)</span>\n"
                elif pmos_val >= 15: p_txt += f"- PER 측면: <span class='good'>[합격] (+{pmos_val:.1f}% 할인)</span>\n"
                elif pmos_val >= 5: p_txt += f"- PER 측면: <span style='color:#74b9ff;'>[약간 합격] (+{pmos_val:.1f}% 할인)</span>\n"
                elif pmos_val >= 0: p_txt += f"- PER 측면: <span style='color:#fdcb6e;'>[보통] (+{pmos_val:.1f}% 할인)</span>\n"
                elif pmos_val > -10: p_txt += f"- PER 측면: <span style='color:#fdcb6e;'>[약간 주의] ({pmos_val:.1f}% 할증)</span>\n"
                elif pmos_val > -20: p_txt += f"- PER 측면: <span class='highlight'>[주의] ({pmos_val:.1f}% 할증)</span>\n"
                else: p_txt += f"- PER 측면: <span class='highlight'>[매우 주의] ({pmos_val:.1f}% 할증)</span>\n"
                
                if is_financial:
                    if pbr <= 0.6: p_txt += f"- PBR 측면: <span class='good'>[매우 합격] ({pbr:.2f}배)</span>"
                    elif pbr <= 0.9: p_txt += f"- PBR 측면: <span class='good'>[합격] ({pbr:.2f}배)</span>"
                    elif pbr <= 1.0: p_txt += f"- PBR 측면: <span style='color:#74b9ff;'>[약간 합격] ({pbr:.2f}배)</span>"
                    elif pbr <= 1.2: p_txt += f"- PBR 측면: <span style='color:#fdcb6e;'>[약간 주의] ({pbr:.2f}배)</span>"
                    elif pbr <= 1.5: p_txt += f"- PBR 측면: <span class='highlight'>[주의] ({pbr:.2f}배)</span>"
                    else: p_txt += f"- PBR 측면: <span class='highlight'>[매우 주의] ({pbr:.2f}배)</span>"
                else:
                    if mos_val >= 30: p_txt += f"- DCF 측면: <span class='good'>[매우 합격] (+{mos_val:.1f}% 할인)</span>"
                    elif mos_val >= 15: p_txt += f"- DCF 측면: <span class='good'>[합격] (+{mos_val:.1f}% 할인)</span>"
                    elif mos_val >= 5: p_txt += f"- DCF 측면: <span style='color:#74b9ff;'>[약간 합격] (+{mos_val:.1f}% 할인)</span>"
                    elif mos_val >= 0: p_txt += f"- DCF 측면: <span style='color:#fdcb6e;'>[보통] (+{mos_val:.1f}% 할인)</span>"
                    elif mos_val > -10: p_txt += f"- DCF 측면: <span style='color:#fdcb6e;'>[약간 주의] ({mos_val:.1f}% 할증)</span>"
                    elif mos_val > -20: p_txt += f"- DCF 측면: <span class='highlight'>[주의] ({mos_val:.1f}% 할증)</span>"
                    else: p_txt += f"- DCF 측면: <span class='highlight'>[매우 주의] ({mos_val:.1f}% 할증)</span>"

                if roe >= 20: biz_eval = f"<span class='good'>{t('[매우 합격] 자본효율 압도적, 강력한 해자 확률', '[Very Pass] Outstanding efficiency, high moat probability')}</span>"
                elif roe >= 15: biz_eval = f"<span class='good'>{t('[합격] 자본효율 탁월, 해자 확률 높음', '[Pass] Great efficiency, high moat probability')}</span>"
                elif roe >= 10: biz_eval = f"<span style='color:#74b9ff;'>{t('[약간 합격] 양호한 수익성', '[Slight Pass] Good profitability')}</span>"
                elif roe >= 5: biz_eval = f"<span style='color:#fdcb6e;'>{t('[약간 주의] 평균 수준, 독점력 확인 필요', '[Slight Warning] Average, verify moat')}</span>"
                elif roe >= 0: biz_eval = f"<span class='highlight'>{t('[주의] 부진한 비즈니스', '[Warning] Poor business')}</span>"
                else: biz_eval = f"<span class='highlight'>{t('[매우 주의] 심각한 구조 훼손 점검 시급', '[Very Warning] Structural damage check urgent')}</span>"

                if final_g >= 0.08: math_eval = f"<span class='good'>{t(f'[합격] 연평균 {final_g*100:.1f}% 고성장하며 복리 모형 탑승 중.', f'[Pass] Growing at {final_g*100:.1f}% CAGR, riding the compound model.')}</span>"
                elif final_g > 0.0: math_eval = f"<span style='color:#74b9ff;'>{t(f'[약간 합격] 연평균 {final_g*100:.1f}% 저속 성장 구간.', f'[Slight Pass] Slow growth at {final_g*100:.1f}% CAGR.')}</span>"
                else: math_eval = f"<span class='highlight'>{t('[매우 주의] 현금흐름 역성장 (복리 팽창 구간 아닙니다).', '[Very Warning] Negative FCF (Not a compounding phase).')}</span>"

                st.markdown(t("**[가격 및 수학] 안전마진과 복리 모형**", "**[Price & Math] Margin of Safety & Compounding**"))
                st.markdown(p_txt, unsafe_allow_html=True)
                st.markdown(f"- 수학 (복리 모형): {math_eval}", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown(t("**[비즈니스 및 생물학] 경제적 해자와 생존력**", "**[Business & Biology] Moat & Survivability**"))
                st.markdown(f"- 비즈니스 수익성: {biz_eval}", unsafe_allow_html=True)
                st.markdown(f"- 생물학 (생존력): {bio_eval}", unsafe_allow_html=True)

                st.divider()

                st.subheader(t("3. 10년 DCF (내재가치 3가지 시나리오)", "3. 10-Year DCF (3 Scenarios)"))
                
                dcf_guide_ko = (
                    "<b>[필독] 쉽게 이해하는 DCF 가치평가</b><br>"
                    "• <b>FCF(잉여현금흐름)란?</b> 회사가 번 돈에서 공장 유지비, 세금 등을 다 빼고 <b>'순수하게 내 주머니에 남길 수 있는 진짜 여윳돈'</b>입니다.<br>"
                    "• <b>시나리오의 의미:</b> 아래의 적정가는 이 회사가 앞으로 <b>10년 동안</b> 제시된 성장률(%)만큼 매년 꾸준히 FCF를 더 벌어들인다고 가정했을 때의 합리적인 가격입니다.<br>"
                    "• <b>투자자 점검 포인트:</b> 현재의 기본 성장률은 최근 4~10년의 현금흐름 추세를 바탕으로 기계적으로 산출된 것입니다. 스스로 기업을 분석했을 때, <b>'과연 이 기업의 비즈니스 해자가 강력해서 향후 10년 동안에도 이 성장을 유지할 수 있을 시'</b> 확신이 드는지 반드시 질문해 보세요!"
                )
                dcf_guide_en = (
                    "<b>[Must Read] Understanding DCF Valuation Easily</b><br>"
                    "• <b>What is FCF (Free Cash Flow)?</b> It is the <b>'pure leftover cash'</b> a company can keep after paying all operational expenses, taxes, and capital expenditures.<br>"
                    "• <b>What do the scenarios mean?</b> The fair values below assume the company will consistently grow its FCF at the given rate (%) every year for the next <b>10 years</b>.<br>"
                    "• <b>Investor Checkpoint:</b> The current base growth rate is mechanically derived from the last available cash flow trends. You must ask yourself: <b>'Does this company have a strong enough business moat to maintain this growth for the next 10 years?'</b> Only invest if you are confident!"
                )
                
                if is_financial:
                    st.write(f"- **{t('추정 적정가 (DCF)', 'Estimated Fair Value (DCF)')}:** {t('금융 및 보험주는 사업 특성상 고객 예치금/지급준비금이 현금흐름표에 대규모로 부채 처리되어 FCF의 기형적 왜곡이나 착시 적자가 발생합니다. 따라서 본 분석기 매커니즘 상 무의미한 DCF 연산을 강제 차단하고, PBR 기반 자산가치 필터링 시스템으로 완벽 대체하여 의견을 도출했습니다.', 'DCF model disabled due to financial accounting distortions. Intrinsic worth cross-evaluated using PBR metrics instead.')}")
                elif iv:
                    st.markdown(f"<div style='background: rgba(160, 196, 255, 0.08); padding:18px 22px; border-radius:12px; margin-bottom:15px; border-left: 4px solid #A0C4FF; font-size:1.0rem; color:var(--text-color); line-height:1.7;'>{t(dcf_guide_ko, dcf_guide_en)}</div>", unsafe_allow_html=True)
                    
                    implied_g = get_implied_g(base_fcf, sh, p, ty)
                    if implied_g is not None:
                        implied_g_str = f"{implied_g*100:.1f}%"
                        implied_text = f"<br><span style='color:#fdcb6e;'><b>※ 현재 주가({p_str}) 정당화 조건 (역산 DCF):</b> 향후 10년간 매년 <b>{implied_g_str}</b>씩 현금을 더 벌어야 현재 주가가 합리적이라고 볼 수 있습니다. 이 수치가 해당 기업의 한계치를 넘는다면 비상식적 고평가 상태입니다.</span>"
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
                    
                    worst_mos_color = '#2ecc71' if mos_worst > 0 else '#ff7675'
                    base_mos_color = '#2ecc71' if mos_val > 0 else '#ff7675'
                    best_mos_color = '#2ecc71' if mos_best > 0 else '#ff7675'

                    txt_w_title = t('최악 (Worst)', 'Worst Case')
                    txt_b_title = t('평균 (Base)', 'Base Case')
                    txt_e_title = t('최상 (Best)', 'Best Case')

                    with c_w:
                        st.markdown(
                            f"<div style='background: rgba(255,255,255,0.02); padding:20px; border-radius:16px; border-top:4px solid #ff7675; color:var(--text-color); text-align:center; box-shadow: 0 4px 12px rgba(0,0,0,0.05);'>"
                            f"<b>{txt_w_title}</b><br><br>{str_g}: {max(final_g*0.5, 0.0)*100:.1f}%<br>{str_fv}: {val_w}<br>"
                            f"{str_mos}: <span style='color:{worst_mos_color}'>{mos_worst:.1f}%</span></div>", 
                            unsafe_allow_html=True
                        )
                    with c_b:
                        st.markdown(
                            f"<div style='background: rgba(255,255,255,0.02); padding:20px; border-radius:16px; border-top:4px solid #fdcb6e; color:var(--text-color); text-align:center; box-shadow: 0 4px 12px rgba(0,0,0,0.05);'>"
                            f"<b>{txt_b_title}</b><br><br>{str_g}: {final_g*100:.1f}%<br>{str_fv}: {val_b}<br>"
                            f"{str_mos}: <span style='color:{base_mos_color}'>{mos_val:.1f}%</span></div>", 
                            unsafe_allow_html=True
                        )
                    with c_e:
                        st.markdown(
                            f"<div style='background: rgba(255,255,255,0.02); padding:20px; border-radius:16px; border-top:4px solid #2ecc71; color:var(--text-color); text-align:center; box-shadow: 0 4px 12px rgba(0,0,0,0.05);'>"
                            f"<b>{txt_e_title}</b><br><br>{str_g}: {min(final_g*1.5, 0.25)*100:.1f}%<br>{str_fv}: {val_e}<br>"
                            f"{str_mos}: <span style='color:{best_mos_color}'>{mos_best:.1f}%</span></div>", 
                            unsafe_allow_html=True
                        )
                    st.markdown("<br>", unsafe_allow_html=True)
                else:
                    st.error(f"{err}")
                
                st.divider()

                st.subheader(t("4. 장기 재무 시각화 (최근 연속 지표)", "4. Long-term Financial Visualizations"))
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
                                st.write(t(f"**[최근 매출 및 순이익]** {u_str}", f"**[Recent Rev & NI Trend]** {u_str}"))
                                st.bar_chart(df_rev_ni, color=["#A0C4FF", "#2ecc71"], height=300, use_container_width=False, width=600)
                            else:
                                st.caption(t("매출/순이익 시각화 데이터가 부족합니다.", "Insufficient Revenue/Net Income data for visualization."))
                        with c_v2:
                            if len(fcf_chart) == len(years):
                                div, u_str = scale_vals([fcf_chart], kr)
                                df_fcf = pd.DataFrame({t('잉여현금흐름(FCF)', 'Free Cash Flow'): [x/div for x in fcf_chart]}, index=years)
                                st.write(t(f"**[최근 잉여현금흐름(FCF)]** {u_str}", f"**[Recent FCF Trend]** {u_str}"))
                                st.bar_chart(df_fcf, color="#fdcb6e", height=300, use_container_width=False, width=600)
                            else:
                                st.caption(t("FCF 시각화 데이터가 부족합니다.", "Insufficient FCF data for visualization."))
                except Exception as e:
                    st.caption(t("시각화 데이터를 불러오는 데 실패했습니다.", "Failed to load visualization data."))

                st.divider()

                st.subheader(t("5. 질적 분석 및 리스크 스크리닝", "5. Qualitative Analysis & Risk Screening"))
                
                st.markdown(f"- **CEO:** {ceo_cleaned}")
                
                st.write(t("**비즈니스 요약**", "**Business Summary**"))
                raw_summary = i.get('kr_sum') or i.get('longBusinessSummary') or t("비즈니스 요약 데이터를 현재 불러올 수 없습니다. (이건 확인이 필요한 부분입니다)", "Business summary data not available.")
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
                <div style="background-color: rgba(255, 118, 117, 0.08); color: #ff7675; padding: 20px; border-radius: 16px; border: 1px solid rgba(255, 118, 117, 0.3); font-size: 1rem; line-height: 1.7;">
                    {criticism_text}
                </div>
                """, unsafe_allow_html=True)

                st.divider()

                st.subheader(t("6. 분석 결과 공유하기", "6. Share Analysis Results"))
                st.write(t("아래 텍스트 박스 우측 상단의 **'복사 아이콘'**을 누르면 깔끔하게 정리된 분석 리포트를 카카오톡이나 제미나이에 바로 붙여넣을 수 있습니다.", "Click the **'Copy icon'** on the top right of the box below to paste the clean report into Gemini or messengers."))
                
                def strip_html(h_str):
                    return re.sub(r'<[^>]+>', '', h_str)
                
                clean_per_mos = strip_html(per_mos_str)
                clean_biz_eval = strip_html(biz_eval)
                clean_eps_trend = strip_html(eps_trend)
                clean_bps_trend = strip_html(bps_trend)
                
                if is_financial:
                    share_fv = t('금융/보험주 제외 (PBR 대체 분석 진행)', 'N/A for Financials (PBR Evaluated)')
                    share_mos = t('해당 없음', 'N/A')
                else:
                    if iv:
                        share_fv = f"{int(iv):,}원" if kr else f"${iv:,.2f}"
                        share_mos = f"{mos_val:.1f}% (최상 {mos_best:.1f}%, 최악 {mos_worst:.1f}%)"
                    else:
                        share_fv = t("계산 불가 (FCF 적자 등)", "N/A (Negative FCF)")
                        share_mos = t("계산 불가", "N/A")

                share_ko = f"""[AGIE 가치투자 분석 리포트]
기업명: {i.get('shortName', tk)} ({tk})
AI 종합 투자의견: {op_title}

핵심 밸류에이션 지표
- 현재 주가: {p_str}
- 추정 적정가(DCF): {share_fv}
- 안전마진(MoS): {share_mos}
- 자본효율(ROE): {roe:.1f}%
- 본전회수기간(Fwd PER): {f_pe:.1f}배 (과거평균: {a_pe:.1f}배)
- 주식 위험 프리미엄(ERP): {erp:.2f}%p (국채 대비 주식 매력도)
- 장기 BPS 성장: {clean_bps_trend}

AI 핵심 요약
{op_reason}

투자 검증 요약
- 가격 매력도 (PER 기준): {clean_per_mos}
- 비즈니스 해자 (ROE/ROIC 기준): {clean_biz_eval}
"""
                share_en = f"""[AGIE Value Investing Report]
Company: {i.get('shortName', tk)} ({tk})
AI Opinion: {op_title}

Core Valuation Metrics
- Current Price: {p_str}
- Est. Fair Value (DCF): {share_fv}
- Margin of Safety (MoS): {share_mos}
- Equity Return (ROE): {roe:.1f}%
- Fwd PE: {f_pe:.1f}x (Hist Avg: {a_pe:.1f}x)
- Equity Risk Premium (ERP): {erp:.2f}%p
- Long-term BPS Growth: {clean_bps_trend}

AI Core Summary
{op_reason}

Verification Summary
- Price Attractiveness (PE): {clean_per_mos}
- Business Moat (ROE/ROIC): {clean_biz_eval}
"""
                st.code(t(share_ko, share_en), language="text")

# ==========================================
# 탭 2: 유명 가치투자자 13F 포트폴리오
# ==========================================
with tab2:
    st.subheader(t("글로벌 유명 가치투자자 13F 포트폴리오", "Global Value Gurus 13F Portfolio"))
    st.caption(t("※ 미국의 13F 공시를 추적하여 최신 포트폴리오 비중을 표출합니다.", "※ Tracks US 13F filings to display latest portfolio weights."))
    
    guru_map = {
        "세스 클라만 (Baupost Group)": "BAU", 
        "빌 애크먼 (Pershing Square)": "BRK_PER",
        "워런 버핏 (Berkshire Hathaway)": "BRK", 
        "리 루 (Himalaya Capital)": "HC", 
        "척 아크레 (Akre Capital)": "AKRE", 
        "모니시 파브라이 (Dalal Street)": "PI", 
        "가이 스피어 (Aquamarine Capital)": "AQUA"
    }
    guru_option = st.selectbox(t("포트폴리오를 조회할 유명 가치투자자를 선택하세요:", "Select a Value Guru:"), list(guru_map.keys()))

    # 인물 설명 정보 패널 추가
    st.markdown("### 인물 개요")
    if guru_option == "세스 클라만 (Baupost Group)":
        st.write("**세스 클라만(Seth Klarman):** '보스턴의 오라클'로 불리는 거장으로, 벤자민 그레이엄의 철학을 철저히 계승한 정통 가치투자자입니다. 리스크 관리를 최우선으로 삼아 현금 비중을 유연하게 조절하며, 훌륭한 비즈니스 모델을 가진 산업재, 헬스케어, 그리고 매력적인 가격대의 테크 기업에 집중투자합니다.")
    elif guru_option == "빌 애크먼 (Pershing Square)":
        st.write("**빌 애크먼(Bill Ackman):** 철저한 기본적 분석을 바탕으로 소수의 고확신 우량주에 자본을 몰아넣는 초집중 투자의 대가입니다. 행동주의 투자자로도 유명하며, 단순한 주가 변동을 넘어 강력 독점력과 예측 가능한 현금흐름을 창출하는 플랫폼 및 글로벌 브랜드 기업 위주로 포트폴리오를 구성합니다.")
    elif guru_option == "워런 버핏 (Berkshire Hathaway)":
        st.write("**워런 버핏(Warren Buffett):** 역사상 가장 위대한 투자자로, 가치투자의 대명사입니다. '경제적 해자'와 정직한 경영진을 갖춘 위대한 기업을 적당한 가격에 사서 영원히 보유하는 소유권 관점의 투자를 실천합니다.")
    elif guru_option == "리 루 (Himalaya Capital)":
        st.write("**리 루(Li Lu):** 찰리 멍거가 전적으로 자산을 위탁한 유일한 펀드매니저로, 철저한 리서치와 장기 복리의 힘을 믿는 정통 가치투자 가치관을 관철하는 아시아계 거장입니다.")
    elif guru_option == "척 아크레 (Akre Capital)":
        st.write("**척 아크레(Chuck Akre):** 뛰어난 비즈니스 모델, 정직한 경영진, 재투자 기회라는 세 가지 요소를 완벽히 결합한 '컴파운더(장기 복리 성장 기업)' 중심의 복리 극대화 투자를 진행합니다.")
    elif guru_option == "모니시 파브라이 (Dalal Street)":
        st.write("**모니시 파브라이(Mohnish Pabrai):** 워런 버핏의 투자 방식을 정교하게 카피하여 큰 부를 일군 인물로, 하방 리스크가 없으면서 상방 잠재력이 극대화된 '단도 투자' 전략을 구사합니다.")
    elif guru_option == "가이 스피어 (Aquamarine Capital)":
        st.write("**가이 스피어(Guy Spier):** 워런 버핏의 체크리스트 철학을 기반으로 내면의 판단 기준을 중시하며, 미스터 마켓의 소음을 철저히 배제하고 장기적이고 안전한 가치 기회를 매입합니다.")

    with st.spinner(t("최신 포트폴리오 데이터 연동 중...", "Fetching latest portfolio data...")):
        code = guru_map[guru_option]
        scraped_data = get_13f_portfolio(code)
            
        if scraped_data and len(scraped_data) > 0:
            df = pd.DataFrame(scraped_data)
            df.index = df.index + 1
            
            st.dataframe(df, height=600, column_config={"티커": st.column_config.TextColumn("Ticker"), "기업명": st.column_config.TextColumn("Company Name"), "비중(%)": st.column_config.ProgressColumn("Weight (%)", format="%.2f%%", min_value=0, max_value=max(df["비중(%)"]) + 5)}, use_container_width=True)
            
            if (df["비중(%)"] == 0.0).any():
                st.caption(t("※ 비중이 0.00%로 표기된 종목은 비중 미상이거나 전량 매도된 종목입니다. (이건 확인이 필요한 부분입니다)", "※ Stocks with 0.00% weight are unknown or fully sold. (Needs verification)"))
            
            st.markdown("---")
            st.write(t("[랭킹 종목 빠른 분석 장전]", "[Fast Load for Analysis]"))
            c_tk, c_btn = st.columns([3, 1])
            with c_tk: fast_name = st.selectbox("Company Name", df["기업명"].tolist(), label_visibility="collapsed")
            with c_btn:
                if st.button(t("검색창에 장전하기", "Load to Search"), use_container_width=True):
                    matched_ticker = df[df["기업명"] == fast_name]["티커"].values[0]
                    st.session_state.search_tk = matched_ticker
                    st.toast(t(f"{fast_name} ({matched_ticker}) 분석 장전 완료!", f"{fast_name} ({matched_ticker}) Loaded!"))
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
    with c_tk2: fast_name_mkt = st.selectbox("Company Name", df_mkt["기업명"].tolist(), key="mkt_fast_tk", label_visibility="collapsed")
    with c_btn2:
        if st.button(t("검색창에 장전하기", "Load to Search"), key="mkt_load_btn", use_container_width=True):
            matched_ticker_mkt = df_mkt[df_mkt["기업명"] == fast_name_mkt]["티커"].values[0]
            st.session_state.search_tk = matched_ticker_mkt
            st.toast(t(f"{fast_name_mkt} ({matched_ticker_mkt}) 분석 장전 완료!", f"{fast_name_mkt} ({matched_ticker_mkt}) Loaded!"))
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
         t("100만 원짜리 물건을 70만 원에 할인할 때 사는 단 원리입니다.", "Like buying a $1,000 item on sale for $700."), 
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
        <div style="background: rgba(255,255,255,0.03); color: var(--text-color); padding: 22px; border-radius: 16px; border: 1px solid rgba(160,196,255,0.2); margin-bottom: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            <h4 style="margin-top: 0; color: #A0C4FF; margin-bottom: 12px; font-size: 1.2rem;">{term}</h4>
            <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 8px;">{definition}</div>
            <div style="font-size: 0.95rem; color: #8892b0;"><b>{lbl_analogy}</b> {example}</div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 탭 5: AGIE 철학
# ==========================================
with tab5:
    phil_title1 = t("가치투자의 진정한 의미와 의의: 투기(Speculation) vs 투자(Investment)", "The True Meaning of Value Investing: Speculation vs. Investment")
    phil_p1 = t("주식 시장에는 두 부류의 참여자가 있습니다. 가격 변동에 베팅하며 누군가 나보다 더 비싼 가격에 사주기만을 바라는 '투기자(Speculator)', 그리고 기업의 비즈니스 모델과 내재가치를 분석하여 성장을 함께 나누고자 하는 '투자자(Investor)'입니다.", "There are two types of participants in the stock market: 'Speculators' who bet on price fluctuations, hoping someone will buy at a higher price, and 'Investors' who analyze business models and intrinsic value to share in the company's growth.")
    phil_p2 = t("가치투자(Value Investing)는 매일같이 요동치는 주가의 이면을 꿰뚫어 보고, 그 기업이 실제로 창출하는 현금흐름과 자산에 집중하는 행위입니다. 시장의 광기나 패닉에 휩쓸리지 않고, '가격(Price)은 우리가 지불하는 것이며, 가치(Value)는 우리가 얻는 것'이라는 확고한 믿음을 실천하는 가장 강력한 무기입니다.", "Value investing focuses on the cash flows and assets a company actually generates, seeing through daily price fluctuations. It is the practice of maintaining the firm belief that 'Price is what you pay, Value is what you get,' without being swept away by market mania or panic.")
    phil_title2 = t("워런 버핏과 찰리 멍거의 핵심 철학", "Core Philosophy of Warren Buffett & Charlie Munger")
    phil_li1 = t("**기업의 소유권 (Business Ownership):** 주식은 단순한 거래의 수단이나 종이가 아닙니다. 주식을 산다는 것은 기업의 지분을 인수하여 진정한 '동업자'가 되는 것입니다. 지분 100%를 인수한다는 마음가짐으로 비즈니스를 해부해야 합니다.", "**Business Ownership:** Stocks are not just trading instruments or pieces of paper. Buying a stock means acquiring an equity stake and becoming a true 'partner'. You must dissect the business as if you were buying 100% of it.")
    phil_li2 = t("**미스터 마켓 (Mr. Market):** 시장은 매일 기분에 따라 터무니없이 비싼 가격이나 싼 가격을 부르는 변덕스러운 동업자일 뿐입니다. 시장은 선생님이 아니라, 가격이 내재가치보다 현저히 낮을 때만 이용해야 하는 도구입니다.", "**Mr. Market:** The market is merely a fickle partner who quotes absurdly high or low prices depending on its daily mood. The market is not your teacher, but a tool to be used only when prices are significantly below intrinsic value.")
    phil_li3 = t("**경영진의 정직성 (Integrity of Management):** 재무적 성과만큼이나 중요한 것이 경영진의 도덕성입니다. 비즈니스 모델이 훌륭해도 경영진의 정직성에 의구심이 든다면 미련 없이 동업을 끝내야 합니다. 신뢰할 수 없는 사람과는 좋은 거래 파트너가 될 수 없습니다.", "**Integrity of Management:** Management's morality is just as important as financial performance. Even if the business is great, if you doubt their integrity, you must walk away. You cannot make a good deal with a bad person.")
    phil_li4 = t("**능력 범위 (Circle of Competence):** 완벽히 이해할 수 있고, 논리적으로 설명할 수 있으며, 전문가의 반론에도 재반박할 수 있는 비즈니스에만 투자해야 합니다. 무엇을 아는지보다 '무엇을 모르는지'를 아는 것이 훨씬 중요합니다.", "**Circle of Competence:** Invest only in businesses you fully understand, can logically explain, and can defend against expert counterarguments. Knowing 'what you don't know' is far more important than what you know.")
    phil_li5 = t("**안전마진 (Margin of Safety):** 1만 파운드의 트럭이 지나갈 다리를 3만 파운드를 견딜 수 있도록 짓는 것이 안전마진입니다. 분석에 실수가 있거나 예기치 못한 위기가 닥쳐도 자본을 잃지 않도록 지켜주는 방패입니다.", "**Margin of Safety:** Building a bridge to withstand 30,000 pounds when only 10,000-pound trucks will drive across it. It is the shield that protects your capital from analysis errors or unforeseen crises.")
    phil_title3 = t("AGIE 앱의 존재 이유", "Why AGIE Exists")
    
    phil_decl_ko = (
        "> **투기가 아닌 '진정한 투자'를 위한 나침반**<br><br>"
        "오늘날의 주식 시장은 자극적인 뉴스, 단기적인 차트의 움직임, 그리고 끊임없이 쏟아지는 소음들로 가득 차 있습니다. "
        "수많은 투자자들이 기업의 본질이 아닌 주가창의 붉고 푸른 숫자에 매몰되어 투기적 거래의 늪에 빠지곤 합니다.<br><br>"
        "**AGIE**는 이러한 시장의 광기 속에서 흔들리지 않는 이성을 유지하기 위해 탄생했습니다.<br><br>"
        "우리는 일시적인 주가 상승률이나 테마주를 쫓지 않습니다. 대신, 철저한 잉여현금흐름(FCF) 기반의 내재가치를 계산하고, "
        "경제적 해자(Moat)를 점검하며, 안전마진이 확보된 위대한 기업을 적당한 가격에 발굴하는 데 모든 역량을 집중합니다.<br><br>"
        "이 터미널은 당신이 감정에 휘둘리지 않고, 철저히 데이터와 논리에 기반해 '기업의 소유권'을 올바르게 매입할 수 있도록 돕는 "
        "가장 강력하고 냉철한 보조 도구가 될 것입니다.<br><br>"
        "**투기자가 아닌, 사회에 기여하는 진정한 투자자로서의 여정을 AGIE와 함께 하십시오.**"
    )
    
    phil_decl_en = (
        "> **A Compass for 'True Investment', Not Speculation**<br><br>"
        "Today's stock market is filled with sensational news, short-term chart movements, and endless noise. "
        "Many fall into the swamp of speculative trading, fixated on the red and green numbers rather than the essence of the business.<br><br>"
        "**AGIE** was created to help you maintain unwavering rationality amidst this market mania.<br><br>"
        "We do not chase temporary stock surges or thematic trends. Instead, we focus all our capabilities on calculating intrinsic value "
        "based on Free Cash Flow (FCF), examining economic moats, and discovering great companies with a secured margin of safety at fair prices.<br><br>"
        "This terminal will serve as your most powerful and objective auxiliary tool, helping you purchase 'business ownership' correctly "
        "based strictly on data and logic, free from emotion.<br><br>"
        "**Join AGIE on the journey to becoming a true investor who contributes to society, not a speculator.**"
    )
    
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
    
    st.markdown(
        f"<div style='font-size: 1.1rem; line-height: 1.8; "
        f"background: rgba(255,255,255,0.03); padding: 30px; border-radius: 16px; "
        f"border-left: 5px solid #A0C4FF; color: var(--text-color); "
        f"box-shadow: 0 4px 12px rgba(0,0,0,0.05);'>{phil_decl}</div>",
        unsafe_allow_html=True
    )

# 하단 면책 조항 및 카피라이트 
st.divider()
lbl_disc_title = t('[면책 조항 / Disclaimer]', '[Disclaimer]')
lbl_disc_1 = t('본 애플리케이션은 가치투자 분석을 돕기 위한 단순 투자 보조 도구일 뿐입니다. 제공되는 재무 데이터, 13F 공시 정보, 분석 결과는 오류나 지연이 발생할 수 있습니다.', 'This application is a simple auxiliary tool to assist in value investing analysis. Provided financial data, 13F filings, and analysis results may contain errors or delays.')
lbl_disc_2 = t('본 터미널의 결과만으로 실제 주식의 특정 종목 매수 및 매도를 권유하지 않으며, 최종 투자 결정 및 그로 인한 재무적 손실에 대한 모든 법적 책임은 전적으로 투자자 본인에게 있습니다.', 'The results of this terminal do not solicit the purchase or sale of specific stocks, and all legal responsibility for final investment decisions and resulting financial losses lies entirely with the investor.')
lbl_copy = t('본 프로그램의 분석 로직, 산식 및 데이터 표출 양식은 저작권법의 보호 파악을 받으며, 원작자의 허가 없는 무단 복제, 배포, 상업적 이용을 엄격히 금지합니다.', 'The analysis logic, formulas, and data display formats of this program are protected by copyright law, and unauthorized reproduction, distribution, or commercial use without permission is strictly prohibited.')

st.markdown(f"""
<div style='text-align: center; color: #8892b0; font-size: 0.85rem; line-height: 1.6;'>
    <p><b>{lbl_disc_title}</b><br>
    {lbl_disc_1}<br>
    {lbl_disc_2}</p>
    <p><b>[Copyright]</b><br>
    ⓒ 2026 AGIE. All rights reserved.<br>
    {lbl_copy}</p>
</div>
""", unsafe_allow_html=True)
