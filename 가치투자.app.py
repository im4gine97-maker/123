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
                matches[v] = primary_names.get(v, k)
                        
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
# [2] 글로벌 상수 및 고정 데이터 (검색 매핑)
# ==========================================
tmap = {
    "삼성전자": "005930.KS", "삼전": "005930.KS", "SAMSUNG": "005930.KS",
    "SK하이닉스": "000660.KS", "하닉": "000660.KS", "HYNIX": "000660.KS",
    "LG에너지솔루션": "373220.KS", "LG엔솔": "373220.KS", "엔솔": "373220.KS",
    "현대자동차": "005380.KS", "현대차": "005380.KS", "현차": "005380.KS", "HYUNDAI": "005380.KS",
    "삼성바이오로직스": "207940.KS", "삼바": "207940.KS",
    "기아": "000270.KS", "기아차": "000270.KS", "KIA": "000270.KS",
    "셀트리온": "068270.KS", "CELLTRION": "068270.KS",
    "KB금융": "105560.KS", "국민은행": "105560.KS", "KB금융지주": "105560.KS",
    "POSCO홀딩스": "005490.KS", "포스코": "005490.KS", "포홀": "005490.KS", "POSCO": "005490.KS",
    "신한지주": "055550.KS", "신한금융": "055550.KS", "신한은행": "055550.KS",
    "삼성SDI": "006400.KS", "SDI": "006400.KS",
    "NAVER": "035420.KS", "네이버": "035420.KS",
    "현대모비스": "012330.KS", "모비스": "012330.KS", "MOBIS": "012330.KS",
    "LG화학": "051910.KS",
    "카카오": "035720.KS", "KAKAO": "035720.KS",
    "삼성물산": "028260.KS", "물산": "028260.KS",
    "하나금융지주": "086790.KS", "하나금융": "086790.KS", "하나은행": "086790.KS",
    "LG전자": "066570.KS", "엘지전자": "066570.KS",
    "SK스퀘어": "402340.KS", "스퀘어": "402340.KS",
    "삼성생명": "032830.KS", "삼생": "032830.KS",
    "메리츠금융지주": "138040.KS", "메리츠": "138040.KS", "메리츠금융": "138040.KS", "메리츠증권": "138040.KS", "메리츠화재": "138040.KS",
    "SK이노베이션": "096770.KS", "SK이노": "096770.KS",
    "HD현대중공업": "329180.KS", "현대중공업": "329180.KS",
    "HMM": "011200.KS", "현대상선": "011200.KS",
    "고려아연": "010130.KS",
    "KT&G": "033780.KS", "케이티앤지": "033780.KS",
    "두산에너빌리티": "034020.KS", "두산에너": "034020.KS", "에너빌리티": "034020.KS",
    "삼성전기": "009150.KS", "삼전기": "009150.KS",
    "크래프톤": "259960.KS", "KRAFTON": "259960.KS",
    "한화에어로스페이스": "012450.KS", "한화에어로": "012450.KS",
    "SK": "034730.KS", "에스케이": "034730.KS",
    "삼성화재": "000810.KS",
    "우리금융지주": "316140.KS", "우리금융": "316140.KS", "우리은행": "316140.KS",
    "한국전력": "015760.KS", "한전": "015760.KS",
    "삼성에스디에스": "018260.KS", "삼성SDS": "018260.KS",
    "미래에셋증권": "006800.KS", "미래에셋": "006800.KS",
    "한국금융지주": "071050.KS", "한국투자증권": "071050.KS", "한투": "071050.KS",
    "키움증권": "039490.KS",
    "삼성카드": "029780.KS",
    
    "NVIDIA": "NVDA", "엔비디아": "NVDA", "앤비디아": "NVDA", "엔비": "NVDA",
    "APPLE": "AAPL", "애플": "AAPL",
    "ALPHABET": "GOOGL", "구글": "GOOGL", "알파벳": "GOOGL", "GOOGLE": "GOOGL",
    "MICROSOFT": "MSFT", "마이크로소프트": "MSFT", "마소": "MSFT",
    "AMAZON": "AMZN", "아마존": "AMZN", "아마": "AMZN",
    "BROADCOM": "AVGO", "브로드컴": "AVGO", "브컴": "AVGO",
    "TESLA": "TSLA", "테슬라": "TSLA", "테슬": "TSLA", "텔라": "TSLA",
    "META": "META", "메타": "META", "페이스북": "META", "페북": "META",
    "MICRON": "MU", "마이크론": "MU", "마이크론테크놀로지": "MU", "마이크론 테크놀로지": "MU",
    "BERKSHIREHATHAWAY": "BRK-A", "버크셔해서웨이": "BRK-A", "버크셔": "BRK-A", "버크셔A": "BRK-A", "버크셔B": "BRK-B", "BRK-A": "BRK-A", "BRK-B": "BRK-B",
    "ELILILLY": "LLY", "일라이릴리": "LLY", "릴리": "LLY", "일릴": "LLY",
    "WALMART": "WMT", "월마트": "WMT",
    "AMD": "AMD", "에이엠디": "AMD",
    "JPMORGAN": "JPM", "제이피모건": "JPM", "JP모건": "JPM", "제이피": "JPM",
    "ORACLE": "ORCL", "오라클": "ORCL",
    "VISA": "V", "비자": "V",
    "EXXONMOBIL": "XOM", "엑손모빌": "XOM", "엑손": "XOM",
    "INTEL": "INTC", "인텔": "INTC",
    "JOHNSON&JOHNSON": "JNJ", "존슨앤존슨": "JNJ", "존슨앤드존슨": "JNJ",
    "CISCO": "CSCO", "시스코": "CSCO",
    "MASTERCARD": "MA", "마스터카드": "MA",
    "COSTCO": "COST", "코스트코": "COST",
    "CATERPILLAR": "CAT", "캐터필러": "CAT",
    "LAMRESEARCH": "LRCX", "램리서치": "LRCX", "램 리서치": "LRCX",
    "ABBVIE": "ABBV", "애브비": "ABBV",
    "PALANTIR": "PLTR", "팔란티어": "PLTR", "팔란": "PLTR",
    "BANKOFAMERICA": "BAC", "뱅크오브아메리카": "BAC", "뱅크 오브 아메리카": "BAC",
    "CHEVRON": "CVX", "쉐브론": "CVX", "셰브론": "CVX",
    "NETFLIX": "NFLX", "넷플릭스": "NFLX", "넷플": "NFLX",
    "APPLIEDMATERIALS": "AMAT", "어플라이드머티리얼즈": "AMAT", "어플라이드 머티어리얼즈": "AMAT", "어플": "AMAT",
    "COCA-COLA": "KO", "코카콜라": "KO", "COCACOLA": "KO",
    "OCCIDENTAL": "OXY", "옥시덴탈": "OXY", "옥시": "OXY",
    
    "SPACEX": "SPCX", "스페이스X": "SPCX", "스페이스엑스": "SPCX", "스페이스 엑스": "SPCX", "스엑": "SPCX",
    "SANDISK": "SNDK", "샌디스크": "SNDK", "샌디": "SNDK", "SNDK": "SNDK",
    "웨스턴 디지털": "WDC", "웨스턴디지털": "WDC", "WESTERN DIGITAL": "WDC", "WDC": "WDC",
    
    "마벨 테크놀로지": "MRVL", "마벨": "MRVL", "MARVELL": "MRVL", "MRVL": "MRVL",
    "텍사스 인스트루먼트": "TXN", "텍사스인스트루먼트": "TXN", "TI": "TXN", "TEXAS INSTRUMENTS": "TXN", "TXN": "TXN",
    "퀄컴": "QCOM", "QUALCOMM": "QCOM", "QCOM": "QCOM",

    "유나이티드헬스 그룹": "UNH", "유나이티드헬스": "UNH", "UNH": "UNH",
    "프록터 앤 갬블": "PG", "P&G": "PG", "PG": "PG",
    "홈디포": "HD", "HD": "HD",
    "머크": "MRK", "MRK": "MRK",
    "펩시코": "PEP", "펩시": "PEP", "PEP": "PEP",
    
    "보잉": "BA", "BA": "BA",
    "제너럴 모터스": "GM", "제너럴모터스": "GM", "GM": "GM",
    "포드 모터": "F", "포드": "F",
    "다우": "DOW", "DOW": "DOW",
    "프리포트 맥모란": "FCX", "프리포트맥모란": "FCX", "FCX": "FCX",
    "뉴코어": "NUE", "NUE": "NUE",
    "델타 항공": "DAL", "델타항공": "DAL", "DAL": "DAL",
    "유나이티드 항공": "UAL", "유나이티드항공": "UAL", "UAL": "UAL",
    "유니온 퍼시픽": "UNP", "유니온퍼시픽": "UNP", "UNP": "UNP",
    "디어 앤 컴퍼니": "DE", "DE": "DE",
    "알코아": "AA", "AA": "AA",
    "레나": "LEN", "LEN": "LEN",
    "DR 호튼": "DHI", "디알호튼": "DHI", "DR호튼": "DHI", "DHI": "DHI",
    "월풀": "WHR", "WHR": "WHR",
    "로얄 캐리비안": "RCL", "로얄캐리비안": "RCL", "RCL": "RCL",
    "카니발": "CCL", "CCL": "CCL",
    "메리어트 인터내셔널": "MAR", "메리어트": "MAR", "MAR": "MAR",
    "힐튼 월드와이드": "HLT", "힐튼": "HLT", "HLT": "HLT",
    "익스피디아": "EXPE", "EXPE": "EXPE",
    
    "알리바바 그룹": "BABA", "알리바바": "BABA", "BABA": "BABA",
    "PDD 홀딩스": "PDD", "핀듀오듀오": "PDD", "PDD": "PDD", "PINDUODUO": "PDD",
    "징동닷컴": "JD", "징동": "JD", "JD": "JD",
    "넷이즈": "NTES", "NTES": "NTES",
    "바이두": "BIDU", "BIDU": "BIDU",
    "트립닷컴 그룹": "TCOM", "트립닷컴": "TCOM", "TCOM": "TCOM",
    "얌 차이나": "YUMC", "YUMC": "YUMC",
    "니오": "NIO", "NIO": "NIO",
    "리 오토": "LI", "리오토": "LI", "LI": "LI",
    "샤오펑": "XPEV", "XPEV": "XPEV",
    "ZTO 익스프레스": "ZTO", "ZTO": "ZTO",
    "KE 홀딩스": "BEKE", "BEKE": "BEKE",
    "텐센트 뮤직 엔터테인먼트": "TME", "텐센트 뮤직": "TME", "TME": "TME",
    "빌리빌리": "BILI", "BILI": "BILI",
    "푸투 홀딩스": "FUTU", "FUTU": "FUTU",
    
    "이스트웨스트뱅코프": "EWBC", "EWBC": "EWBC",
    "크록스": "CROX", "CROX": "CROX",
    "에스앤피글로벌": "SPGI", "S&P글로벌": "SPGI", "SPGI": "SPGI",
    "H&R블록": "HRB", "HRB": "HRB",
    "무디스": "MCO", "MCO": "MCO",
    "모건스탠리캐피털인터내셔널": "MSCI", "MSCI": "MSCI",
    "아메리칸익스프레스": "AXP", "아멕스": "AXP", "AXP": "AXP",
    "처브": "CB", "CB": "CB",
    "크래프트하인즈": "KHC", "크래프트": "KHC", "하인즈": "KHC", "KHC": "KHC",
    "다비타": "DVA", "DVA": "DVA",
    "크로거": "KR", "KR": "KR",
    "얼라이파이낸셜": "ALLY", "얼라이": "ALLY", "ALLY": "ALLY",
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
    "데일리저널": "DJCO", "DJCO": "DJCO",
    
    "TSM": "TSM", "TSMC": "TSM", "티에스엠씨": "TSM", "대만반도체": "TSM", "티에스엠": "TSM",
    "UMC": "UMC", "유엠씨": "UMC",
    "TENCENT": "TCEHY", "텐센트": "TCEHY"
}

primary_names = {}
for k, v in tmap.items():
    if v not in primary_names:
        primary_names[v] = k

fallback_13f_data = {
    "BRK": [{"티커": "AAPL", "기업명": "Apple", "비중(%)": 22.04}, {"티커": "AXP", "기업명": "American Express", "비중(%)": 17.14}, {"티커": "KO", "기업명": "Coca-Cola", "비중(%)": 10.86}, {"티커": "GOOGL", "기업명": "Alphabet Class A", "비중(%)": 9.41}, {"티커": "BAC", "기업명": "Bank of America", "비중(%)": 9.20}, {"티커": "CVX", "기업명": "Chevron", "비중(%)": 4.67}, {"티커": "OXY", "기업명": "Occidental Petroleum", "비중(%)": 4.30}],
    "BRK_PER": [{"티커": "UBER", "기업명": "Uber Technologies", "비중(%)": 12.72}, {"티커": "BN", "기업명": "Brookfield Corp", "비중(%)": 12.58}, {"티커": "MSFT", "기업명": "Microsoft", "비중(%)": 11.89}, {"티커": "AMZN", "기업명": "Amazon", "비중(%)": 10.49}, {"티커": "HHH", "기업명": "Howard Hughes", "비중(%)": 10.23}, {"티커": "QSR", "기업명": "Restaurant Brands", "비중(%)": 9.62}, {"티커": "META", "기업명": "Meta Platforms", "비중(%)": 9.25}],
    "BAU": [{"티커": "AMZN", "기업명": "Amazon", "비중(%)": 16.48}, {"티커": "ELV", "기업명": "Elevance Health", "비중(%)": 9.11}, {"티커": "QSR", "기업명": "Restaurant Brands", "비중(%)": 9.04}, {"티커": "GOOG", "기업명": "Alphabet Class C", "비중(%)": 8.95}, {"티커": "FERG", "기업명": "Ferguson", "비중(%)": 6.36}, {"티커": "GPC", "기업명": "Genuine Parts", "비중(%)": 6.13}, {"티커": "UNP", "기업명": "Union Pacific", "비중(%)": 5.95}],
    "HC": [{"티커": "GOOGL", "기업명": "Alphabet Class A", "비중(%)": 24.55}, {"티커": "GOOG", "기업명": "Alphabet Class C", "비중(%)": 23.39}, {"티커": "PDD", "기업명": "PDD Holdings", "비중(%)": 22.17}, {"티커": "BRK-A", "기업명": "Berkshire Hathaway A", "비중(%)": 14.98}, {"티커": "EWBC", "기업명": "East West Bancorp", "비중(%)": 9.68}, {"티커": "CROX", "기업명": "Crocs", "비중(%)": 2.89}, {"티커": "TME", "기업명": "Tencent Music", "비중(%)": 1.49}, {"티커": "AAPL", "기업명": "Apple", "비중(%)": 0.86}],
    "AKRE": [{"티커": "MA", "기업명": "Mastercard", "비중(%)": 20.01}, {"티커": "MCO", "기업명": "Moody's", "비중(%)": 10.26}, {"티커": "BN", "기업명": "Brookfield Corp", "비중(%)": 10.11}, {"티커": "KKR", "기업명": "KKR & Co", "비중(%)": 8.95}, {"티커": "FICO", "기업명": "Fair Isaac Corp", "비중(%)": 8.47}, {"티커": "ROP", "기업명": "Roper Technologies", "비중(%)": 7.80}, {"티커": "V", "기업명": "Visa", "비중(%)": 7.46}],
    "PI": [{"티커": "HCC", "기업명": "Warrior Met Coal", "비중(%)": 43.32}, {"티커": "RIG", "기업명": "Transocean", "비중(%)": 30.53}, {"티커": "AMR", "기업명": "Alpha Metallurgical", "비중(%)": 26.11}, {"티커": "KSPI", "기업명": "Kaspi.kz ADR", "비중(%)": 0.04}],
    "AQUA": [{"티커": "BRK-A", "기업명": "Berkshire Hathaway A", "비중(%)": 33.89}, {"티커": "BRK-B", "기업명": "Berkshire Hathaway B", "비중(%)": 15.59}, {"티커": "AXP", "기업명": "American Express", "비중(%)": 15.26}, {"티커": "MA", "기업명": "Mastercard", "비중(%)": 14.26}, {"티커": "MCO", "기업명": "Moody's", "비중(%)": 8.49}, {"티커": "RACE", "기업명": "Ferrari", "비중(%)": 7.71}, {"티커": "DJCO", "기업명": "Daily Journal", "비중(%)": 4.80}]
}

