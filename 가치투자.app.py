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
.guru-quote {font-style: italic; color: #8b949e; 
border-left: 3px solid #e3b341; padding-left: 10px; margin-bottom: 15px;}
.highlight {color: #da3633; font-weight: bold;}
.good {color: #3fb950; font-weight: bold;}
.box {background-color: #161b22; padding: 15px; 
border-radius: 8px; border: 1px solid #30363d; height: 100%;}
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
    headers = {'User-Agent': 'Mozilla/5.0'}
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
        if fwd_per_tag: 
            info['forwardPE'] = float(fwd_per_tag.text.replace(',', ''))
        else: 
            info['forwardPE'] = info.get('trailingPE', 0)
        
        div_tag = soup.select_one('#_dvr')
        if div_tag: 
            info['dividendYield'] = float(div_tag.text.replace(',', '')) / 100
        
        summary_tag = soup.select_one('.summary_info p')
        if summary_tag: info['longBusinessSummary_kr'] = summary_tag.text
        
        info['sector'] = '한국 주식(네이버연동)'
        return info
    except:
        return None

def get_stock_data(ticker_symbol):
    if "." not in ticker_symbol:
        ticker_symbol = ticker_symbol.upper()
        
    is_kr = ticker_symbol.endswith('.KS') or ticker_symbol.endswith('.KQ')
    code = ticker_symbol.split('.')[0] if is_kr else ticker_symbol
    
    stock = yf.Ticker(ticker_symbol)
    price, info = None, {}
    for i in range(3):
        try:
            price = stock.fast_info['lastPrice']
            info = stock.info
            if not isinstance(info, dict): info = {}
            break
        except:
            time.sleep(2)
            
    if is_kr and price:
        naver_info = get_naver_finance_info(code)
        if naver_info:
            info['shortName'] = naver_info.get('shortName', info.get('shortName'))
            info['trailingPE'] = naver_info.get('trailingPE', info.get('trailingPE', 0))
            info['forwardPE'] = naver_info.get('forwardPE', info.get('forwardPE', 0))
            info['priceToBook'] = naver_info.get('priceToBook', info.get('priceToBook', 0))
            info['dividendYield'] = naver_info.get('dividendYield', info.get('dividendYield', 0))
            info['sector'] = naver_info.get('sector', '한국 주
