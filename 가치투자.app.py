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
    url = "https://finance.naver.com/item/main.naver?code=" + code
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers)
        s = BeautifulSoup(r.text, 'html.parser')
        i = {}
        
        name_tag = s.select_one('.wrap_company h2 a')
        if name_tag: i['name'] = name_tag.text
        
        per