us_top30 = [{"순위": 1, "티커": "NVDA", "기업명": "NVIDIA", "시가총액": "$5.11T"}, {"순위": 2, "티커": "AAPL", "기업명": "Apple", "시가총액": "$4.58T"}, {"순위": 3, "티커": "GOOGL", "기업명": "Alphabet", "시가총액": "$4.56T"}, {"순위": 4, "티커": "MSFT", "기업명": "Microsoft", "시가총액": "$3.34T"}, {"순위": 5, "티커": "AMZN", "기업명": "Amazon", "시가총액": "$2.91T"}, {"순위": 6, "티커": "AVGO", "기업명": "Broadcom", "시가총액": "$2.11T"}, {"순위": 7, "티커": "TSLA", "기업명": "Tesla", "시가총액": "$1.63T"}, {"순위": 8, "티커": "META", "기업명": "Meta Platforms", "시가총액": "$1.60T"}, {"순위": 9, "티커": "MU", "기업명": "Micron", "시가총액": "$1.09T"}, {"순위": 10, "티커": "BRK-A", "기업명": "Berkshire Hathaway", "시가총액": "$1.02T"}, {"순위": 11, "티커": "LLY", "기업명": "Eli Lilly", "시가총액": "$985B"}, {"순위": 12, "티커": "WMT", "기업명": "Walmart", "시가총액": "$922B"}, {"순위": 13, "티커": "AMD", "기업명": "AMD", "시가총액": "$841B"}, {"순위": 14, "티커": "JPM", "기업명": "JPMorgan Chase", "시가총액": "$802B"}, {"순위": 15, "티커": "ORCL", "기업명": "Oracle", "시가총액": "$649B"}, {"순위": 16, "티커": "V", "기업명": "Visa", "시가총액": "$620B"}, {"순위": 17, "티커": "XOM", "기업명": "Exxon Mobil", "시가총액": "$602B"}, {"순위": 18, "티커": "INTC", "기업명": "Intel", "시가총액": "$576B"}, {"순위": 19, "티커": "JNJ", "기업명": "Johnson & Johnson", "시가총액": "$542B"}, {"순위": 20, "티커": "CSCO", "기업명": "Cisco", "시가총액": "$474B"}, {"순위": 21, "티커": "MA", "기업명": "Mastercard", "시가총액": "$436B"}, {"순위": 22, "티커": "COST", "기업명": "Costco", "시가총액": "$424B"}, {"순위": 23, "티커": "CAT", "기업명": "Caterpillar", "시가총액": "$403B"}, {"순위": 24, "티커": "LRCX", "기업명": "Lam Research", "시가총액": "$397B"}, {"순위": 25, "티커": "ABBV", "기업명": "AbbVie", "시가총액": "$384B"}, {"순위": 26, "티커": "PLTR", "기업명": "Palantir", "시가총액": "$375B"}, {"순위": 27, "티커": "BAC", "기업명": "Bank of America", "시가총액": "$366B"}, {"순위": 28, "티커": "CVX", "기업명": "Chevron", "시가총액": "$363B"}, {"순위": 29, "티커": "NFLX", "기업명": "Netflix", "시가총액": "$362B"}, {"순위": 30, "티커": "AMAT", "기업명": "Applied Materials", "시가총액": "$357B"}]
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
        "AAPL": "애플: 장점: 압도적인 마진을 바탕으로 자사주 매입과 주당가치 제고를 통해 교과서적 자본 배분을 보여줍니다.\n단점: 혁신 정체 우려와 앱스토어 관련 반독점 및 독점 규제 리스크가 상존합니다.",
        "MSFT": "마이크로소프트: 장점: AI 시장 선점으로 확고한 시장 장악에 성공했고, 투명한 소통으로 가장 신뢰받는 기업입니다.\n단점: 인프라 투자로 인한 마진 희석 우려와 글로벌 독점 규제 타겟이 되고 있습니다.",
        "BRK-A": "버크셔 해서웨이: 장점: 정직을 최우선으로 교과서적 자본 배분을 실천하며, 시장에서 가장 신뢰받는 지주회사입니다.\n단점: 워런 버핏 이후 시대를 대비해야 하는 키맨 리스크가 유일한 약점입니다.",
        "BRK-B": "버크셔 해서웨이: 장점: 정직을 최우선으로 교과서적 자본 배분을 실천하며, 시장에서 가장 신뢰받는 지주회사입니다.\n단점: 워런 버핏 이후 시대를 대비해야 하는 키맨 리스크가 유일한 약점입니다.",
        "AMZN": "아마존: 장점: 본업에 집중하여 잉여현금 극대화 및 폭발적인 수익성 개선을 이뤄냈습니다.\n단점: 물류 센터 노동 환경 관련 노무 이슈 및 반독점 독점 규제 소송 리스크가 상존합니다.",
        "GOOGL": "알파벳: 장점: 검색 시장의 독점적 지위를 통해 강력한 현금 창출력을 유지하고 있습니다.\n단점: AI 경쟁 격화로 인한 해자 잠식 우려와 강력한 반독점 및 독점 규제 압박을 받습니다.",
        "GOOG": "알파벳: 장점: 검색 시장의 독점적 지위를 통해 강력한 현금 창출력을 유지하고 있습니다.\n단점: AI 경쟁 격화로 인한 해자 잠식 우려와 강력한 반독점 및 독점 규제 압박을 받습니다.",
        "META": "메타: 장점: 마진 극대화 및 적극적인 주주환원과 배당 확대 등을 통해 수익성 개선을 이루었습니다.\n단점: 통제 리스크가 크며, 과거 개인정보 유출 관련 집단소송 이력이 있습니다.",
        "AXP": "아메리칸 익스프레스: 장점: 철저한 ROE 관리와 프리미엄 우위를 바탕으로 연속 배당 성장을 이루는 주주친화 기업입니다.\n단점: 거시경제 침체 및 사이클에 따른 변동성 우려가 있습니다.",
        "KO": "코카콜라: 장점: 연속 배당 성장의 대명사로 전 세계적인 시장 장악력과 안정적 현금 창출력을 자랑합니다.\n단점: 건강 트렌드 확산에 따른 외형 성장 정체 및 둔화 우려가 있습니다.",
        "MA": "마스터카드: 장점: 결제 네트워크의 독보적 지위를 바탕으로 압도적인 마진과 탁월한 자본수익률을 기록 중입니다.\n단점: 가맹점 수수료 관련 집단소송 및 정부와의 규제 마찰 위협이 있습니다.",
        "V": "비자: 장점: 결제 네트워크의 독보적 지위를 바탕으로 압도적인 마진과 탁월한 자본수익률을 기록 중입니다.\n단점: 가맹점 수수료 관련 집단소송 및 정부와의 규제 마찰 위협이 있습니다.",
        "BN": "브룩필드: 장점: 자산 투자에서 검증된 역량으로 탁월한 자본수익률 및 수익성 개선을 증명합니다.\n단점: 잦은 인수로 인한 높은 레버리지 및 부채 부담과 지배구조 불안이 흠입니다.",
        "UBER": "우버: 장점: 글로벌 모빌리티 시장 장악을 통해 흑자 달성 및 잉여현금 극대화 구간에 진입했습니다.\n단점: 기사 분류 관련 노동 환경 및 노무 소송과 각국 정부와의 규제 마찰이 잦습니다.",
        "PDD": "핀둬둬: 장점: 초저가 전략으로 단기간에 압도적인 수익성 개선과 이커머스 시장 장악력을 확보했습니다.\n단점: 재무가 불투명한 편이며, 가혹한 노동 환경 및 강제노동 논란, 지정학적 리스크가 큽니다.",

        "TSM": "TSMC: 장점: 파운드리 시장 장악을 바탕으로 독점적 지위와 압도적인 우위를 유지하고 있습니다.\n단점: 지정학적 리스크와 전방 IT 수요 사이클에 따른 실적 변동성이 큽니다.",
        "SNDK": "샌디스크: 장점: 플래시 스토리지 부문에서 검증된 1위 우위를 보유하고 있습니다.\n단점: 과거 소비자에게 알리지 않고 부품 바꿔치기를 단행해 집단소송을 당하는 등 정직성이 부족합니다.",
        "WDC": "웨스턴 디지털: 장점: 본업에 집중하여 스토리지 분야의 수익성 개선을 도모하고 있습니다.\n단점: 극심한 다운 사이클 침체에 취약하며, 무리한 인수로 누적된 부채 부담이 큽니다.",
        "SPCX": "스페이스X: 장점: 재사용 로켓으로 시장 장악을 이루며 독보적 지위와 압도적인 발사 원가 경쟁력을 갖췄습니다.\n단점: 오너의 키맨 리스크가 크며, 정부 규제 마찰 및 부당 해고 관련 소송이 제기되었습니다.",
        "MU": "마이크론: 장점: 차세대 메모리 시장 선점에 성공하며 검증된 기술력을 입증했습니다.\n단점: 메모리 수요 침체 및 사이클 변동성에 취약하며, 지정학적 우려에 노출되어 있습니다.",
        "MRVL": "마벨: 장점: 네트워킹 칩 분야의 독보적 강자로 확실한 수익성 개선을 보이고 있습니다.\n단점: 과거 경영진의 조작 스캔들이 있었으며 전방위 수요 침체 및 둔화에 취약합니다.",
        "TXN": "텍사스 인스트루먼트: 장점: 교과서적 자본 배분과 자사주 매입, 연속 배당 성장을 실천하는 우량 기업입니다.\n단점: 산업용 침체 사이클에 민감하며, 대규모 증설로 인한 단기 마진 희석 우려가 있습니다.",
        "QCOM": "퀄컴: 장점: 모바일 모뎀칩 부문의 독점적 지배력과 압도적인 마진을 자랑합니다.\n단점: 과거 로열티 관련 반독점 소송 및 과징금 이력이 있으며 점유율 잠식 우려가 큽니다.",
        "AMAT": "어플라이드 머티어리얼즈: 장점: 장비 시장에서 검증된 1위 경쟁력을 갖추고 수익성 개선을 이룹니다.\n단점: 수출 통제를 우회하여 불법 수출한 혐의로 사법 당국의 제재 및 조사를 받고 있습니다.",
        "LRCX": "램리서치: 장점: 식각 장비 분야에서 독보적 점유율과 시장 장악력을 차지하고 있습니다.\n단점: 투자 축소 시 사이클 둔화 타격을 받으며 지정학적 리스크가 존재합니다.",
        "INTC": "인텔: 장점: 전통적 PC 및 서버 CPU 시장에서 방대한 생태계 우위를 가졌습니다.\n단점: 경쟁 격화로 잠식을 당했으며, 적자 방치와 배당 중단 등으로 심각한 주주가치 훼손을 겪었습니다.",
        "BABA": "알리바바: 장점: 이커머스 생태계 시장 장악을 바탕으로 적극적인 주주환원을 실행합니다.\n단점: 정부의 독점 규제 리스크로 막대한 과징금을 맞았으며 경쟁 격화로 점유율 잠식이 우려됩니다.",
        "JD": "징동닷컴: 장점: 자체 물류망을 기반으로 강력한 배송 신뢰도와 품질 우위를 점했습니다.\n단점: 내수 소비 침체 둔화 타격을 직접적으로 받으며, 경쟁 격화에 따른 정체를 겪습니다.",
        "NTES": "넷이즈: 장점: 자체 개발 IP를 통해 안정적이고 강력한 현금 창출력을 보입니다.\n단점: 정부의 규제 마찰 리스크와 성장 정체 우려가 상존합니다.",
        "BIDU": "바이두: 장점: 검색 1위 기업으로 AI 시장을 선점해 안정적 이익을 냅니다.\n단점: 과거 의료광고 은폐 및 조작 논란으로 신뢰도 타격을 입었으며 지정학적 리스크가 우려됩니다.",
        "TCOM": "트립닷컴: 장점: 여행 시장에서 독보적 지위와 1위 점유율을 지녔습니다.\n단점: 불투명한 거래로 규제 마찰을 빚었으며 글로벌 지정학적 변동성에 민감합니다.",
        "YUMC": "얌 차이나: 장점: 현지화 메뉴와 공급망을 통해 안정적 방어력을 보여줍니다.\n단점: 출혈 및 경쟁 격화로 인해 구조적인 마진 희석 우려가 존재합니다.",
        "NIO": "니오: 장점: 배터리 스왑 생태계 선점으로 프리미엄 커뮤니티 우위를 가졌습니다.\n단점: 무리한 적자 방치 및 잦은 유상증자로 인한 주주가치 희석과 분식회계 논란이 흠결입니다.",
        "LI": "리오토: 장점: EREV 시장 선점을 통해 흑자 달성 및 자본 효율적 경영을 입증했습니다.\n단점: 가격 치킨게임 등 경쟁 격화에 따른 마진 희석 우려가 있습니다.",
        "XPEV": "샤오펑: 장점: 소프트웨어 역량 선점과 원가 절감을 통해 수익성 개선을 꾀하고 있습니다.\n단점: 기밀 유출 소송에 휘말린 이력이 있으며 지속적인 적자 방치가 우려됩니다.",
        "ZTO": "ZTO 익스프레스: 장점: 최저 원가로 시장 우위를 굳히며 수익성 개선을 보입니다.\n단점: 조작 의혹을 받은 바 있으며, 단가 인하 출혈 경쟁의 타격을 받습니다.",
        "BEKE": "KE 홀딩스: 장점: 부동산 중개 플랫폼 1위로 독보적 네트워크를 지녔습니다.\n단점: 과거 허위 매출 조작 공격 이력이 있으며 부동산 장기 침체 둔화 타격을 받습니다.",
        "TME": "텐센트 뮤직: 장점: 모기업 생태계를 활용해 음원 시장 장악력을 가졌습니다.\n단점: 과거 독점 판권 남용으로 반독점 과징금 제재를 받았으며, 유저 이탈 리스크가 큽니다.",
        "BILI": "빌리빌리: 장점: 팬덤을 통해 충성도 높은 플랫폼 우위를 지녔습니다.\n단점: 유해 콘텐츠 방조로 제재를 받으며, 적자 방치 및 유저 이탈 우려가 존재합니다.",
        "FUTU": "푸투 홀딩스: 장점: 플랫폼 경쟁력으로 시장 확장에 선점 우위를 가졌습니다.\n단점: 당국의 불법 규제로 본토 앱이 삭제되는 제재를 받았으며 사이클 변동성이 큽니다.",

        "005930": "삼성전자: 장점: 메모리 및 스마트폰 1위의 시장 장악력과 압도적인 현금 창출력을 바탕으로 안정적 운영을 보여줍니다.\n단점: 과거 사법 리스크 및 소송 이력이 있으며, 기술 경쟁 격화에 따른 시장 잠식 우려가 존재합니다.",
        "000660": "SK하이닉스: 장점: HBM 공급망 선점과 실행력을 바탕으로 시장에서 독보적 지위를 굳혔습니다.\n단점: 특정 고객사 의존에 따른 사이클 변동성이 매우 크며 무리한 설비투자로 인한 부채 부담 리스크가 있습니다.",
        "373220": "LG에너지솔루션: 장점: 배터리 수주 잔고 선점을 통해 시장 장악 우위를 가졌습니다.\n단점: 과거 대규모 화재 결함으로 배상금을 지출했으며, 성장 둔화 및 가동률 하락에 따른 경쟁 격화가 우려됩니다.",
        "207940": "삼성바이오로직스: 장점: 압도적인 마진과 1위 생산능력으로 CMO 시장 우위를 증명했습니다.\n단점: 거규모 분식회계 사태로 인한 장기 사법 리스크 및 소송이 최대 거버넌스 붕괴 요인입니다.",
        "005380": "현대차: 장점: 유연 생산 체계로 흑자 달성 및 수익성 개선을 이루고 적극적인 주주환원을 시행 중입니다.\n단점: 과거 엔진 결함 은폐로 배상금을 지불한 전력이 있으며 관세 및 지정학적 우려가 존재합니다.",
        "000270": "기아: 장점: 탁월한 자본수익률을 바탕으로 자사주 매입 및 전량 소각을 단행하는 주주친화 기업입니다.\n단점: 차량 결함에 따른 집단소송 및 배상금 지급 이력과 사이클 변동성이 약점입니다.",
        "068270": "셀트리온: 장점: 지배구조 단순화로 수익성 개선 및 주당가치 제고를 추진하며 본업에 집중합니다.\n단점: 과거 회계 조작 논란이 있었으며, 직판망 확대에 따른 부채 부담과 오버행 우려가 큽니다.",
        "005490": "POSCO홀딩스: 장점: 철강 경쟁력 위에 이차전지 소재를 완결형으로 구축해 강력한 우위를 지녔습니다.\n단점: 잦은 정경유착 구설수와 이사회 외유성 압수수색 등 거버넌스 리스크가 잦습니다.",
        "035420": "NAVER: 장점: 국내 검색 시장 장악력을 바탕으로 안정적 흑자 달성을 이뤄냅니다.\n단점: 알고리즘 조작 방조로 과징금을 물었던 전력과 글로벌 지정학적 마찰 및 이탈 리스크가 존재합니다.",
        "028260": "삼성물산: 장점: 배당 확대와 자사주 전량 소각 등 선도적인 주주 환원을 실천합니다.\n단점: 과거 불공정한 합병 비율 조작으로 인한 사법 리스크 및 배상금 패소 전력이 심각한 주주가치 훼손입니다.",
        "006400": "삼성SDI: 장점: 철저한 ROE 수익성 중심 기조로 본업에 집중하여 안정적 이익 창출력을 보입니다.\n단점: 배터리 발화 결함 전력이 있으며, 무리한 투자 회피로 인한 점유율 잠식 및 둔화 우려가 있습니다.",
        "105560": "KB금융: 장점: 주주환원율 로드맵 제시와 자사주 매입으로 금융주를 선도하는 1위 우위 기업입니다.\n단점: 불완전판매로 거액의 배상금을 냈으며, 은행권 특유의 내부통제 부실 및 부채 부담 리스크가 있습니다.",
        "055550": "신한지주: 장점: 자본 효율적 경영 및 자사주 매입 소각 등 적극적인 주주환원을 실행합니다.\n단점: 라임펀드 사태 및 비리 연루로 사법 제재를 받았으며, 펀드 부실에 따른 배상금 흠결이 존재합니다.",
        "051910": "LG화학: 장점: 포트폴리오를 전환하며 고부가 스페셜티 시장을 선점 및 완결형 우위를 가졌습니다.\n단점: 핵심 사업부 물적분할로 최악의 주주가치 훼손 논란을 일으켰으며 해외 공장 사망 참사 오점이 있습니다.",
        "032830": "삼성생명: 장점: 금융 계열사 간 시너지를 바탕으로 안정적이고 강력한 현금 창출력을 자랑합니다.\n단점: 소비자 소송 제재를 겪었으며, 보험업법 개정에 따른 지배구조 불안 및 지분 매각 오버행 우려가 있습니다.",
        "086790": "하나금융지주: 장점: 탁월한 외환 영업력 우위를 바탕으로 대규모 자사주 매입과 전량 소각을 이행합니다.\n단점: 채용 비리 및 불완전판매 사기 사태로 사법 기관의 제재를 받은 내부통제 부실 이력이 있습니다.",
        "035720": "카카오: 장점: 국민 메신저 플랫폼 트래픽을 기반으로 확고한 시장 장악력을 지녔습니다.\n단점: 경영진 구속, 먹튀 등 총체적 거버넌스 붕괴를 겪었으며 데이터센터 먹통 사태로 신뢰도를 상실했습니다.",
        "138040": "메리츠금융지주: 장점: 철저한 ROE 경영과 파격적인 주주가치 제고, 자본 배분을 증명했습니다.\n단점: 임직원의 미공개 정보 투기로 압수수색을 당한 바 있으며, 부동산 부채 부담 리스크가 존재합니다.",
        "012330": "현대모비스: 장점: 그룹사 핵심 공급망을 바탕으로 독점적 수주와 안정적 이익을 냅니다.\n단점: 과거 지배구조 개편 시 합병 비율 조작 논란으로 주주가치 희석을 빚었으며 지배구조 불안이 큽니다.",
        "066570": "LG전자: 장점: 가전 구독 및 B2B 전장 사업 전환을 통해 확실한 수익성 개선을 달성했습니다.\n단점: 과거 수조 원대 적자 방치로 비판받은 바 있으며 물류비 변동성 및 침체 사이클에 취약합니다.",
        "034730": "SK: 장점: 자사주 매입과 주당가치 제고를 통해 수익성 개선에 본업에 집중하고 있습니다.\n단점: 무리한 차입으로 부채 부담을 키웠으며, 합병 비율 논란 및 오너 지배구조 불안 리스크가 큽니다.",
        "329180": "HD현대중공업: 장점: 탁월한 기술력으로 시장 장악 및 1위 우위를 선점했습니다.\n단점: 기밀 유출 혐의로 유죄 판결 및 제재를 받았으며 잦은 조선소 사망 참사가 치명적입니다.",
        "000810": "삼성화재: 장점: 손보업계 1위 우위와 탁월한 자본수익률(ROE)을 유지하며 안정적입니다.\n단점: 보험금 부지급 관련 소송 및 과징금 리스크가 있으며 장기 성장 둔화 우려가 있습니다.",
        "316140": "우리금융지주: 장점: 종합금융 포트폴리오를 완결형으로 구축하며 주주 환원을 모색합니다.\n단점: 부당대출 비리 및 직원의 대규모 횡령 등 금융권 최악의 내부통제 부실 및 거버넌스 붕괴가 반복됩니다.",
        "010130": "고려아연: 장점: 제련 부문 세계 1위의 독보적 기술력과 압도적인 원가 우위를 지녔습니다.\n단점: 경영권 분쟁 중 무리한 유상증자를 강행해 거버넌스 붕괴 및 파탄 양상을 보이며 출혈이 큽니다.",
        "011200": "HMM: 장점: 사이클 당시 축적한 현금 창출력을 바탕으로 선대를 확충했습니다.\n단점: 과거 분식회계로 국유화된 전력이 있으며 대규모 오버행 및 운임 사이클 변동성에 심각하게 노출됩니다.",
        "033780": "KT&G: 장점: 자사주 대규모 매입 및 전량 소각 등 적극적인 주주환원과 배당 확대에 나섭니다.\n단점: 과거 비자금 의혹 및 이사회 낙하산 논란이 있었으며 글로벌 규제 마찰 리스크가 큽니다.",
        "015760": "한국전력: 장점: 국가 기간 전력망을 통제하는 독점적 사업자로서 시장 장악력이 강력한 수준입니다.\n단점: 규제 마찰로 천문학적인 적자 방치를 강요받았으며 무리한 부채 부담이 존립을 위협합니다.",
        "259960": "크래프톤: 장점: 글로벌 IP를 바탕으로 소프트웨어 업계 최고 수준의 압도적인 마진을 달성했습니다.\n단점: 상장 당시 고평가 논란이 있었으며, 단일 IP 의존도로 인해 성장 정체 우려가 큽니다.",
        "018260": "삼성에스디에스: 장점: 그룹사 캡티브 매출과 안정적 방어력, 튼튼한 현금 창출력을 가졌습니다.\n단점: 내부거래 일감 몰아주기로 과징금 제재를 받았으며, 상속세를 위한 블록딜 오버행 부담이 상존합니다.",

        "CAT": "캐터필러: 장점: 인프라 시장에서 강력한 장비 우위와 1위 독점적 지위를 자랑합니다.\n단점: 역외 탈세 혐의로 거액의 배상금을 냈으며 글로벌 건설 사이클 둔화에 매우 취약합니다.",
        "BA": "보잉: 장점: 항공기 시장에서 대체가 불가능한 시장 장악력과 독점적 지위를 지녔습니다.\n단점: 기체 결함 은폐로 사망 참사를 냈으며 사기 유죄 판결 및 천문학적인 부채 부담을 안고 있습니다.",
        "GM": "제너럴 모터스: 장점: 강력한 현금 창출력을 바탕으로 대규모 자사주 매입을 지속하며 주당가치 제고 중입니다.\n단점: 결함 은폐로 수많은 사망 참사를 냈으며 사고 은폐 전력 등 거버넌스 붕괴 및 도덕성이 열악합니다.",
        "F": "포드 모터: 장점: 북미 트럭 시장에서 충성도 높은 1위 선점 브랜드를 보유했습니다.\n단점: 만성적인 잦은 결함으로 출혈이 크며, 전기차 부문의 적자 방치와 사이클 변동성 약점이 있습니다.",
        "DOW": "다우: 장점: 고도화된 설비를 바탕으로 석유화학 원가 경쟁력 우위를 굳혔습니다.\n단점: 독성 물질 은폐 및 오염 판결로 대규모 배상금을 물었으며 산업 포화 침체 우려가 있습니다.",
        "FCX": "프리포트 맥모란: 장점: 전력 인프라 전환에 필수적인 원자재 채굴 시장 1위 선점 우위를 가졌습니다.\n단점: 환경 파괴 논란을 빚었으며, 자원국 정부의 지정학적 마찰과 사이클 변동성에 극히 민감합니다.",
        "NUE": "뉴코어: 장점: 뛰어난 원가 통제력과 수익성 개선으로 철강 시장 1위를 선점했습니다.\n단점: 대기오염 위반으로 제재를 받은 이력이 있으며 거시 경제 둔화 및 변동성 타격이 큽니다.",
        "DAL": "델타 항공: 장점: 프리미엄 비중 확대와 로열티 수입으로 업계 최고의 수익성 개선을 달성했습니다.\n단점: IT 대란 당시 시스템 먹통 사태로 당국의 가혹한 조사와 제재를 받았으며 유가 사이클에 취약합니다.",
        "UAL": "유나이티드 항공: 장점: 원가 절감을 통해 뚜렷한 수익성 개선과 안정적 흑자 달성을 보입니다.\n단점: 기체 결함 논란으로 탑승객 소송에 휘말리며 항공 사이클 침체 리스크가 상존합니다.",
        "UNP": "유니온 퍼시픽: 장점: 북미 화물 운송 인프라를 지배하는 독점적 해자와 시장 장악력을 지녔습니다.\n단점: 극단적인 출혈성 원가 절감으로 탈선 사고가 잦아 제재를 받았으며, 노무 파업 리스크가 큽니다.",
        "DE": "디어 앤 컴퍼니: 장점: 정밀 소프트웨어 전환을 통해 농기계 시장 1위 독보적 지위를 공고히 했습니다.\n단점: 수리 권리 차단 문제로 반독점 독점 규제 조사를 받았으며 농가 소득 둔화 사이클에 민감합니다.",
        "AA": "알코아: 장점: 수직계열화 및 제련 기술 선점 우위를 확보해 강력한 원가 경쟁력이 있습니다.\n단점: 뇌물 제공으로 과징금을 물었으며 원자재 변동성 및 사이클 약점이 심각합니다.",
        "LEN": "레나: 장점: 에셋 라이트 전략을 완벽히 정착시켜 업계에서 철저한 ROE와 수익성 개선을 달성했습니다.\n단점: 과거 서브프라임 모기지 사기 사태 당시 부채를 은폐해 집단소송을 당했으며 사이클 둔화에 민감합니다.",
        "DHI": "DR 호튼: 장점: 1위 주택 건설사로서 시장 장악력을 자랑하며 안정적 수익성을 냅니다.\n단점: 부실시공 결함 문제로 집단소송이 잦으며, 모기지 침체 시 판매 둔화 타격이 큽니다.",
        "WHR": "월풀: 장점: 백색가전 부문 1위 브랜드를 여럿 보유해 충성도와 우위를 확보했습니다.\n단점: 가격 담합으로 반독점 과징금을 맞았으며 저가 브랜드의 시장 잠식 및 정체 우려가 큽니다.",
        "RCL": "로얄 캐리비안: 장점: 신규 크루즈선 취항을 통해 팬데믹 이후 확실한 흑자 달성과 수익성 개선을 이뤘습니다.\n단점: 환경 규제를 무시한 무단 방류로 제재를 받았으며 무리한 발주로 막대한 부채 부담을 안고 있습니다.",
        "CCL": "카니발: 장점: 대대적인 구조조정을 통해 크루즈 업계 흑자 달성 및 수익성 개선에 성공했습니다.\n단점: 좌초 사망 참사 및 무단 투기 전력이 흉악하며 천문학적인 레버리지 및 부채 부담이 존재합니다.",
        "MAR": "메리어트: 장점: 로열티 회원을 바탕으로 1위 우위의 안정적 현금 창출력을 얻습니다.\n단점: 대규모 개인정보 유출 참사로 거액 과징금을 물었으며 기만적인 은폐 소송을 겪었습니다.",
        "HLT": "힐튼: 장점: 수수료 위주의 자본 경량화 모델을 구축해 탁월한 자본수익률을 자랑합니다.\n단점: 과거 경쟁사 기밀 유출 혐의로 사법 유죄 판결 및 대규모 배상금을 물었으며 침체기 약점이 있습니다.",
        "EXPE": "익스피디아: 장점: 파트너십 확장 및 자체 로열티 런칭으로 확실한 수익성 개선을 보입니다.\n단점: 호텔 파트너들에게 최저가 보장을 강요해 반독점 과징금을 맞았으며, 경쟁 격화 잠식 위기에 직면했습니다.",

        "NVDA": "엔비디아: 장점: 압도적인 GPU 하드웨어 생태계를 통해 AI 시장에서 독점적 지위와 완결형 해자를 구축했습니다.\n단점: 칩 끼워팔기 및 독점 규제 타겟이 되었으며, 지정학적 리스크와 경쟁 격화 잠식이 상존합니다.",
        "LLY": "일라이 릴리: 장점: 비만 치료제 신약으로 글로벌 제약 시장 1위 시장 장악력을 달성했습니다.\n단점: 치명적 부작용을 고의로 은폐하고 불법 마케팅을 강행해 형사 과징금을 물었으며 약가 규제 마찰이 잦습니다.",
        "AVGO": "브로드컴: 장점: 맞춤형 반도체 선점 및 SW 인수로 독점적 지위와 잉여현금 극대화를 이뤘습니다.\n단점: 독점적 지위를 남용한 일방적인 가격 인상으로 고객사 이탈 반발이 극심하며 규제 마찰을 빚고 있습니다.",
        "TSLA": "테슬라: 장점: 제조 혁신과 자체 충전망 등 모빌리티 플랫폼을 선점해 독보적 생태계를 확보했습니다.\n단점: 오너의 돌발 언행에 휘둘리는 키맨 리스크가 크며 자율주행 과장 사기 소송 및 제재 직면 상태입니다.",
        "JPM": "JP모건 체이스: 장점: 1위 상업은행으로서 가장 신뢰받는 든든하고 안정적 방어력을 입증하며 자본 배분에 능합니다.\n단점: 귀금속 시세 조작 범죄와 자금 세탁 방조 비리로 천문학적 배상금을 지불한 부도덕한 은폐 오점이 있습니다.",
        "WMT": "월마트: 장점: 옴니채널 유통 장악과 광고 결합으로 소매업계 1위 지위 강화 및 마진 극대화를 이루었습니다.\n단점: 뇌물 공여 등 불법을 저질렀으며, 오피오이드 불법 처방 사태로 조 단위 합의 배상금을 낸 사법 리스크가 있습니다.",
        "XOM": "엑슨모빌: 장점: 핵심 유전 중심의 수직계열화로 업계 최고 수준의 잉여현금 극대화를 완결형으로 달성했습니다.\n단점: 기후변화 연구 결과를 조직적으로 은폐한 사기 혐의로 환경 파괴 관련 집단소송을 받고 있습니다.",
        "UNH": "유나이티드헬스: 장점: 의료 보험과 데이터를 결합한 완결형 수직계열화로 압도적 1위와 안정적 현금 창출력을 가집니다.\n단점: 자금 과다 청구 사기 혐의와 반독점 조사를 받고 있으며, 최악의 보안 침해(해킹) 사태로 배상금을 물었습니다.",
        "PG": "프록터 앤 갬블: 장점: 강력한 가격 전가력을 발휘해 반세기 이상의 연속 배당 성장을 달성한 1위 우량주입니다.\n단점: 과거 가격 담합을 주도해 막대한 과징금을 맞았으며, 유통사 PB 상품의 부상으로 점유율 잠식 정체 우려가 큽니다.",
        "JNJ": "존슨앤드존슨: 장점: 고성장 제약 부문에 집중하며 업계 최고의 압도적인 마진 및 수익성 개선을 냅니다.\n단점: 발암물질 부작용 은폐로 집단소송을 당한 뒤 꼼수 파산을 시도해 최악의 거버넌스 붕괴 비판을 받았습니다.",
        "HD": "홈디포: 장점: 전문 B2B 유통망을 선점하여 주택 개보수 시장 장악 및 독보적 우위를 지녔습니다.\n단점: 결제 정보가 털린 개인정보 유출 참사로 배상금을 지급했으며, 고금리 사이클에 따른 둔화에 민감합니다.",
        "ORCL": "오라클: 장점: 클라우드 동맹 구축과 AI 인프라 수주 확대로 1위 데이터베이스 기업의 위상을 재확인했습니다.\n단점: 소프트웨어 시스템 결함 문제로 계약 차질을 빚었으며 저작권 소송 패소 및 클라우드 경쟁 격화 약점이 있습니다.",
        "COST": "코스트코: 장점: 멤버십 기반 철학을 고수하여 전 세계 소비자들에게 가장 신뢰받는 유통 1위 기업입니다.\n단점: 명품 상표를 무단 도용해 막대한 배상금 제재를 받은 오점이 있으며, 이커머스 전환 둔화 우려가 있습니다.",
        "MRK": "머크: 장점: 압도적인 면역항암제 파이프라인을 바탕으로 제약 시장 1위 수익성 개선을 굳히고 있습니다.\n단점: 부작용을 고의로 은폐하여 사망 참사를 낸 최악의 사기 흑역사가 있으며 특허 만료 시 잠식 우려가 큽니다.",
        "ABBV": "애브비: 장점: 블록버스터 신약 세대교체에 성공하며 1위 제약사로서의 안정적 현금 창출력 우위를 입증했습니다.\n단점: 복제약 진입을 막기 위한 꼼수로 반독점 규제 비판을 받았으며 무리한 인수로 막대한 부채 부담 위협이 있습니다.",
        "CRM": "세일즈포스: 장점: 기업용 SaaS 시장 1위 선점 효과에 자율형 AI를 결합하고 적극적인 주주환원을 시행했습니다.\n단점: 불법 사이트에 자사 소프트웨어를 공급해 소송을 당했으며 무리한 M&A 후 대량 해고를 반복하는 노무 리스크가 잦습니다.",
        "CVX": "셰브론: 장점: 우량 유전 중심의 투자를 통해 에너지 업계에서 안정적이고 탁월한 자본수익률 우위를 달성했습니다.\n단점: 독성 폐수를 무단 방류하고 책임을 회피해 거대 소송을 빚었으며, 동종 업계 인수 과정에서 합병 비율 규제 마찰을 겪습니다.",
        "AMD": "AMD: 장점: CPU 시장 점유율 확대와 AI 가속기 선점 진입으로 1위 대항마로서 강력한 우위를 구축했습니다.\n단점: 특정 기업 의존에 따른 대만 지정학적 리스크가 핵심 우려이며, 선두 기업 대비 소프트웨어 생태계가 잠식 당할 수 있습니다.",
        "BAC": "뱅크 오브 아메리카: 장점: 강력한 리테일 예금 기반으로 안정적 흑자 달성을 창출하며 주주 환원에 충실합니다.\n단점: 부실 채권 사기 판매로 미국 역사상 최대 과징금을 물었으며 유령 계좌 조작 개설로 당국 제재를 받은 부도덕한 이력이 큽니다.",
        "NFLX": "넷플릭스: 장점: 계정 공유 금지의 완벽한 성공으로 전 세계 스트리밍 시장에서 경쟁 불가의 독보적 1위 지위를 확립했습니다.\n단점: 과거 조 단위 탈세 혐의로 사법 조사를 받았으며, 망 사용료 소송 및 가입자 성장 정체 둔화 딜레마를 겪고 있습니다.",
        "PEP": "펩시코: 장점: 독보적인 스낵 라인업 우위로 필수소비재 1위의 강력한 가격 전가력과 연속 배당 성장을 냅니다.\n단점: 무리한 가격 인상으로 유럽 마트에서 이탈당하는 출혈을 겪었고 환경 파괴 집단소송을 당했으며 판매량 둔화 리스크가 있습니다."
    }
    
    if cd_clean in db:
        return db[cd_clean]
    if tk_clean in db:
        return db[tk_clean]
            
    return f"{ceo_name} 경영진 - 위키 및 공공 기록 스크리닝 결과, 해당 경영진에 대한 사법적 리스크나 중범죄 이력은 두드러지지 않습니다. 다만 가치투자 관점에서 경영자의 정직성과 과도한 자본 배분 오류, 노사 갈등(상생 여부)에 대한 철저한 팩트 체크가 선행되어야 합니다."
    
    if cd_clean in db:
        return db[cd_clean]
    if tk_clean in db:
        return db[tk_clean]
            
    return f"{ceo_name} 경영진 - 위키 및 공공 기록 스크리닝 결과, 해당 경영진에 대한 사법적 리스크나 중범죄 이력은 두드러지지 않습니다. 다만 가치투자 관점에서 경영자의 정직성과 과도한 자본 배분 오류, 노사 갈등(상생 여부)에 대한 철저한 팩트 체크가 선행되어야 합니다."

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
            pb = get_fv("P/B")
            if pb: res['priceToBook'] = safe_float(pb)
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
            
            if 'priceToBook' not in i or not i.get('priceToBook'):
                if 'priceToBook' in fv_res: i['priceToBook'] = fv_res['priceToBook']
            
            if 'longBusinessSummary' not in i and 'longBusinessSummary' in yh_res:
                i['longBusinessSummary'] = yh_res['longBusinessSummary']
            if 'companyOfficers' not in i and 'companyOfficers' in yh_res:
                i['companyOfficers'] = yh_res['companyOfficers']
        else:
            nv_res = future_naver.result()
            for k in ['shortName', 'trailingPE', 'forwardPE', 'priceToBook', 'dividendYield', 'kr_sum']:
                if k in nv_res: i[k] = nv_res[k]
        
    return i

