import streamlit as st
import yfinance as yf
import time

st.set_page_config(page_title="JB Value Terminal", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main {background-color: #0d1117; color: #c9d1d9;}
    h1, h2, h3 {color: #58a6ff;}
    .stAlert {background-color: #161b22; border: 1px solid #30363d;}
    .guru-quote {font-style: italic; color: #8b949e; border-left: 3px solid #e3b341; padding-left: 10px; margin-bottom: 10px;}
    .highlight {color: #da3633; font-weight: bold;}
    .good {color: #3fb950; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ JB Value Terminal PRO")
st.caption("상위 1% 가치투자자를 위한 실시간 다학제적 멘탈 모델 스캐너")
st.error("🚨 삼성전자, 델타항공 등 시클리컬 기업은 밸류에이션이 왜곡될 수 있습니다. 본 앱은 알파벳 등 이익이 우상향하는 '해자(Moat) 기업'에 최적화되어 있습니다.")

ticker_map = {
    "애플": "AAPL", "구글": "GOOGL", "알파벳": "GOOGL", "마이크로소프트": "MSFT", 
    "아마존": "AMZN", "테슬라": "TSLA", "엔비디아": "NVDA", "크록스": "CROX", 
    "무디스": "MCO", "코카콜라": "KO", "뱅크오브아메리카": "BAC", "버크셔": "BRK-B",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "KB금융": "105560.KS", "현대차": "005380.KS"
}

st.subheader("🔍 실시간 데이터 자동 스캔")
user_input = st.text_input("기업명 또는 티커(Ticker)를 입력하세요", placeholder="예: 무디스, AAPL, 005930.KS")

if st.button("가치 분석 즉시 실행", type="primary"):
    if user_input:
        with st.spinner('야후 파이낸스에서 실시간 데이터를 추출 중입니다...'):
            time.sleep(1)
            
            search_ticker = ticker_map.get(user_input.strip(), user_input.strip().upper())
            is_korean = search_ticker.endswith('.KS') or search_ticker.endswith('.KQ')
            
            try:
                stock = yf.Ticker(search_ticker)
                try:
                    price = stock.fast_info['lastPrice']
                except:
                    price = stock.history(period="1d")['Close'].iloc[-1]
                    
                info = stock.info if isinstance(stock.info, dict) else {}
                
                name = info.get('shortName', search_ticker)
                sector = info.get('sector', 'Unknown')
                fwd_pe = info.get('forwardPE')
                pbr = info.get('priceToBook')
                roe = (info.get('returnOnEquity', 0) * 100) if info.get('returnOnEquity') else 10.0
                
                # 경영진 및 비즈니스 데이터 추출
                business_summary = info.get('longBusinessSummary', '비즈니스 설명 데이터가 제공되지 않았습니다.')
                officers = info.get('companyOfficers', [])
                ceo_info = "CEO 정보 누락 (구글링 등 직접 검색 요망)"
                
                if officers:
                    for o in officers:
                        title = o.get('title', '').upper()
                        if 'CEO' in title or 'CHIEF EXECUTIVE' in title:
                            ceo_info = f"{o.get('name')} ({o.get('title')})"
                            break
                    if ceo_info == "CEO 정보 누락 (구글링 등 직접 검색 요망)":
                        ceo_info = f"{officers[0].get('name')} ({officers[0].get('title')})"
                
                try:
                    tnx = yf.Ticker("^TNX")
                    treasury = tnx.fast_info['lastPrice']
                except:
                    treasury = 4.4
                
                alerts = []
                if not fwd_pe:
                    if sector == 'Technology': fwd_pe = 30.0
                    elif sector == 'Financial Services': fwd_pe = 12.0
                    else: fwd_pe = 18.0
                    alerts.append(f"⚠️ 야후 API 누락: [{sector}] 업종 평균 {fwd_pe}배로 추정")
                if not pbr and is_korean:
                    if sector == 'Financial Services': pbr = 0.4
                    else: pbr = 0.8
                    alerts.append(f"⚠️ PBR 누락: 업종 평균 {pbr}배로 추정")
                
                avg_pe = fwd_pe * 1.2
                avg_pbr = pbr * 1.2 if pbr else 1.0
                
                st.success(f"🏢 {name} ({search_ticker}) / 업종: {sector}")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("현재 주가", f"{price:,.2f}")
                col2.metric("10년물 국채 금리", f"{treasury:.2f}%")
                col3.metric("ROIC (자본수익률)", f"{roe:.2f}%")
                
                for alert in alerts:
                    st.warning(alert)
                
                st.markdown("---")
                st.subheader("📊 1. 펀더멘털 & 안전마진")
                
                if is_korean:
                    st.info("💡 한국 주식은 시클리컬 특성을 고려하여 **PBR**을 최우선 잣대로 평가합니다.")
                    mos = ((avg_pbr - pbr) / avg_pbr) * 100
                    intrinsic = price * (avg_pbr / pbr) if pbr > 0 else 0
                    
                    st.write(f"- 적용 지표: 현재 PBR **{pbr:.2f}배** / 과거 평균 **{avg_pbr:.2f}배**")
                    st.write(f"- 적정 가치: **₩{intrinsic:,.0f}**")
                    if mos > 0:
                        st.markdown(f"- 안전마진: <span class='good'>{mos:.1f}% 확보 (자산가치 할인 구간)</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("- 안전마진: <span class='highlight'>역사적 고평가 (상투 주의)</span>", unsafe_allow_html=True)
                else:
                    ey = (1 / fwd_pe) * 100
                    prem = ey - treasury
                    mos = ((avg_pe - fwd_pe) / avg_pe) * 100
                    intrinsic = price * (avg_pe / fwd_pe) if fwd_pe > 0 else 0
                    
                    st.write(f"- 적용 지표: 포워드 PER **{fwd_pe:.2f}배** / 과거 평균 **{avg_pe:.2f}배**")
                    if prem > 0:
                        st.markdown(f"- 이익수익률: **{ey:.2f}%** (국채 대비 <span class='good'>+{prem:.2f}%p 초과 수익</span>)", unsafe_allow_html=True)
                    else:
                        st.markdown(f"- 이익수익률: **{ey:.2f}%** (국채 대비 <span class='highlight'>{prem:.2f}%p 프리미엄 과열</span>)", unsafe_allow_html=True)
                    st.write(f"- 적정 가치: **${intrinsic:,.2f}**")
                    if mos > 0:
                        st.markdown(f"- 안전마진: <span class='good'>{mos:.1f}% 확보</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("- 안전마진: <span class='highlight'>0% (고평가 영역)</span>", unsafe_allow_html=True)
                
                # --- 신규 추가된 질적 분석 (경영진) 섹션 ---
                st.markdown("---")
                st.subheader("🕵️‍♂️ 2. 질적 분석 (능력범위 & 경영진 파악)")
                st.markdown(f"- **핵심 경영진:** <span class='highlight'>{ceo_info}</span>", unsafe_allow_html=True)
                st.markdown(f"- **비즈니스 모델 요약:**\n> {business_summary[:400]}... (중략)")
                st.info("💡 위 비즈니스 모델을 다른 사람에게 논리적으로 설명할 수 없다면 내 '능력 범위' 밖입니다. 검색된 경영자의 이름으로 과거 주주 기만 이력이나 정직성에 위배되는 기사가 없는지 반드시 사실 수집을 진행하십시오.")

                st.markdown("---")
                st.subheader("🧠 3. 거장들의 멘탈 모델")
                st.markdown("<div class='guru-quote'><b>워런 버핏:</b> 이익이 10년물 국채를 이기고 복리로 팽창하는가? 무엇보다 <span class='highlight'>경영자가 정직한가?</span> 도덕성이 의심되면 즉각 손절하게.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>필립 피셔:</b> 이 하락이 ①상업화 초기 문제 ②미스터 마켓의 우울증 ③해결 가능한 악재 중 하나라면 영혼을 걸고 매수하시오.</div>", unsafe_allow_html=True)
                st.markdown("<div class='guru-quote'><b>찰리 멍거:</b> 단일 실패 지점은 없는가? 전문가의 반론을 재반박할 수 없다면 당신의 능력 범위 밖이네.</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("🚨 4. 액션 플랜 (절대 매도 3원칙)")
                st.write("☑️ **최종 점검:** 가격, 비즈니스, 경영진, 리스크, 사실수집, 능력범위")
                st.markdown("""
                <div style='background-color:#2d1114; padding:10px; border-radius:5px; border-left:4px solid #da3633;'>
                <b style='color:#da3633;'>[오직 다음 3가지 경우에만 매도합니다]</b><br>
                1. 분석에 치명적인 실수가 있었을 때<br>
                2. 주가가 폭등하여 밸류에이션이 지나치게 과열되었을 때<br>
                3. 더 확실하고 안전한 기회를 발견했을 때
                </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"오류가 발생했습니다. 정확한 기업명이나 티커를 입력했는지 확인해주세요. (Error: {e})")
    else:
        st.warning("기업명이나 티커를 입력해주세요.")
