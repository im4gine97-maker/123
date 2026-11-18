import os
import sys
import time
import subprocess
import webview

def start_agie_program():
    # 1. 현재 폴더의 가치투자.app.py 경로 확인
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(base_dir, "가치투자.app.py")

    # 2. 스트림릿 서버를 백그라운드에서 실행 (메모리 및 업로드 용량 제한 2000MB로 완전 해제!)
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.headless=true",
        "--server.port=8505",
        "--server.maxUploadSize=2000",
        "--server.maxMessageSize=2000",
        "--browser.gatherUsageStats=false"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 서버가 켜질 때까지 2.5초 대기
    time.sleep(2.5)

    # 3. 크롬 브라우저 대신 깔끔한 독립 PC 프로그램(게임 창 형태)으로 실행!
    webview.create_window(
        title="AGIE PRO — 워런 버핏 10년 장부 & 다큐멘터리 스튜디오",
        url="http://localhost:8505",
        width=1600,
        height=940,
        resizable=True
    )
    webview.start()

    # 4. 프로그램 창을 닫으면 백그라운드 서버도 깔끔하게 자동 종료
    proc.terminate()

if __name__ == "__main__":
    start_agie_program()