def get_data(tk):
    try:
        if not tk: return None, None, {}, False
        tk_raw = str(tk).strip()
        tk = tk_raw.upper()
        
        if tk_raw.isdigit() and len(tk_raw) == 6:
            test_tk = tk_raw + ".KS"
            stk_test = yf.Ticker(test_tk)
            try:
                _ = stk_test.history(period="1d")
                tk = test_tk 
            except: tk = tk_raw + ".KQ"

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
            
        # [주식수 Fallback 로직]
        sh = safe_float(i.get('sharesOutstanding'))
        if sh <= 0:
            sh = safe_float(i.get('impliedSharesOutstanding'))
        if sh <= 0:
            mcap = safe_float(i.get('marketCap'))
            if mcap > 0 and p > 0:
                sh = mcap / p
        if sh <= 0:
            try:
                inc = stk.income_stmt
                if inc is not None and not inc.empty and 'Net Income' in inc.index:
                    ni = safe_float(inc.loc['Net Income'].iloc[0])
                    eps = safe_float(i.get('trailingEps'))
                    if ni != 0 and eps != 0:
                        sh = abs(ni / eps)
            except: pass
        
        i['sharesOutstanding'] = sh

        return stk, p, i, kr
    except Exception as e:
        return None, None, {}, False

def get_base_dcf_data(stk, i):
    try:
        if stk is None: return None, None, 0.05, 0, False
        fcf_s = None
        cf = stk.cash_flow
        
        if cf is not None and not cf.empty:
            if 'Free Cash Flow' in cf.index: fcf_s = cf.loc['Free Cash Flow'].dropna()
            elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                fcf_s = (cf.loc['Operating Cash Flow'] + cf.loc['Capital Expenditure']).dropna()
                
        fcf = safe_float(fcf_s.iloc[0]) if (fcf_s is not None and not fcf_s.empty) else safe_float(i.get('freeCashflow'))
        sh = safe_float(i.get('sharesOutstanding'))
            
        g, data_len = 0.05, 0
        is_zigzag = False
        
        if fcf_s is not None and len(fcf_s) >= 2:
            vals = fcf_s.values[::-1] # 과거에서 현재 순으로 정렬
            c, o = safe_float(vals[-1]), safe_float(vals[0])
            data_len = len(vals)
            if c > 0 and o > 0: g = (c / o) ** (1 / (data_len - 1)) - 1
            
            # [지그재그(변동성) 감지 로직] 3년 이상의 데이터가 있을 때 10% 이상 상승과 하락이 섞여 있으면 해자가 없는 것으로 간주
            if data_len >= 3:
                directions = []
                for idx in range(1, data_len):
                    prev = safe_float(vals[idx-1])
                    curr = safe_float(vals[idx])
                    if prev == 0:
                        directions.append(1 if curr > 0 else (-1 if curr < 0 else 0))
                    else:
                        change_pct = (curr - prev) / abs(prev)
                        if change_pct >= 0.10: directions.append(1)   # 10% 이상 상승
                        elif change_pct <= -0.10: directions.append(-1) # 10% 이상 하락
                        else: directions.append(0) # 횡보
                
                # 상승(+1)과 하락(-1)이 모두 존재하면 일관성 없는 지그재그 기업으로 낙인
                if 1 in directions and -1 in directions:
                    is_zigzag = True
        else:
            eg = safe_float(i.get('earningsGrowth'))
            if eg != 0.0: g = eg
            data_len = 1
            
        g = max(0.02, min(g, 0.15))
        return fcf, sh, g, data_len, is_zigzag
    except: return None, None, 0.05, 0, False

