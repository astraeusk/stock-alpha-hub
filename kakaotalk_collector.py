"""
KakaoTalk Message Collector & Webhook Forwarder for AlphaHub
============================================================
이 스크립트는 PC 카카오톡 텍스트 클립보드/로그 파일 또는 웹훅을 감지하여
AlphaHub의 /api/kakaotalk/ingest 엔드포인트로 주식 리포트 및 지라시 정보를 자동으로 전송합니다.
"""

import sys
import time
import requests
import re

SERVER_URL = "http://127.0.0.1:5000/api/kakaotalk/ingest"

def send_to_alphahub(raw_text, sender="PC 카카오톡 자동 수집기"):
    payload = {
        "text": raw_text,
        "sender": sender
    }
    try:
        response = requests.post(SERVER_URL, json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"[SUCCESS] AlphaHub 수집 완료: {result.get('message')}")
            return True
        else:
            print(f"[ERROR] 서버 응답 에러: {response.status_code}")
            return False
    except Exception as e:
        print(f"[EXCEPTION] AlphaHub 연결 실패: {e}")
        return False

def sample_ingest_demo():
    print("=== 카카오톡 자동 수집 데모 실행 중 ===")
    sample_texts = [
        "TSLA 테슬라 로보택시 행사 일정 확정. FSD v13 승인 가능성에 밤사이 주가 +6.8% 상향.",
        "삼성전자(005930) 파운드리 2나노 수주 계약 공시. 목표주가 95,000원 신규 리포트 발행."
    ]
    for text in sample_texts:
        send_to_alphahub(text, sender="카톡방 - 글로벌주식채널")
        time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw_input = " ".join(sys.argv[1:])
        send_to_alphahub(raw_input)
    else:
        sample_ingest_demo()
