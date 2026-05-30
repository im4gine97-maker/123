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
    .guru-quote {font-style: italic; color: #8b949e; border-left: 3px solid #e3b341; padding-left: 10px; margin-bottom: 15px;}
    .highlight {color: #da3633; font-weight: bold;}
    .good {color: #3fb950; font-weight: bold;}
    .box {background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; height: 100%;}
    </style>
    """, unsafe_allow_html=True)

def safe_translate(text):
    if not text or not isinstance(text, str) or len(text) < 2: return text
    try:
        return GoogleTranslator(source='en', target='ko').translate(text[:3000])
    except:
        return text

def get_naver_finance_info(code):
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        info = {}
        name_tag = soup.select_one('.wrap_company h2 a')
        if name_tag: info['shortName'] = name_tag.text
        
        per_tag = soup.select_one('#_per')
        if per_tag: info['trailingPE'] = float(per_tag.text.replace(',', ''))
        
        pbr_tag = soup.select_one('#_pbr')
        if pbr_tag: info['priceToBook'] = float(pbr_tag.text.replace(',', ''))
        
        fwd_per_tag = soup.select_one('#_cns_per')
        if fwd_per_tag: info['forwardPE'] = float(fwd_per_tag.text.replace(',', ''))
        else: info['forwardPE'] = info.get('trailingPE', 0)
        
        div_tag = soup.select_one('#_dvr')
        if div_tag: info['dividendYield'] = float(div_tag.text.replace(',', '')) / 100
        
        summary_tag = soup.select_one('.summary_info p')
        if summary_tag: info['longBusinessSummary_kr'] = summary_tag.text
        
        info['sector'] = '한국 주식 (네이버 금융 연동)'
        return info
    except Exception:
        return None

def get_stock_data(ticker_symbol):
    if "." not in ticker_symbol:
        ticker_symbol = ticker_symbol.upper()
        
    is_korean = ticker_symbol.endswith('.KS') or ticker_symbol.endswith('.KQ')
    code = ticker_symbol.split('.')[0] if is_korean else ticker_symbol
    
    stock = yf.Ticker(ticker_symbol)
    price, info = None, {}
    for i in range(3):
        try:
            price = stock.fast_info['lastPrice']
            info = stock.info
            if not isinstance(info, dict): info = {}
            break
        except Exception:
            time.sleep(2)
            
    if is_korean and price:
        naver_info = get_naver_finance_info(code)
        if naver_info:
            info['shortName'] = naver_info.get('shortName', info.get('shortName'))
            info['trailingPE'] = naver_info.get('trailingPE') or info.get('trailingPE', 0)
            info['forwardPE'] = naver_info.get('forwardPE') or info.get('forwardPE', 0)
            info['priceToBook'] = naver_info.get('priceToBook') or info.get('priceToBook', 0)
            info['dividendYield'] = naver_info.get('dividendYield') or info.get('dividendYield', 0)
            info['sector'] = naver_info.get('sector', '한국 주식')
            if 'longBusinessSummary_kr' in naver_info:
                info['longBusinessSummary_kr'] = naver_info['longBusinessSummary_kr']

    return stock, price, info, is_korean

def calculate_buffett_dcf(stock, info, price, treasury_yield):
    try:
        fcf = info.get('freeCashflow')
        if not fcf:
            cf = stock.cash_flow
            if cf is not None and not cf.empty:
                if 'Free Cash Flow' in cf.index:
                    fcf = cf.loc['Free Cash Flow'].iloc[0]
                elif 'Operating Cash Flow' in cf.index and 'Capital Expenditure' in cf.index:
                    fcf = cf.loc['Operating Cash Flow'].iloc[0] + cf.loc['Capital Expenditure'].iloc[0]
        
        if not fcf or fcf <= 0:
            return None, 0, "최근 잉여현금흐름(FCF)이 적자이거나 야후 API에서 데이터를 제공하지 않습니다."

        shares = info.get('sharesOutstanding')
        if not shares or shares == 0:
            mcap = info.get('marketCap')
            if mcap and price > 0:
                shares = mcap / price
            else:
                return None, 0, "발행주식수 산출 불가"

        discount_rate = max(treasury_yield / 100, 0.09)
        g1, g2, tg = 0.05, 0.03, 0.02

        future_fcf = []
        current_fcf = fcf
        
        for year in range(1, 11):
            current_fcf *= (1 + g1) if year <= 5 else (1 + g2)
            future_fcf.append(current_fcf / ((1 + discount_rate) ** year))

        tv = (current_fcf * (1 + tg)) / (discount_rate - tg)
        discounted_tv = tv / ((1 + discount_rate) ** 10)
        
        intrinsic_value = (sum(future_fcf) + discounted_tv) / shares
        mos = ((intrinsic_value - price) / intrinsic_value) * 100
        
        return intrinsic_value, mos, None
        
    except Exception as e:
        return None, 0, "DCF 산출용 재무 데이터 누락"

st.title("⚡ AGIE")
st.error("🚨 **시클리컬 기업 주의:** 본 분석 모델은 알파벳, 무디스처럼 **'경제적 해자(Moat)'**를 갖추고 이익이 장기 우상향하는 기업에 최적화되어 있습니다. 경기 민감주 분석 시 밸류에이션 왜곡에 주의하십시오.")
st.info("💡 **검색 팁:** 제이피모건, jp모건, 애플, 삼성전자 등 대충 입력해도 찰떡같이 알아듣습니다.")

# 대규모 유도리 검색 사전 (띄어쓰기, 대소문자 무시를 위해 모두 띄어쓰기 없고 대문자로 맵핑)
ticker_map = {
    # 금융
    "제이피모건": "JPM", "JP모건": "JPM", "JPMORGAN": "JPM", "제이피모건체이스": "JPM",
    "골드만삭스": "GS", "모건스탠리": "MS", "뱅크오브아메리카": "BAC", "BOFA": "BAC",
    "씨티은행": "C", "씨티그룹": "C", "시티그룹": "C", "블랙록": "BLK", "웰스파고": "WFC",
    
    # 반도체 & IT & 통신
    "애플": "AAPL", "구글": "GOOGL", "알파벳": "GOOGL", "마이크로소프트": "MSFT", "마소": "MSFT",
    "아마존": "AMZN", "테슬라": "TSLA", "엔비디아": "NVDA", "메타": "META", "페이스북": "META",
    "TSMC": "TSM", "티에스엠씨": "TSM", "ASML": "ASML", "에이에스엠엘": "ASML", 
    "AMD": "AMD", "에이엠디": "AMD", "인텔": "INT