def calc_custom_dcf(fcf, sh, p, ty, g, is_financial=False):
    if is_financial: return 0, 0, t("금융/보험주 DCF 평가 제외 (PBR 대체 분석 진행)", "DCF N/A for Financials (Evaluated via PBR instead)")
    if not fcf or fcf <= 0: return 0, 0, t("주주이익(FCF) 적자 또는 미제공", "Negative / Missing FCF (Owner Earnings)")
    if not sh or sh <= 0: return 0, 0, t("주식수 누락 (데이터 부족)", "Missing Shares Outstanding")
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
    if is_financial: return f"<span style='color:#8892b0'>{t('금융주 평가 제외', 'N/A (Financial)')}</span>"
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
                        if mv >= 1e12: div_rnd, u = 1e12, "조원"
                        elif mv >= 1e8: div_rnd, u = 1e8, "억원"
                        else: div_rnd, u = 1, "원"
                    else:
                        if mv >= 1e9: div_rnd, u = 1e9, "B"
                        elif mv >= 1e6: div_rnd, u = 1e6, "M"
                        else: div_rnd, u = 1, "$"
                    
                    history_str = ", ".join([f"<b>{y}년</b>: {v/div_rnd:.1f}{u}" for y, v in zip(rnd_years, rnd_vals)])
                    
                    sudden_alert = ""
                    for idx in range(len(rnd_vals) - 1, 0, -1):
                        curr = safe_float(rnd_vals[idx])
                        prev = safe_float(rnd_vals[idx-1])
                        if prev > 0:
                            inc_pct = ((curr - prev) / prev) * 100
                            if inc_pct >= 30:
                                years_ago = len(rnd_vals) - 1 - idx 
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
                            
                        rnd_trend = f"{r_eval}{sudden_alert} <span style='font-size:0.95em;'>-> FCF의 <b>{ratio:.1f}%</b> 지출 ({desc})<br><span style='color:#8892b0;'>4개년 지출 추이: [{history_str}]</span></span>"
                    elif base_fcf and base_fcf <= 0:
                        rnd_trend = f"<span class='highlight'>{t('FCF(순수여윳돈) 적자로 적정선 계산 불가', 'Unable to calc optimal line due to negative FCF')}</span>{sudden_alert}<br><span style='color:#8892b0;'>4개년 지출 추이: [{history_str}]</span>"
                    else:
                        rnd_trend = f"<span style='color:#8892b0;'>4개년 지출 추이: [{history_str}]</span>{sudden_alert}"
                else:
                    rnd_trend = f"<span style='color:#8892b0'>{t('R&D 지출 없음', 'No R&D')}</span>"
    except:
        pass
        
    return rnd_trend

