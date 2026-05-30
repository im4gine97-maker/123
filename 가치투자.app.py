import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time

st.set_page_config(layout="wide")

def tr(text):
    if not text: return text
    try:
        gt = GoogleTranslator(source='en', target='ko')
        return gt.translate(text[:1000])
    except:
        return text

def get_nv(code):
    url = "https://finance.naver.com/item/main.naver"
    url += "?code=" + code
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
    code = tk.split('.')[0] if kr else tk
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
        nv = get_nv(code)
        if nv:
            if 'name' in nv: 
                i['shortName'] = nv['name']
            if 'pe' in nv: 
                i['trailingPE'] = nv['pe']
            if 'fpe' in nv: 
                i['forwardPE'] = nv['fpe']
            if 'pbr' in nv: 
                i['priceToBook'] = nv['pbr']
            if 'div' in nv: 
                i['dividendYield'] = nv['div']
            if 'sum' in nv: 
                i['kr_sum'] = nv['sum']
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
        if not fcf or fcf <= 0: return