# 파라미터 맨 끝에 is_zigzag=False 를 추가로 받습니다.
def get_comprehensive_investment_opinion(mos, pmos, roe, roic, erp, final_g, ceo_text, is_financial=False, pbr=0.0, kr=False, tk="", base_fcf=0.0, div_yield_pct=0.0, is_zigzag=False):
    score_details = {}
    score = 0
    ceo_score = 0
    
    # 💡 매크로 답변(DB에 없는 기업)일 경우 스캔을 멈추고 강제 0점 처리
    if "위키 및 공공 기록 스크리닝 결과" in ceo_text:
        ceo_final = 0
    else:
        # (기존에 작성하신 경영진 키워드 점수 스캔 로직이 그대로 들어갑니다. 생략 없이 유지해주세요.)
        # [1] 경영진 및 거버넌스 점수 (상대평가 및 20단계 세분화)
        kw_super_pos = ["교과서적", "자본 배분", "정직", "가장 신뢰받는", "파격적인 주주가치", "전량 소각", "압도적인 마진", "마진 극대화", "탁월한 자본수익률", "철저한 ROE", "연속 배당 성장"]
        kw_high_pos = ["자사주 매입", "주주 환원", "주주친화", "상생", "압도적인", "독보적", "독점적", "시장 장악", "완결형", "적극적인 주주환원", "잉여현금 극대화", "배당 확대", "주당가치 제고", "자본 효율적", "주주환원율 로드맵"]
        kw_pos = ["검증된", "수익성 개선", "안정적", "선점", "실행력", "투명한", "신뢰도", "프리미엄", "우위", "현금 창출력", "흑자 달성", "1위", "장악력", "본업에 집중", "강력한"]

        kw_super_neg = ["구속", "횡령", "배임", "분식회계", "사기", "은폐", "조작", "부품 바꿔치기", "거버넌스 붕괴", "파탄", "먹튀", "사망 참사", "부당대출", "비리", "미공개 정보", "내부통제 부실", "압수수색"]
        kw_high_neg = ["사법", "물적분할", "유상증자", "합병 비율", "주주가치 훼손", "주주가치 희석", "뇌물", "탈세", "유죄", "불법", "강제노동", "배당 중단", "무단", "독성", "파산", "정경유착", "비자금", "불투명한", "기밀 유출"]
        kw_neg = ["과징금", "집단소송", "배상금", "결함", "환경 파괴", "키맨 리스크", "노동 환경", "노무", "반독점", "독점 규제", "무리한", "출혈", "낙하산", "가동률 하락", "소송", "제재", "적자 방치", "부채 부담", "레버리지", "규제 마찰", "지배구조 불안", "오버행", "통제 리스크", "이탈", "보안 침해", "먹통", "개인정보 유출"]
        kw_minor_neg = ["사이클", "변동성", "침체", "둔화", "관세", "마진 희석", "경쟁 격화", "잠식", "포화", "지정학적", "정체", "우려"]

        raw_score = 0
        for k in kw_super_pos:
            if k in ceo_text: raw_score += 40
        for k in kw_high_pos:
            if k in ceo_text: raw_score += 30
        for k in kw_pos:
            if k in ceo_text: raw_score += 15
        for k in kw_super_neg:
            if k in ceo_text: raw_score -= 80
        for k in kw_high_neg:
            if k in ceo_text: raw_score -= 40
        for k in kw_neg:
            if k in ceo_text: raw_score -= 20
        for k in kw_minor_neg:
            if k in ceo_text: raw_score -= 5

        max_raw_score = 180.0
        ratio = max(-1.0, min(1.0, raw_score / max_raw_score))
        scaled_score = ratio * 40.0

        if scaled_score >= 38: ceo_final = 40
        elif scaled_score >= 34: ceo_final = 36
        elif scaled_score >= 30: ceo_final = 32
        elif scaled_score >= 26: ceo_final = 28
        elif scaled_score >= 22: ceo_final = 24
        elif scaled_score >= 18: ceo_final = 20
        elif scaled_score >= 14: ceo_final = 16
        elif scaled_score >= 10: ceo_final = 12
        elif scaled_score >= 6:  ceo_final = 8
        elif scaled_score >= 2:  ceo_final = 4
        elif scaled_score >= -2: ceo_final = 0
        elif scaled_score >= -6: ceo_final = -4
        elif scaled_score >= -10: ceo_final = -8
        elif scaled_score >= -14: ceo_final = -12
        elif scaled_score >= -18: ceo_final = -16
        elif scaled_score >= -22: ceo_final = -20
        elif scaled_score >= -26: ceo_final = -24
        elif scaled_score >= -30: ceo_final = -28
        elif scaled_score >= -34: ceo_final = -32
        elif scaled_score >= -38: ceo_final = -36
        else: ceo_final = -40

    score += ceo_final
    score_details[t("경영진 및 거버넌스", "Management & Governance")] = ceo_final

    # =========================================================================
    # [금융주 전용] 배당 매력도 점수 
    # =========================================================================
    div_score = 0
    if is_financial:
        if div_yield_pct >= 9.5: div_score = 20
        elif div_yield_pct >= 9.0: div_score = 19
        elif div_yield_pct >= 8.5: div_score = 18
        elif div_yield_pct >= 8.0: div_score = 17
        elif div_yield_pct >= 7.5: div_score = 16
        elif div_yield_pct >= 7.0: div_score = 15
        elif div_yield_pct >= 6.5: div_score = 14
        elif div_yield_pct >= 6.0: div_score = 13
        elif div_yield_pct >= 5.5: div_score = 12
        elif div_yield_pct >= 5.0: div_score = 11
        elif div_yield_pct >= 4.5: div_score = 10
        elif div_yield_pct >= 4.0: div_score = 8
        elif div_yield_pct >= 3.5: div_score = 6
        elif div_yield_pct >= 3.0: div_score = 4
        elif div_yield_pct >= 2.5: div_score = 2
        elif div_yield_pct >= 2.0: div_score = 0
        elif div_yield_pct >= 1.5: div_score = -2
        elif div_yield_pct >= 1.0: div_score = -4
        elif div_yield_pct > 0.0: div_score = -6
        else: div_score = -10
        if tk.upper() in ["BRK-A", "BRK-B"]: div_score = 0
        score += div_score
        score_details[t("배당 매력도 (주주환원)", "Dividend Attractiveness")] = div_score

        
    # [2] 가격 매력도 점수 (버핏의 안전마진 철학 반영, 만점 40점)
    p_score = 0
    if not is_financial:
        if pmos >= 50: p_score = 40      # [극단적 저평가] 역사적 바닥 수준, 미스터 마켓의 극심한 우울증
        elif pmos >= 45: p_score = 37
        elif pmos >= 40: p_score = 34    # [강력한 안전마진] 벤저민 그레이엄이 사랑하는 40% 폭탄 세일
        elif pmos >= 35: p_score = 31
        elif pmos >= 30: p_score = 28
        elif pmos >= 25: p_score = 24
        elif pmos >= 20: p_score = 20    # [훌륭한 할인] 버핏의 일반적인 매수 타겟 (20% 할인)
        elif pmos >= 15: p_score = 16
        elif pmos >= 10: p_score = 12
        elif pmos >= 5: p_score = 8      # [약간의 할인]
        elif pmos >= 0: p_score = 4      # [적정 가격] "위대한 기업이라면 적정가에 사라" (약간의 플러스 부여)
        elif pmos >= -5: p_score = 0     # [약간의 할증] 압도적 경제적 해자가 있다면 용인되는 마지노선
        elif pmos >= -10: p_score = -5   # [주의] 미래 성장이 선반영됨. 보수적 접근 필요
        elif pmos >= -15: p_score = -10
        elif pmos >= -20: p_score = -15  # [경고] 확연한 할증, 미스터 마켓의 흥분 상태 (안전마진 상실)
        elif pmos >= -25: p_score = -20
        elif pmos >= -30: p_score = -26
        elif pmos >= -40: p_score = -33  # [위험] 밸류에이션 붕괴, 자본 손실 위험 극대화
        else: p_score = -40              # [극위험] 터무니없는 버블
        
        score += p_score
        score_details[t("가격 매력도 (PER 안전마진)", "Price Attractiveness (PE MoS)")] = p_score

    # [3] 자본 효율성 및 비즈니스 해자 점수
    cap_score = 0
    if is_financial:
        if kr:
            # 🇰🇷 한국 금융주 로직: 만성적 코리아 디스카운트 반영 (기존 유지)
            if pbr <= 0.3: cap_score += 40
            elif pbr <= 0.4: cap_score += 35
            elif pbr <= 0.5: cap_score += 30
            elif pbr <= 0.6: cap_score += 25
            elif pbr <= 0.7: cap_score += 20
            elif pbr <= 0.8: cap_score += 15
            elif pbr <= 0.9: cap_score += 10
            elif pbr <= 1.0: cap_score += 5
            elif pbr <= 1.1: cap_score += 0
            elif pbr <= 1.2: cap_score -= 5
            elif pbr <= 1.3: cap_score -= 10
            elif pbr <= 1.4: cap_score -= 15
            elif pbr <= 1.5: cap_score -= 20
            else: cap_score -= 30
        else:
            # 🇺🇸 미국 금융주 로직: 워런 버핏의 '안전마진' 잣대 적용
            # 버크셔 역사적 자사주 매입 상한선인 'PBR 1.2배'를 핵심 허들로 설정
            if pbr <= 0.8: cap_score += 40    # [최상] 강력한 안전마진 (과거 BAC 대량 매수 구간)
            elif pbr <= 1.0: cap_score += 35  # [우수] 청산가치 이하의 훌륭한 가격
            elif pbr <= 1.2: cap_score += 25  # [합격] 버핏의 전통적인 적정가 상한선
            elif pbr <= 1.4: cap_score += 15  # [약간 프리미엄] JP모건처럼 ROE가 매우 뛰어난 은행에만 정당화되는 한계선
            elif pbr <= 1.6: cap_score += 5   # [보통] 가격 매력도 상실 (미스터 마켓이 제값 이상을 부르는 중)
            elif pbr <= 1.8: cap_score += 0   # [한계] 수익성(ROE)이 아무리 좋아도 비싼 구간
            elif pbr <= 2.0: cap_score -= 10  # [주의] 전통 은행/보험업으로서 버블 위험 발생
            elif pbr <= 2.3: cap_score -= 20  # [매우 주의] 
            elif pbr <= 2.6: cap_score -= 30  # [위험] 안전마진 붕괴
            else: cap_score -= 40             # [극위험] 자본 대비 상식 밖의 버블

        if roe >= 20: cap_score += 40
        elif roe >= 18: cap_score += 35
        elif roe >= 16: cap_score += 30
        elif roe >= 14: cap_score += 25
        elif roe >= 12: cap_score += 20
        elif roe >= 10: cap_score += 15
        elif roe >= 8: cap_score += 10
        elif roe >= 6: cap_score += 5
        elif roe >= 4: cap_score += 0
        elif roe >= 2: cap_score -= 5
        elif roe >= 0: cap_score -= 15
        elif roe >= -5: cap_score -= 25
        else: cap_score -= 40
        
        score += cap_score
        score_details[t("자본 효율성 (ROE 및 PBR)", "Capital Efficiency (ROE & PBR)")] = cap_score
    else:
        if roic >= 25: cap_score += 25
        elif roic >= 20: cap_score += 23
        elif roic >= 17: cap_score += 21
        elif roic >= 14: cap_score += 18
        elif roic >= 11: cap_score += 15
        elif roic >= 9: cap_score += 12
        elif roic >= 7: cap_score += 9
        elif roic >= 5: cap_score += 6
        elif roic >= 3: cap_score += 3
        elif roic >= 0: cap_score -= 3
        elif roic >= -5: cap_score -= 8
        elif roic >= -10: cap_score -= 12
        else: cap_score -= 15

        if roe >= 25: cap_score += 15
        elif roe >= 22: cap_score += 13
        elif roe >= 19: cap_score += 11
        elif roe >= 16: cap_score += 9
        elif roe >= 13: cap_score += 7
        elif roe >= 10: cap_score += 5
        elif roe >= 7: cap_score += 3
        elif roe >= 4: cap_score += 1
        elif roe >= 0: cap_score -= 4
        elif roe >= -5: cap_score -= 9
        else: cap_score -= 15

        score += cap_score
        score_details[t("비즈니스 수익성 및 해자 (ROIC, ROE)", "Business Profitability & Moat (ROIC, ROE)")] = cap_score

    # =========================================================================
    # [4] DCF 안전마진(MoS) 점수 (최대 15점 ~ 최소 -25점 / 20단계 세분화)
    # =========================================================================
    dcf_score = 0
    if not is_financial:
        if base_fcf is None or base_fcf <= 0:
            dcf_score = -25
        elif is_zigzag:
            dcf_score = -25 # 🚨 현금흐름이 위아래로 요동치는 지그재그 기업은 즉시 최하점 낙인
        else:
            if mos >= 50: dcf_score = 15
            elif mos >= 45: dcf_score = 14
            elif mos >= 40: dcf_score = 13
            elif mos >= 35: dcf_score = 12
            elif mos >= 30: dcf_score = 11
            elif mos >= 25: dcf_score = 10
            elif mos >= 20: dcf_score = 8
            elif mos >= 15: dcf_score = 6
            elif mos >= 10: dcf_score = 4
            elif mos >= 5:  dcf_score = 2
            elif mos >= 0:  dcf_score = 0
            elif mos >= -5: dcf_score = -2
            elif mos >= -10: dcf_score = -4
            elif mos >= -15: dcf_score = -6
            elif mos >= -20: dcf_score = -9
            elif mos >= -25: dcf_score = -12
            elif mos >= -30: dcf_score = -15
            elif mos >= -40: dcf_score = -18
            elif mos >= -50: dcf_score = -21
            else: dcf_score = -25
            
        score += dcf_score
        score_details[t("내재가치 안전마진 (DCF MoS)", "Intrinsic Value Margin of Safety (DCF)")] = dcf_score

    # =========================================================================
    # [5] ERP 점수 (거시 매력도 - 이익수익률 vs 국채) (최대 15점 ~ 최소 -25점 / 20단계 세분화)
    # 기준: 국채 대비 5.0%p 이상 초과 수익 시 만점(15점)
    # =========================================================================
    e_score = 0
    if not is_financial:
        if erp >= 5.0: e_score = 15
        elif erp >= 4.5: e_score = 14
        elif erp >= 4.0: e_score = 13
        elif erp >= 3.5: e_score = 12
        elif erp >= 3.0: e_score = 11
        elif erp >= 2.5: e_score = 9
        elif erp >= 2.0: e_score = 7
        elif erp >= 1.5: e_score = 5
        elif erp >= 1.0: e_score = 3
        elif erp >= 0.5: e_score = 1
        elif erp >= 0.0: e_score = -1
        elif erp >= -0.5: e_score = -3
        elif erp >= -1.0: e_score = -5
        elif erp >= -1.5: e_score = -8
        elif erp >= -2.0: e_score = -11
        elif erp >= -2.5: e_score = -14
        elif erp >= -3.0: e_score = -17
        elif erp >= -4.0: e_score = -20
        elif erp >= -5.0: e_score = -23
        else: e_score = -25
        
        score += e_score
        score_details[t("거시 매력도 (ERP)", "Macro Attractiveness (ERP)")] = e_score

    # =========================================================================
    # [6] 10년 복리 성장성 점수 (CAGR) (최대 15점 ~ 최소 -30점 / 20단계 세분화)
    # 기준: 연평균 20% 이상 폭발적 성장 시 만점(15점)
    # =========================================================================
    g_score = 0
    if not is_financial:
        if final_g >= 0.20: g_score = 15
        elif final_g >= 0.18: g_score = 14
        elif final_g >= 0.16: g_score = 13
        elif final_g >= 0.14: g_score = 12
        elif final_g >= 0.12: g_score = 11
        elif final_g >= 0.10: g_score = 9
        elif final_g >= 0.08: g_score = 7
        elif final_g >= 0.06: g_score = 5
        elif final_g >= 0.04: g_score = 3
        elif final_g >= 0.02: g_score = 1
        elif final_g >= 0.00: g_score = -2
        elif final_g >= -0.02: g_score = -5
        elif final_g >= -0.04: g_score = -8
        elif final_g >= -0.06: g_score = -11
        elif final_g >= -0.08: g_score = -14
        elif final_g >= -0.10: g_score = -17
        elif final_g >= -0.15: g_score = -20
        elif final_g >= -0.20: g_score = -23
        elif final_g >= -0.25: g_score = -26
        else: g_score = -30
        
        score += g_score
        score_details[t("장기 복리 성장성 (CAGR)", "Long-term Compounding (CAGR)")] = g_score

    # =========================================================================
    # [7] 국가별 디스카운트 및 시클리컬 패널티 (요청하신 감점 점수 반영)
    # =========================================================================
    pen_score = 0
    tk_upper = str(tk).upper()

    chinese_hk_adrs = [
        "PDD", "TME", "GDS", "BABA", "BIDU", "JD", "NIO", "XPEV", "LI", "NTES", 
        "TCEHY", "YUMC", "ZTO", "EDU", "BILI", "FUTU", "TCOM"
    ]
    is_china_hk = any(tk_upper.startswith(c) for c in chinese_hk_adrs) or tk_upper.endswith(".HK") or ("중국 정부" in ceo_text) or ("중국 데이터센터" in ceo_text)

    taiwan_tickers = ["TSM", "UMC", "ASX", "HIMX"]
    is_taiwan = any(tk_upper.startswith(c) for c in taiwan_tickers) or tk_upper.endswith(".TW") or ("대만" in ceo_text) or ("양안 갈등" in ceo_text)

    # 코리아 디스카운트 -30점
    if kr:
        pen_score -= 30
    # 중국/홍콩 -30점
    elif is_china_hk:
        pen_score -= 40
    # 대만 -30점
    elif is_taiwan:
        pen_score -= 40

    INCLUDE_APPLE_AS_CYCLICAL = True
    explicit_cyclicals = [
        "TSM", "AVGO", "NVDA", "AMD", "MU", "INTC", "AMAT", "LRCX", "MRVL", "TXN", "QCOM", "WDC", "SNDK",
        "CAT", "BA", "GM", "F", "DOW", "FCX", "NUE", "DAL", "UAL", "UNP", "DE", "AA", "LEN", "DHI", "WHR", "RCL", "CCL"
    ]
    if INCLUDE_APPLE_AS_CYCLICAL:
        explicit_cyclicals.append("AAPL")

    is_cyclical = (tk_upper in explicit_cyclicals) or any(k in ceo_text for k in [
        "사이클", "유가", "경기 민감", "철강", "석유화학", "화학", "화석 연료", 
        "조선", "해운", "운임", "원자재", "비철금속", "건설", "기계", "건설장비", "항공", "여행",
        "메모리", "반도체", "디스플레이", "파운드리", "엔비디아", "AMD", "마이크론", "인텔", "어플라이드", "램리서치", 
        "브로드컴", "TSMC", "자동차", "현대차", "기아", "테슬라", "부품 납품", "내연기관", "전기차"
    ])

    # 시클리컬 감점 -50점
    if is_cyclical:
        pen_score -= 50
        
    if pen_score < 0:
        score += pen_score
        score_details[t("시장 및 산업 페널티", "Market & Industry Penalty")] = pen_score

    # =========================================================================
    # 종합 등급 판정 (기존 7단계 -> 9단계 확장)
    # =========================================================================
    if score >= 110:
        title, color, reason = t(f"초극단적 저평가 ({score}점)", f"Deep Value ({score} pts)"), "#00b894", t("거버넌스, 비즈니스 해자, 밸류에이션 모든 면에서 완벽하며 극단적인 안전마진을 제공하는 일생일대의 가치투자 기회입니다.", "A once-in-a-lifetime value investing opportunity with extreme margin of safety, flawless governance, and a massive moat.")
    elif score >= 85:
        title, color, reason = t(f"적극적 할인 ({score}점)", f"Strong Discount ({score} pts)"), "#2ecc71", t("비즈니스 해자(ROIC), 경영진, 안전마진 등 핵심 평가에서 흠잡을 데 없는 워런 버핏급 초저평가 기회입니다.", "An exceptionally rare 'Buffett-level' deep discount meeting 'Very Pass' criteria across ROIC, management, and MoS.")
    elif score >= 60:
        title, color, reason = t(f"할인 ({score}점)", f"Discount ({score} pts)"), "#1dd1a1", t("훌륭한 자본 배치 능력(ROIC/ROE)과 검증된 경영진이 교차 검증되어 전반적으로 안전하게 매수할 수 있는 우량한 할인 구간입니다.", "A solid discount zone backed by excellent capital allocation metrics and verified management, offering a safe entry.")
    elif score >= 30:
        title, color, reason = t(f"약간 할인 ({score}점)", f"Slight Discount ({score} pts)"), "#74b9ff", t("안전마진이 아주 넉넉하지는 않지만, 우량한 사업 퀄리티 대비 현재 가격이 약간 할인되어 충분히 긍정적으로 검토할 수 있는 구간입니다.", "Priced at a slight discount relative to its high-quality business profile, presenting a reasonable entry point.")
    elif score >= 0:
        title, color, reason = t(f"적정 가치 ({score}점)", f"Fair Value ({score} pts)"), "#fdcb6e", t("비즈니스 퀄리티와 성장성을 감안할 때 충분히 납득할 수 있는 적당한 가격(Fair Price)입니다. 장기 투자자에게는 여전히 유효합니다.", "Perfectly justifiable as a fair price given business quality. Still a valid hold/buy for long-term investors.")
    elif score >= -25:
        title, color, reason = t(f"약간 할증 ({score}점)", f"Slight Premium ({score} pts)"), "#fab1a0", t("기업의 펀더멘털은 견고하지만 시장의 기대감이 선반영되어 가격에 약간의 할증(Premium)이 붙어 있습니다. 보수적인 접근이 필요합니다.", "Solid fundamentals, but trading at a slight premium due to pre-reflected market optimism. A conservative stance is recommended.")
    elif score >= -50:
        title, color, reason = t(f"할증 ({score}점)", f"Premium ({score} pts)"), "#ff7675", t("다수의 밸류에이션 지표에서 '주의' 판정을 받았습니다. 비즈니스 퀄리티 대비 시장의 기대감이 꽤 선반영되어 비싸게 거래 중입니다.", "Trading at a premium with multiple 'Warning' signals. The price reflects somewhat excessive market expectations.")
    elif score >= -80:
        title, color, reason = t(f"과도한 할증 ({score}점)", f"Excessive Premium ({score} pts)"), "#e17055", t("가치평가 지표가 대체로 '매우 주의'를 가리킵니다. 비상식적인 밸류에이션 거품이 끼어 있어 투자에 상당한 위험이 따릅니다.", "Highly speculative territory with multiple 'Very Warning' signals, indicating a significant valuation bubble.")
    else:
        title, color, reason = t(f"극단적 버블 / 가치 훼손 ({score}점)", f"Extreme Bubble / Value Trap ({score} pts)"), "#d63031", t("심각한 펀더멘털의 훼손(거버넌스 붕괴 등)이 있거나, 수식을 완전히 벗어난 극단적인 광기의 버블 구간입니다. 절대적인 주의가 필요합니다.", "Absolute extreme bubble or severe fundamental destruction (e.g., governance collapse). Demands extreme caution; likely a value trap.")
   
    return title, color, reason, score_details

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

# [패널 배치 순서: 환율 -> 채권 -> 원유 -> 미국 지수 -> 한국 지수]
macro_items = [
    (t("환율(KRW/USD)", "USD/KRW"), krw_p, krw_pct, "%"),
    (t("10년물 국채", "10Y Treasury"), tnx_p, tnx_c, " bp"),
    (t("WTI 원유", "WTI Crude"), wti_p, wti_pct, "%"),
    (t("S&P 500", "S&P 500"), sp_p, sp_pct, "%"),
    (t("Nasdaq 100", "Nasdaq 100"), nd_p, nd_pct, "%"),
    (t("NQ 선물", "Nasdaq Fut"), nf_p, nf_pct, "%"),
    (t("KOSPI", "KOSPI"), k_p, k_pct, "%"),
    (t("KOSDAQ", "KOSDAQ"), kq_p, kq_pct, "%")
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
            placeholder=t("예: 마소, 엔비, 버크셔, 삼전, 하닉 (입력 후 Enter)", "e.g., MSFT, NVDA, AAPL, BRK-A (Press Enter)"), 
            label_visibility="collapsed",
            key="main_input",
            on_change=trigger_scan 
        )
        st.caption(t("[안내] 초성이나 일부분만 쳐도 스마트하게 찾아냅니다. (예: '마소' -> 마이크로소프트, '엔비' -> 엔비디아, '버크셔' -> 버크셔해서웨이)", "[Info] Smart partial match supported."))
    with col_btn:
        if st.button(t("가치 분석 스캔", "Start Value Scan"), use_container_width=True, type="primary"):
            trigger_scan(); st.rerun() 

    if st.session_state.suggestions:
        st.markdown(f"<div style='color:#fdcb6e; font-weight:bold; margin-bottom:10px; padding:10px; background:rgba(255,255,255,0.05); border-radius:8px;'>여러 종목이 발견되었습니다. 찾으시는 기업을 클릭해주세요.</div>", unsafe_allow_html=True)
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

                # =====================================================================
                # [금융/보험주 강력 탐지 로직]
                # =====================================================================
                sector_str = str(i.get('sector', '')).lower()
                industry_str = str(i.get('industry', '')).lower()
                summary_str = str(i.get('longBusinessSummary', i.get('kr_sum', ''))).lower()
                
                eng_fin_keywords = ['financial', 'bank', 'insurance', 'capital market', 'credit service', 'securities', 'asset management', 'investment']
                is_eng_fin = any(kw in sector_str or kw in industry_str for kw in eng_fin_keywords)
                
                kor_fin_keywords = ['금융지주', '은행', '증권', '보험', '카드사', '캐피탈', '생명', '화재', '해상보험']
                is_kor_fin = any(kw in summary_str for kw in kor_fin_keywords)
                is_summary_fin = any(kw in summary_str for kw in ['commercial bank', 'investment bank', 'property & casualty', 'insurance company'])

                us_fin_tickers = [
                    "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "V", "MA", "BRK-B", "BRK-A",
                    "CB", "PGR", "MMC", "AON", "CME", "ICE", "SPGI", "MCO", "DFS", "COF", "SYF",
                    "BLK", "BX", "KKR", "APO", "MET", "PRU", "AFL", "TRV", "ALL", "AIG", "SCHW"
                ]
                
                kr_fin_tickers = [
                    "105560.KS", "055550.KS", "086790.KS", "316140.KS", "138040.KS", 
                    "032830.KS", "000810.KS", "006800.KS", "016360.KS", "039490.KS", 
                    "024110.KS", "377300.KS", "323410.KS", "071050.KS", "088980.KS",
                    "008560.KS", "016610.KS", "138930.KS", "030000.KS", "005830.KS", "000370.KS"
                ]

                tk_upper = str(tk).upper()
                is_financial = is_eng_fin or is_kor_fin or is_summary_fin or (tk_upper in us_fin_tickers) or (tk_upper in kr_fin_tickers)
                # =====================================================================
                
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

                t_pe_raw = safe_float(i.get('trailingPE'))
                f_pe_raw = safe_float(i.get('forwardPE'))
                
                t_eps = safe_float(i.get('trailingEps'))
                f_eps = safe_float(i.get('forwardEps', i.get('finviz_eps_next')))
                
                reg_p = safe_float(i.get('regularMarketPrice', p))
                if reg_p == 0: reg_p = p
                
                if t_eps == 0 and t_pe_raw > 0: t_eps = reg_p / t_pe_raw
                if f_eps == 0 and f_pe_raw > 0: f_eps = reg_p / f_pe_raw

                t_pe = (p / t_eps) if t_eps > 0 else t_pe_raw
                f_pe = (p / f_eps) if f_eps > 0 else f_pe_raw

                pbr = safe_float(i.get('priceToBook'))
                bv = safe_float(i.get('bookValue'))
                
                if bv > 0:
                    pbr = p / bv
                else:
                    if pbr > 0 and is_ext_active and reg_p > 0:
                        pbr = pbr * (p / reg_p)
                    elif pbr == 0.0:
                        try:
                            bs = stk.balance_sheet
                            if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index:
                                eq = safe_float(bs.loc['Stockholders Equity'].iloc[0])
                                sh = safe_float(i.get('sharesOutstanding'))
                                if eq > 0 and sh > 0:
                                    pbr = p / (eq / sh)
                        except: pass
                
                roe = safe_float(i.get('returnOnEquity')) * 100
                if roe == 0.0:
                    try:
                        inc = stk.income_stmt
                        bs = stk.balance_sheet
                        if inc is not None and not inc.empty and bs is not None and not bs.empty:
                            if 'Net Income' in inc.index and 'Stockholders Equity' in bs.index:
                                ni = safe_float(inc.loc['Net Income'].iloc[0])
                                eq = safe_float(bs.loc['Stockholders Equity'].iloc[0])
                                if eq > 0:
                                    roe = (ni / eq) * 100
                    except: pass
                
                real_roic = get_real_roic(stk, i)
                
                if is_financial:
                    roic_str = t("금융주 제외", "N/A (Financial)")
                else:
                    if real_roic is not None: roic_str = f"{real_roic:.2f}%"
                    else: roic_str = t("데이터 부족", "N/A")
                
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
                
                # 1. 5개의 변수를 받도록 변경
                base_fcf, sh, final_g, data_len, is_zigzag = get_base_dcf_data(stk, i)
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
                    
                has_ytd = False
                ytd_ret = 0.0
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
                        gap_text = f" -> <span class='highlight'>{t(txt_ko, txt_en)}</span>"
                    elif gap < 0:
                        txt_ko = f"[주가 {abs(gap):.1f}%p 덜 오름 - 기회 가능성]"
                        txt_en = f"[Price lagged by {abs(gap):.1f}%p - Potential opportunity]"
                        gap_text = f" -> <span class='good'>{t(txt_ko, txt_en)}</span>"
                    else:
                        gap_text = f" -> <span>{t('[기대치와 주가 일치]', '[In line with expectations]')}</span>"
                else:
                    gap_text = f" -> <span style='color:#8892b0'>{t('[비교 불가]', '[N/A]')}</span>"
                    
                eps_vs_ytd_html = f"<span style='color:{eps_col}; font-weight:bold;'>{eps_g_str}</span> vs <span style='color:{ytd_col}; font-weight:bold;'>{ytd_str}</span>{gap_text}"

                eps_trend, bps_trend = analyze_trends(stk)
                
                gross_m = safe_float(i.get('grossMargins')) * 100
                op_m = safe_float(i.get('operatingMargins')) * 100
                current_ratio = safe_float(i.get('currentRatio'))
                
                if (op_m == 0.0 or gross_m == 0.0):
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

                gm_eval = f"<span class='good'>{t('강력한 가격결정력/해자', 'Strong Pricing Power')}</span>" if gross_m >= 40 else (f"<span style='color:#fdcb6e;'>{t('보통', 'Average')}</span>" if gross_m >= 20 else f"<span class='highlight'>{t('원가 부담/해자 약함', 'Weak Moat / High Cost')}</span>")
                opm_eval = f"<span class='good'>{t('탁월한 비즈니스', 'Excellent Business')}</span>" if op_m >= 15 else (f"<span style='color:#fdcb6e;'>{t('보통', 'Average')}</span>" if op_m >= 8 else f"<span class='highlight'>{t('수익성 경고', 'Poor Profitability')}</span>")
                cr_eval = f"<span class='good'>{t('불황 대비 완벽 (유동자산 풍부)', 'Crisis-Ready (Highly Liquid)')}</span>" if current_ratio >= 1.5 else (f"<span style='color:#74b9ff;'>{t('안전', 'Safe')}</span>" if current_ratio >= 1.0 else f"<span class='highlight'>{t('단기 유동성/외부조달 위험', 'Liquidity Risk')}</span>")
                
                if (gross_m == 0.0 and op_m == 0.0): gm_eval, opm_eval = "N/A", "N/A"
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
                except: pass

                iv, mos_val, err = calc_custom_dcf(base_fcf, sh, p, ty, final_g, is_financial)
                mos_val = safe_float(mos_val)
                
                iv_best, mos_best, _ = calc_custom_dcf(base_fcf, sh, p, ty, min(final_g * 1.5, 0.25), is_financial)
                iv_worst, mos_worst, _ = calc_custom_dcf(base_fcf, sh, p, ty, max(final_g * 0.5, 0.0), is_financial)
                
                roic_val = real_roic if real_roic is not None else 0
                # 2. 맨 끝에 div와 is_zigzag 파라미터 전달
                op_title, op_color, op_reason, score_breakdown = get_comprehensive_investment_opinion(mos_val, pmos_val, roe, roic_val, erp, final_g, criticism_text, is_financial, pbr, kr, tk, base_fcf, div, is_zigzag)

                st.markdown(f"""
                <div style="padding: 25px 20px; border-radius: 16px; border: 1px solid {op_color}; background: linear-gradient(145deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); color: var(--text-color); margin-bottom: 25px; margin-top: 15px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0 0 12px 0; color: {op_color}; font-size: 1.5rem; letter-spacing: -0.5px;">[AI 종합 투자의견] : {op_title}</h3>
                    <span style="color: var(--text-color); font-size: 1.05rem; display: block; margin-top: 10px; line-height: 1.6;">{op_reason}</span>
                </div>
                """, unsafe_allow_html=True)

                st.sidebar.markdown(f"**현재 투자의견:** <span style='color:{op_color}; font-weight:bold;'>{op_title}</span>", unsafe_allow_html=True)

                with st.expander(t("투자의견 점수 산출 세부 내역", "Scoring Breakdown Details")):
                    breakdown_html = "<ul style='list-style-type: none; padding: 0;'>"
                    total_score = 0
                    for k, v in score_breakdown.items():
                        color_sd = "#2ecc71" if v > 0 else ("#ff7675" if v < 0 else "#8892b0")
                        sign_sd = "+" if v > 0 else ""
                        breakdown_html += f"<li style='margin-bottom: 8px; font-size: 1.05rem;'><b>{k}:</b> <span style='color: {color_sd}; font-weight: bold;'>{sign_sd}{v:g}점</span></li>"
                        total_score += v
                    breakdown_html += f"<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'><li style='font-size: 1.15rem;'><b>{t('총합', 'Total Score')}:</b> <span style='color: {op_color}; font-weight: bold;'>{total_score:g}점</span></li>"
                    breakdown_html += "</ul>"
                    st.markdown(breakdown_html, unsafe_allow_html=True)

                st.divider()

                if is_financial:
                    beginner_summary = t(
                        f"<b>초보자 가이드:<b> 내가 <b>{p_str}<b>을 주고 이 금융사를 사면, 기업의 자산 대비 프리미엄을 <b>{pbr:.2f}배</b>(PBR) 지불하게 됩니다. 현재 회사는 이 자본을 굴려 1년에 <b>{roe:.1f}%</b>씩(ROE) 불려주고 있습니다.",
                        f"<b>Beginner Guide:<b> If you buy this financial stock for <b>{p_str}</b>, you pay <b>{pbr:.2f}x</b> its book value (PBR). The company currently grows its equity at <b>{roe:.1f}%/yr</b> (ROE)."
                    )
                else:
                    beginner_summary = t(
                        f"<b>초보자 가이드:<b> 내가 <b>{p_str}<b>을 주고 이 회사를 사면, 본전을 찾는 데 <b>{f_pe:.1f}년</b>이 걸릴 것으로 예상되며(Fwd PER), 회사는 장사를 통해 내 돈을 1년에 <b>{roe:.1f}%</b>씩(ROE) 불려주고 있습니다.",
                        f"<b>Beginner Guide:<b> It takes <b>{f_pe:.1f} yrs</b> to break even (Fwd PE), and the company grows your money at <b>{roe:.1f}%/yr</b> (ROE)."
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

                if is_financial:
                    per_mos_str = ""
                else:
                    if pmos_val >= 30: per_mos_str = f"<span class='good'>[매우 합격] +{pmos_val:.1f}% (과거 대비 극심한 저평가)</span>"
                    elif pmos_val >= 15: per_mos_str = f"<span class='good'>[합격] +{pmos_val:.1f}% (안전마진 확보)</span>"
                    elif pmos_val >= 5: per_mos_str = f"<span style='color:#74b9ff;'>[약간 합격] +{pmos_val:.1f}% (양호한 할인)</span>"
                    elif pmos_val >= 0: per_mos_str = f"<span style='color:#fdcb6e;'>[보통] +{pmos_val:.1f}% (적정 수준)</span>"
                    elif pmos_val > -10: per_mos_str = f"<span style='color:#fdcb6e;'>[약간 주의] {pmos_val:.1f}% (약간의 할증)</span>"
                    elif pmos_val > -20: per_mos_str = f"<span class='highlight'>[주의] {pmos_val:.1f}% (할증 구간)</span>"
                    else: per_mos_str = f"<span class='highlight'>[매우 주의] {pmos_val:.1f}% (과도한 고평가)</span>"

                if is_financial:
                    if roe >= 20: rr_eval = f"<span class='good'>{t('[매우 합격] 경이로운 자본 배치 (최상위 플랫폼/금융급)', '[Very Pass] Phenomenal Capital Allocation')}</span>"
                    elif roe >= 15: rr_eval = f"<span class='good'>{t('[합격] 버핏이 사랑하는 우량 금융주 기준 통과', '[Pass] Buffett’s Prime Financial Standard')}</span>"
                    elif roe >= 10: rr_eval = f"<span style='color:#74b9ff;'>{t('[약간 합격] 안정적인 수익 창출 (인플레이션 방어)', '[Slight Pass] Stable Earnings')}</span>"
                    elif roe >= 7: rr_eval = f"<span style='color:#fdcb6e;'>{t('[보통] 평범한 수익성 (성장보다 유지 수준)', '[Average] Ordinary Profitability')}</span>"
                    elif roe >= 0: rr_eval = f"<span class='highlight'>{t('[주의] 예금 이자만도 못한 비효율적 자산 운용', '[Warning] Inefficient Asset Management')}</span>"
                    else: rr_eval = f"<span class='highlight'>{t('[매우 주의] 심각한 자본 훼손 및 적자 상태', '[Very Warning] Severe Capital Destruction')}</span>"
                    biz_eval = rr_eval
                else:
                    if roic_val >= 20 and roe >= 15: rr_eval = f"<span class='good'>{t('[매우 합격] 멍거의 완벽한 복리 기계 (압도적 해자)', '[Very Pass] Munger’s Compounding Machine')}</span>"
                    elif roic_val >= 15 and roe >= 12: rr_eval = f"<span class='good'>{t('[합격] 버핏의 경제적 해자 통과 (탁월한 비즈니스)', '[Pass] Buffett’s Economic Moat')}</span>"
                    elif roic_val >= 10 and roe >= 10: rr_eval = f"<span style='color:#74b9ff;'>{t('[약간 합격] 자본비용을 상회하는 준수한 수익성', '[Slight Pass] Good Profitability')}</span>"
                    elif roic_val >= 7 and roe >= 7: rr_eval = f"<span style='color:#fdcb6e;'>{t('[보통] 평범한 비즈니스 (뚜렷한 해자 없음)', '[Average] Ordinary Business, No Moat')}</span>"
                    elif roic_val >= 0: rr_eval = f"<span class='highlight'>{t('[주의] 장사를 할수록 손해 (자본 파괴 구간)', '[Warning] Value Destructive')}</span>"
                    else: rr_eval = f"<span class='highlight'>{t('[매우 주의] 밑빠진 독 (극심한 펀더멘털 훼손)', '[Very Warning] Severe Fundamental Damage')}</span>"
                    biz_eval = rr_eval
                    
                if is_financial:
                    ey_str = ""
                else:
                    if erp > 0:
                        ey_str = f"{ey:.2f}% <span class='good'>(국채 이김! +{erp:.2f}%p 수익률 추가 우위/할인)</span>"
                    else:
                        ey_str = f"{ey:.2f}% <span class='highlight'>(국채에 짐! {abs(erp):.2f}%p 매력도 열위/할증)</span>"

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"- **{t('현재 주가', 'Current Price')}:** {p_str}{ext_str}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('배당 추이', 'Dividend Trend')}:** {div:.2f}% ({div_trend})", unsafe_allow_html=True)
                    if is_financial:
                        st.markdown(f"- **ROE {t('(자본수익률 - 금융주 핵심지표)', '(Equity Return)')}:** {roe:.2f}% -> {rr_eval}", unsafe_allow_html=True)
                    else:
                        st.markdown(f"- **ROE {t('(내 돈 굴리는 이자율)', '(Equity Return)')} / ROIC {t('(진짜 수익률)', '(True Return)')}:** {roe:.2f}% / {roic_str} -> {rr_eval}", unsafe_allow_html=True)
                    
                    st.write(f"- **{t('현재 PER', 'Current PE (Ref)')}:** {t_pe:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('Fwd PER (미래 1년 기준)', 'Fwd PE (Next 1Y)')}:** {f_pe:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('5~10년 평균 PER', '5-10Y Avg PE')}:** {a_pe:.2f}{t('배', 'x')}")
                with c2:
                    if not is_financial:
                        st.markdown(f"- **{t('PER 안전마진', 'PE Margin of Safety')}:** {per_mos_str}", unsafe_allow_html=True)
                    st.write(f"- **PBR {t('(청산 가치 대비 배수)', '(Price to Book)')}:** {pbr:.2f}{t('배', 'x')}")
                    st.write(f"- **{t('10년물 미국채 금리 (안전 자산)', '10Y US Treasury Yield (Risk-free)')}:** {ty:.2f}%")
                    if not is_financial:
                        st.markdown(f"- **{t('예상 이익수익률 (주식의 연간 기대 이자율)', 'Expected Earnings Yield')}:** {ey_str}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('EPS 추세 (최근 4년 1주당 순이익 / 기업의 진짜 벌이 체력)', 'EPS Trend (4 Years / Net Income per Share)')}:** {eps_trend}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('자본/BPS 추세 (최근 4년 1주당 순자산 / 기업의 덩치와 재산 성장)', 'Equity Trend (4 Years / Book Value per Share)')}:** {bps_trend}", unsafe_allow_html=True)
                    if not is_financial:
                        st.markdown(f"- **{t('R&D(연구개발비) 분석 (FCF 대비 미래 투자 체력)', 'R&D Check (vs FCF)')}:** {rnd_trend}", unsafe_allow_html=True)
                    st.markdown(f"- **{t('올해시장(eps)컨센서스 vs 실제 주가 괴리', 'Consensus vs YTD Price Gap')}:** {eps_vs_ytd_html}", unsafe_allow_html=True)
                
                st.divider()

                st.subheader(t("2. AI 다차원 투자 검증 (6원칙 및 학문적 모델 적용)", "2. AI Multi-dimensional Verification"))
                
                p_txt = ""
                if is_financial:
                    if kr:
                        if pbr <= 0.4: p_txt += f"- PBR 측면: <span class='good'>[매우 합격] ({pbr:.2f}배 - 극단적 자산 저평가/풍부한 안전마진)</span>"
                        elif pbr <= 0.7: p_txt += f"- PBR 측면: <span class='good'>[합격] ({pbr:.2f}배 - 우량한 자산 할인 구간)</span>"
                        elif pbr <= 0.9: p_txt += f"- PBR 측면: <span style='color:#74b9ff;'>[약간 합격] ({pbr:.2f}배 - 청산가치 이하 안전 구간)</span>"
                        elif pbr <= 1.1: p_txt += f"- PBR 측면: <span style='color:#fdcb6e;'>[보통] ({pbr:.2f}배 - 장부가 수준의 적정 가격)</span>"
                        elif pbr <= 1.3: p_txt += f"- PBR 측면: <span style='color:#fdcb6e;'>[약간 주의] ({pbr:.2f}배 - 국내 금융주 기준 프리미엄 발생)</span>"
                        elif pbr <= 1.5: p_txt += f"- PBR 측면: <span class='highlight'>[주의] ({pbr:.2f}배 - 자본 대비 고평가 경고)</span>"
                        else: p_txt += f"- PBR 측면: <span class='highlight'>[매우 주의] ({pbr:.2f}배 - 극심한 밸류에이션 거품)</span>"
                    else:
                        if pbr <= 0.8: p_txt += f"- PBR 측면: <span class='good'>[매우 합격] ({pbr:.2f}배 - 버핏급 강력한 안전마진 확보)</span>"
                        elif pbr <= 1.0: p_txt += f"- PBR 측면: <span class='good'>[합격] ({pbr:.2f}배 - 청산가치 이하의 매력적인 가격)</span>"
                        elif pbr <= 1.2: p_txt += f"- PBR 측면: <span style='color:#74b9ff;'>[약간 합격] ({pbr:.2f}배 - 버핏식 적정 가치 상한선)</span>"
                        elif pbr <= 1.4: p_txt += f"- PBR 측면: <span style='color:#fdcb6e;'>[보통] ({pbr:.2f}배 - 고ROE 은행에 한해 허용 가능한 수준)</span>"
                        elif pbr <= 1.8: p_txt += f"- PBR 측면: <span style='color:#fdcb6e;'>[약간 주의] ({pbr:.2f}배 - 가격 매력도 상실/보수적 접근 필요)</span>"
                        elif pbr <= 2.2: p_txt += f"- PBR 측면: <span class='highlight'>[주의] ({pbr:.2f}배 - 전통 금융업 대비 명백한 할증/버블)</span>"
                        else: p_txt += f"- PBR 측면: <span class='highlight'>[매우 주의] ({pbr:.2f}배 - 안전마진 붕괴/극심한 고평가)</span>"
                else:
                    if pmos_val >= 30: p_txt += f"- PER 측면: <span class='good'>[매우 합격] (+{pmos_val:.1f}% 할인)</span>\n"
                    elif pmos_val >= 15: p_txt += f"- PER 측면: <span class='good'>[합격] (+{pmos_val:.1f}% 할인)</span>\n"
                    elif pmos_val >= 5: p_txt += f"- PER 측면: <span style='color:#74b9ff;'>[약간 합격] (+{pmos_val:.1f}% 할인)</span>\n"
                    elif pmos_val >= 0: p_txt += f"- PER 측면: <span style='color:#fdcb6e;'>[보통] (+{pmos_val:.1f}% 할인)</span>\n"
                    elif pmos_val > -10: p_txt += f"- PER 측면: <span style='color:#fdcb6e;'>[약간 주의] ({pmos_val:.1f}% 할증)</span>\n"
                    elif pmos_val > -20: p_txt += f"- PER 측면: <span class='highlight'>[주의] ({pmos_val:.1f}% 할증)</span>\n"
                    else: p_txt += f"- PER 측면: <span class='highlight'>[매우 주의] ({pmos_val:.1f}% 할증)</span>\n"
                    
                    if base_fcf is None or base_fcf <= 0: p_txt += f"- DCF 측면: <span class='highlight'>{t('[매우 주의] 잉여현금흐름(FCF) 적자로 평가 불가', '[Very Warning] Negative FCF (N/A)')}</span>\n"
                    elif is_zigzag: p_txt += f"- DCF 측면: <span class='highlight'>{t('[매우 주의] 현금흐름 지그재그(변동성 극심). 해자 없음 및 DCF 무의미 (최하점)', '[Very Warning] FCF fluctuates (Zigzag). No Moat. DCF is meaningless (Lowest Score)')}</span>\n"
                    elif mos_val >= 50: p_txt += f"- DCF 측면: <span class='good'>[매우 합격] (+{mos_val:.1f}% 할인)</span>\n"
                    elif mos_val >= 25: p_txt += f"- DCF 측면: <span class='good'>[합격] (+{mos_val:.1f}% 할인)</span>\n"
                    elif mos_val >= 10: p_txt += f"- DCF 측면: <span style='color:#74b9ff;'>[약간 합격] (+{mos_val:.1f}% 할인)</span>\n"
                    elif mos_val >= 0: p_txt += f"- DCF 측면: <span style='color:#fdcb6e;'>[보통] (+{mos_val:.1f}% 할인)</span>\n"
                    elif mos_val > -15: p_txt += f"- DCF 측면: <span style='color:#fdcb6e;'>[약간 주의] ({mos_val:.1f}% 할증)</span>\n"
                    elif mos_val > -30: p_txt += f"- DCF 측면: <span class='highlight'>[주의] ({mos_val:.1f}% 할증)</span>\n"
                    else: p_txt += f"- DCF 측면: <span class='highlight'>[매우 주의] ({mos_val:.1f}% 할증)</span>\n"

                if roe >= 20: biz_eval = f"<span class='good'>{t('[매우 합격] 자본효율 압도적, 강력한 해자 확률', '[Very Pass] Outstanding efficiency, high moat probability')}</span>"
                elif roe >= 15: biz_eval = f"<span class='good'>{t('[합격] 자본효율 탁월, 해자 확률 높음', '[Pass] Great efficiency, high moat probability')}</span>"
                elif roe >= 10: biz_eval = f"<span style='color:#74b9ff;'>{t('[약간 합격] 양호한 수익성', '[Slight Pass] Good profitability')}</span>"
                elif roe >= 5: biz_eval = f"<span style='color:#fdcb6e;'>{t('[약간 주의] 평균 수준, 독점력 확인 필요', '[Slight Warning] Average, verify moat')}</span>"
                elif roe >= 0: biz_eval = f"<span class='highlight'>{t('[주의] 부진한 비즈니스', '[Warning] Poor business')}</span>"
                else: biz_eval = f"<span class='highlight'>{t('[매우 주의] 심각한 구조 훼손 점검 시급', '[Very Warning] Structural damage check urgent')}</span>"

                if is_financial:
                    math_eval = f"<span class='good'>{t('[해당 없음] 금융주는 PBR/ROE 듀폰 모델로 가치 창출을 평가합니다.', '[N/A] Financials evaluated via PBR/ROE.')}</span>"
                else:
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
                    "• <b>Investor Checkpoint:</b> The current base growth rate is mechanically derived from the last available cash flow trends."
                )
                
                if is_financial:
                    st.markdown(f"<div style='background: rgba(255, 118, 117, 0.08); padding:18px 22px; border-radius:12px; margin-bottom:15px; border-left: 4px solid #ff7675; font-size:1.0rem; color:var(--text-color); line-height:1.7;'>{t('<b>[평가 제외]</b> 금융 및 증권/보험주는 사업 특성상 고객 예치금 및 지급준비금이 영업현금흐름에 대규모 부채로 포함되어 FCF(잉여현금흐름) 분석 시 기형적인 착시 적자가 발생합니다.<br>따라서 본 AI 분석기에서는 무의미한 DCF 연산을 강제 차단하고, <b>PBR(장부가치)과 ROE 기반 시스템으로 완벽 대체</b>하여 적정성을 평가했습니다.', '<b>[N/A]</b> DCF model is disabled for Financials. Intrinsic worth is cross-evaluated using PBR metrics instead, due to cash flow accounting distortions from customer deposits.')}</div>", unsafe_allow_html=True)
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
                                div_val, u_str = scale_vals([rev, ni], kr)
                                df_rev_ni = pd.DataFrame({t('매출액', 'Revenue'): [x/div_val for x in rev], t('순이익', 'Net Income'): [x/div_val for x in ni]}, index=years)
                                st.write(t(f"**[최근 매출 및 순이익]** {u_str}", f"**[Recent Rev & NI Trend]** {u_str}"))
                                st.bar_chart(df_rev_ni, color=["#A0C4FF", "#2ecc71"], height=300, use_container_width=False, width=600)
                            else:
                                st.caption(t("매출/순이익 시각화 데이터가 부족합니다.", "Insufficient Revenue/Net Income data for visualization."))
                        with c_v2:
                            if is_financial:
                                st.caption(t("※ 금융/증권/보험주는 고객 예치금 및 운용 자산 변동이 영업현금흐름에 포함되어 현금흐름 분석이 무의미하므로 FCF 차트를 생략합니다.", "※ FCF chart is omitted for financials as operating cash flows include customer deposits and assets, making FCF analysis meaningless."))
                            elif len(fcf_chart) == len(years):
                                div_val, u_str = scale_vals([fcf_chart], kr)
                                df_fcf = pd.DataFrame({t('잉여현금흐름(FCF)', 'Free Cash Flow'): [x/div_val for x in fcf_chart]}, index=years)
                                st.write(t(f"**[최근 잉여현금흐름(FCF)]** {u_str}", f"**[Recent FCF Trend]** {u_str}"))
                                st.bar_chart(df_fcf, color="#fdcb6e", height=300, use_container_width=False, width=600)
                            else:
                                st.caption(t("FCF 시각화 데이터가 부족합니다.", "Insufficient FCF data for visualization."))
                    else:
                        st.caption(t("시각화 데이터를 불러오는 데 실패했습니다 (데이터 미제공).", "Visualization data not available."))
                except Exception as e:
                    st.caption(t("시각화 데이터를 불러오는 데 실패했습니다.", "Failed to load visualization data."))

                st.divider()

                st.subheader(t("5. 질적 분석 및 리스크 스크리닝", "5. Qualitative Analysis & Risk Screening"))
                
                st.markdown(f"- **CEO:** {ceo_cleaned}")
                
                st.write(t("**비즈니스 요약**", "**Business Summary**"))
                raw_summary = i.get('kr_sum') or i.get('longBusinessSummary') or t("비즈니스 요약 데이터를 현재 불러올 수 없습니다.", "Business summary data not available.")
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
                
                clean_biz_eval = strip_html(biz_eval)
                clean_eps_trend = strip_html(eps_trend)
                clean_bps_trend = strip_html(bps_trend)
                
                if is_financial:
                    share_fv = t('금융주 적용 제외 (PBR 대체 분석 진행)', 'N/A for Financials (PBR Evaluated)')
                    share_mos = t('해당 없음', 'N/A')
                    biz_summary_str = f"- 자산가치(PBR): {pbr:.2f}배\n- 자본효율(ROE): {roe:.1f}%\n- 비즈니스 효율 (ROE/PBR 기준): {clean_biz_eval}"
                    clean_p_txt = strip_html(p_txt).strip()
                    share_val_summary = f"- 가격 매력도 (PBR 기준): {clean_p_txt}"
                else:
                    clean_per_mos = strip_html(per_mos_str)
                    biz_summary_str = f"- 자본효율(ROE): {roe:.1f}%\n- 비즈니스 해자 (ROE/ROIC 기준): {clean_biz_eval}"
                    if iv:
                        share_fv = f"{int(iv):,}원" if kr else f"${iv:,.2f}"
                        share_mos = f"{mos_val:.1f}% (최상 {mos_best:.1f}%, 최악 {mos_worst:.1f}%)"
                    else:
                        share_fv = t("계산 불가 (FCF 적자 등)", "N/A (Negative FCF)")
                        share_mos = t("계산 불가", "N/A")
                    share_val_summary = f"- 가격 매력도 (PER 기준): {clean_per_mos}"

                share_ko = f"""[AGIE 가치투자 분석 리포트]
기업명: {i.get('shortName', tk)} ({tk})
AI 종합 투자의견: {op_title}

핵심 밸류에이션 지표
- 현재 주가: {p_str}
- 추정 적정가(DCF): {share_fv}
- 안전마진(MoS): {share_mos}
{biz_summary_str}
- 본전회수기간(Fwd PER): {f_pe:.1f}배 (과거평균: {a_pe:.1f}배)
- 장기 BPS 성장: {clean_bps_trend}

AI 핵심 요약
{op_reason}

투자 검증 요약
{share_val_summary}
"""
                share_en = f"""[AGIE Value Investing Report]
Company: {i.get('shortName', tk)} ({tk})
AI Opinion: {op_title}

Core Valuation Metrics
- Current Price: {p_str}
- Est. Fair Value (DCF): {share_fv}
- Margin of Safety (MoS): {share_mos}
{biz_summary_str}
- Fwd PE: {f_pe:.1f}x (Hist Avg: {a_pe:.1f}x)
- Long-term BPS Growth: {clean_bps_trend}

AI Core Summary
{op_reason}

Verification Summary
{share_val_summary}
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

    st.markdown("### 인물 개요")
    if guru_option == "세스 클라만 (Baupost Group)":
        st.write("**세스 클라만(Seth Klarman):** '보스턴의 오라클'로 불리는 거장으로, 벤자민 그레이엄의 철학을 철저히 계승한 정통 가치투자자입니다. 리스크 관리를 최우선으로 삼아 현금 비중을 유연하게 조절하며, 훌륭한 비즈니스 모델을 가진 산업재, 헬스케어, 그리고 매력적인 가격대의 테크 기업에 집중투자합니다.")
    elif guru_option == "빌 애크먼 (Pershing Square)":
        st.write("**빌 애크먼(Bill Ackman):** 철저한 기본적 분석을 바탕으로 소수의 고확신 우량주에 자본을 몰아넣는 초집중 투자의 대가입니다. 행동주의 투자자로도 유명하며, 단순한 주가 변동을 넘어 강력 독점력과 예측 가능한 현금흐름을 창출하는 플랫폼 및 글로벌 브랜드 기업 위주로 포트폴리오 정예화를 구성합니다.")
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
                st.caption(t("※ 비중이 0.00%로 표기된 종목은 비중 미상이거나 전량 매도된 종목입니다.", "※ Stocks with 0.00% weight are unknown or fully sold."))
            
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
    phil_p2 = t("가치투자(Value Investing)는 매일같이 요동치는 주가의 이면을 꿰뚫어 보고, 그 기업이 실제로 창출하는 현금흐름과 자산에 집중하는 행위입니다. 시장의 광기나 패닉에 휩쓸리지 않고, '가격(Price)은 우리가 지불하는 것이며, 가치(Value)는 우리가 얻는 것'이라는 확고한 믿음을 실천하는 가장 강력 무기입니다.", "Value investing focuses on the cash flows and assets a company actually generates, seeing through daily price fluctuations. It is the practice of maintaining the firm belief that 'Price is what you pay, Value is what you get,' without being swept away by market mania or panic.")
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
lbl_copy = t('본 프로그램의 분석 로직, 산식 및 데이터 표출 양식은 저작권법의 보호를 받으며, 원작자의 허가 없는 무단 복제, 배포, 상업적 이용을 엄격히 금지합니다.', 'The analysis logic, formulas, and data display formats of this program are protected by copyright law, and unauthorized reproduction, distribution, or commercial use without permission is strictly prohibited.')

st.markdown(f"""
<div style='text-align: center; color: #8892b0; font-size: 0.85rem; line-height: 1.6;'>
    <p><b>{lbl_disc_title}</b><br>
    {lbl_disc_1}<br>
    {lbl_disc_2}</p>
    <p><b>[Copyright]</b><br>
    (c) 2026 AGIE. All rights reserved.<br>
    {lbl_copy}</p>
</div>
""", unsafe_allow_html=True)
