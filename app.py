import os
import re
import json
import time
import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Allowed 10 Whitelisted Users Simulation
WHITELIST_USERS = {
    "admin@alpha.com": {"name": "우성교 (Master)", "role": "admin", "pass": "alpha123"},
    "user1@alpha.com": {"name": "투자자 A", "role": "member", "pass": "invest1"},
    "user2@alpha.com": {"name": "투자자 B", "role": "member", "pass": "invest2"}
}

# Watchlist Data Storage (Domestic & International)
WATCHLIST = [
    {
        "ticker": "NVDA",
        "name": "엔비디아",
        "market": "international", # 'domestic' | 'international'
        "currency": "USD",
        "price": 128.50,
        "change_pct": "+2.4%",
        "sector": "AI 반도체",
        "memo": "블랙웰 램프업 및 HBM3e 데이터센터 공급 확대 모니터링"
    },
    {
        "ticker": "AAPL",
        "name": "애플",
        "market": "international",
        "currency": "USD",
        "price": 218.20,
        "change_pct": "-4.2%",
        "sector": "빅테크 하드웨어/서비스",
        "memo": "중국 유통망 우려 및 Apple Intelligence 기기 교체주기 추적"
    },
    {
        "ticker": "000660",
        "name": "SK하이닉스",
        "market": "domestic",
        "currency": "KRW",
        "price": 178500,
        "change_pct": "+1.8%",
        "sector": "국내 메모리/HBM",
        "memo": "HBM3e 독점 수율 우위 및 환율 상승 수혜주"
    },
    {
        "ticker": "005930",
        "name": "삼성전자",
        "market": "domestic",
        "currency": "KRW",
        "price": 74500,
        "change_pct": "+0.5%",
        "sector": "국내 반도체/파운드리",
        "memo": "HBM3e 12단 퀄테스트 통과 및 2나노 파운드리 수주 점검"
    }
]

# In-memory storage for KakaoTalk Ingested Messages
KAKAOTALK_MESSAGES = [
    {
        "id": 1,
        "sender": "카톡방 - 주식분석방",
        "time": "2026-08-06 09:15",
        "raw": "NVDA 엔비디아 이번 2분기 블랙웰 출하량 가이던스 상향 가능성 언급됨. 목표주가 $150 제시 리포트 나옴.",
        "tickers": ["NVDA"],
        "market": "international",
        "sentiment": "호재",
        "summary": "엔비디아 블랙웰 출하 가이던스 상향 기대감 & 목표가 $150 상향",
        "action": "가격 판독기(Reverse DCF)로 $150 반영 성장률 추정 필요"
    },
    {
        "id": 2,
        "sender": "카톡방 - 반도체&전력",
        "time": "2026-08-06 10:30",
        "raw": "SK하이닉스(000660) HBM3e 공급계약 확대 공시 뜸. 환율 1,385원 상승 효과 반영 시 분기 영업이익 최고치 예상.",
        "tickers": ["000660", "SK하이닉스"],
        "market": "domestic",
        "sentiment": "호재",
        "summary": "SK하이닉스 HBM3e 공급계약 확대 및 환율 상승 수혜 예상",
        "action": "스토리 리더로 공시 톤 변화 점검"
    },
    {
        "id": 3,
        "sender": "카톡방 - 글로벌마켓일지",
        "time": "2026-08-06 14:20",
        "raw": "AAPL 애플 아이폰 17 중국 유통망 수요가 예상보다 약하다는 민감 뉴스 있음. 밤사이 주가 -4.2% 하락.",
        "tickers": ["AAPL"],
        "market": "international",
        "sentiment": "악재",
        "summary": "애플 중국 유통망 우려로 주가 -4.2% 하락",
        "action": "가격 판독기(Reverse DCF)로 안전마진 재평가 필요"
    }
]

# Stock Database for 2nd Layer Deep Dive
STOCK_DECODER_DATA = {
    "NVDA": {
        "name": "NVIDIA Corporation",
        "ticker": "NVDA",
        "market": "international",
        "price": 128.50,
        "currency": "USD",
        "segment_revenue": [
            {"segment": "Compute & Networking (Data Center)", "share": 87, "amount": 26200},
            {"segment": "Graphics (Gaming & ProViz)", "share": 10, "amount": 3000},
            {"segment": "Automotive & Robotics", "share": 3, "amount": 900}
        ],
        "geo_revenue": [
            {"region": "United States", "share": 44},
            {"region": "Taiwan", "share": 22},
            {"region": "China (incl. HK)", "share": 14},
            {"region": "Other International", "share": 20}
        ],
        "business_model": "가속 연산(GPU) 및 CUDA 소프트웨어 생태계를 기반으로 AI 데이터센터 서버용 칩셋 공급. 매출의 87%가 AI 컴퓨팅에서 발생.",
        "kpis": [
            {"name": "데이터센터 매출 성장률 (YoY)", "value": "+427%", "status": "최상"},
            {"name": "매출총이익률 (Gross Margin)", "value": "78.4%", "status": "최상"},
            {"name": "블랙웰(Blackwell) 램프업 속도", "value": "4분기 양산", "status": "양호"}
        ],
        "source_doc": "NVIDIA FY2025 Q1 10-Q (p.18-24)"
    },
    "AAPL": {
        "name": "Apple Inc.",
        "ticker": "AAPL",
        "market": "international",
        "price": 218.20,
        "currency": "USD",
        "segment_revenue": [
            {"segment": "iPhone", "share": 52, "amount": 45963},
            {"segment": "Services (AppStore, iCloud, Pay)", "share": 28, "amount": 23867},
            {"segment": "Wearables, Home & Accessories", "share": 8, "amount": 7913},
            {"segment": "Mac & iPad", "share": 12, "amount": 10842}
        ],
        "geo_revenue": [
            {"region": "Americas", "share": 42},
            {"region": "Europe", "share": 25},
            {"region": "Greater China", "share": 17},
            {"region": "Japan & Rest of Asia", "share": 16}
        ],
        "business_model": "하드웨어(iPhone/Mac) 디바이스 하이엔드 잠금 효과(Lock-in)를 바탕으로 마진율 74%의 고수익 서비스 부문 가입자 확대.",
        "kpis": [
            {"name": "Services ARR 성장률", "value": "+14.2%", "status": "양호"},
            {"name": "활성 디바이스 (Active Installed Base)", "value": "22억 대", "status": "최상"},
            {"name": "중국 시장 iPhone 매출 (YoY)", "value": "-8.1%", "status": "주의"}
        ],
        "source_doc": "Apple Inc. Q3 FY24 Form 10-Q (Item 2, p.29)"
    },
    "000660": {
        "name": "SK하이닉스",
        "ticker": "000660",
        "market": "domestic",
        "price": 178500,
        "currency": "KRW",
        "segment_revenue": [
            {"segment": "DRAM (HBM3e / LPDDR5X 포함)", "share": 68, "amount": 108000},
            {"segment": "NAND Flash (eSSD 포함)", "share": 29, "amount": 46000},
            {"segment": "기타 및 모듈", "share": 3, "amount": 4800}
        ],
        "geo_revenue": [
            {"region": "해외 (미국/대만/중국)", "share": 89},
            {"region": "내수 (한국)", "share": 11}
        ],
        "business_model": "AI 가속기 전용 고대역폭 메모리(HBM) 독점적 기술 우위를 바탕으로 글로벌 반도체 빅테크 공급. DRAM 매출 중 HBM 비중 30% 돌파.",
        "kpis": [
            {"name": "HBM3e 수율 및 출하 비중", "value": "DRAM 매출의 32%", "status": "최상"},
            {"name": "기업용 SSD(eSSD) 영업이익률", "value": "35%", "status": "양호"},
            {"name": "설비투자(CAPEX) 집행률", "value": "EBITDA 대비 42%", "status": "중립"}
        ],
        "source_doc": "SK하이닉스 2024년 2분기 분기보고서 (사업의 내용 p.45)"
    },
    "005930": {
        "name": "삼성전자",
        "ticker": "005930",
        "market": "domestic",
        "price": 74500,
        "currency": "KRW",
        "segment_revenue": [
            {"segment": "DS (반도체 - DRAM/NAND/파운드리)", "share": 44, "amount": 110000},
            {"segment": "DX (스마트폰/가전/TV)", "share": 48, "amount": 120000},
            {"segment": "SDC (디스플레이 OLED)", "share": 8, "amount": 20000}
        ],
        "geo_revenue": [
            {"region": "미국/아메리카", "share": 38},
            {"region": "중국", "share": 28},
            {"region": "아시아/유럽", "share": 22},
            {"region": "한국 내수", "share": 12}
        ],
        "business_model": "메모리 반도체 세계 1위 사업자 및 스마트폰/가전 종합 IT 기업. HBM3e 12단 공급 퀄테스트 추진 중.",
        "kpis": [
            {"name": "DRAM 1a/1b 비중", "value": "62%", "status": "양호"},
            {"name": "스마트폰 MX 부문 영업이익률", "value": "11.5%", "status": "양호"},
            {"name": "파운드리 가동률", "value": "65%", "status": "중립"}
        ],
        "source_doc": "삼성전자 2024년 2분기 반기보고서 (p.32)"
    }
}

STORY_READER_DATA = {
    "AAPL": {
        "ticker": "AAPL",
        "market": "international",
        "period": "2022 ~ 2025 (3개년 공시 및 어닝콜)",
        "tone_changes": [
            {
                "topic": "중국 시장 가이던스 표현",
                "old_text": "2023 10-K: '중국 시장의 강력한 프리미엄 수요 지속 확신(robust premium demand)'",
                "new_text": "2024 10-K: '중국 거시경제적 환경의 불확실성이 매출에 영향을 줄 수 있음(may impact revenue)'",
                "shift": "Tone-Down (확신 → 불확실성 언급)",
                "significance": "중요"
            },
            {
                "topic": "Apple Intelligence (AI 기능)",
                "old_text": "2022 콘퍼런스콜: '머신러닝 기술을 기능 고도화에 지속 적용하고 있습니다'",
                "new_text": "2024 어닝콜: '애플 인텔리전스는 기기 교체 주기(Supercycle)를 유도할 핵심 동력'",
                "shift": "New-Focus (생성형 AI 전면 내세움)",
                "significance": "핵심"
            }
        ],
        "guidance_track_record": [
            {"quarter": "2023 Q4", "promised": "Services 부문 두 자릿수 성장", "actual": "+16% 달성", "result": "초과 달성"},
            {"quarter": "2024 Q1", "promised": "iPhone 매출 전년 대비 보합", "actual": "-0.9% 기록", "result": "부합"},
            {"quarter": "2024 Q2", "promised": "전사 매출 싱글 디짓 성장", "actual": "+4.9% 기록", "result": "부합"}
        ]
    },
    "NVDA": {
        "ticker": "NVDA",
        "market": "international",
        "period": "2023 ~ 2025 (3개년 공시 및 어닝콜)",
        "tone_changes": [
            {
                "topic": "대중국 수출 규제 비중",
                "old_text": "2023 10-K: '중국 시장 매출 비중 20~25% 수준 유지 예상'",
                "new_text": "2024 10-K: '미정부 수출 통제 강화로 중국 특화 칩셋 매출 지속 제한'",
                "shift": "Risk Escalation (수출 통제 리스크 상시화)",
                "significance": "중요"
            }
        ],
        "guidance_track_record": [
            {"quarter": "2024 Q1", "promised": "매출 $240억 ± 2%", "actual": "$260억 기록", "result": "8% 초과"}
        ]
    },
    "000660": {
        "ticker": "000660",
        "market": "domestic",
        "period": "2022 ~ 2025 (국내 분기보고서 및 IR)",
        "tone_changes": [
            {
                "topic": "HBM 수율 및 공급 언급",
                "old_text": "2023 Q2 IR: 'HBM3 기술적 검증 완료 및 샘플 공급 중'",
                "new_text": "2024 Q2 IR: 'HBM3e 8단 독점 공급 확고 및 12단 내년 상반기 공급 가시화'",
                "shift": "Monopoly Confirmed (시장 지배력 공고화)",
                "significance": "핵심"
            }
        ],
        "guidance_track_record": [
            {"quarter": "2024 Q2", "promised": "HBM 매출 전분기 대비 80% 이상 증가", "actual": "+89% 증가", "result": "초과 달성"}
        ]
    }
}

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if email in WHITELIST_USERS and WHITELIST_USERS[email]['pass'] == password:
        user_info = WHITELIST_USERS[email]
        return jsonify({
            "success": True,
            "token": f"auth_token_{int(time.time())}_{email}",
            "user": {
                "email": email,
                "name": user_info['name'],
                "role": user_info['role']
            },
            "capacity": "10인 허용 화이트리스트 접근 가능"
        })
    return jsonify({"success": False, "message": "등록되지 않은 화이트리스트 계정이거나 비밀번호가 일치하지 않습니다."}), 401

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    market_filter = request.args.get('market', 'all')
    if market_filter in ['domestic', 'international']:
        filtered = [item for item in WATCHLIST if item['market'] == market_filter]
        return jsonify(filtered)
    return jsonify(WATCHLIST)

@app.route('/api/watchlist/add', methods=['POST'])
def add_watchlist():
    data = request.json or {}
    ticker = data.get('ticker', '').strip().upper()
    name = data.get('name', '').strip()
    market = data.get('market', 'international') # 'domestic' or 'international'
    sector = data.get('sector', '기타').strip()
    memo = data.get('memo', '').strip()
    price = float(data.get('price', 100.0))

    if not ticker or not name:
        return jsonify({"success": False, "message": "티커와 종목명은 필수입니다."}), 400

    # Check if already exists
    for item in WATCHLIST:
        if item['ticker'] == ticker:
            item['name'] = name
            item['market'] = market
            item['sector'] = sector
            item['memo'] = memo
            item['price'] = price
            return jsonify({"success": True, "message": f"[{ticker}] 종목 정보가 갱신되었습니다.", "watchlist": WATCHLIST})

    new_item = {
        "ticker": ticker,
        "name": name,
        "market": market,
        "currency": "KRW" if market == "domestic" else "USD",
        "price": price,
        "change_pct": "0.0%",
        "sector": sector,
        "memo": memo
    }
    WATCHLIST.append(new_item)
    return jsonify({"success": True, "message": f"[{name} ({ticker})] 관심 종목에 추가되었습니다.", "watchlist": WATCHLIST})

@app.route('/api/watchlist/delete/<ticker>', methods=['DELETE'])
def delete_watchlist(ticker):
    ticker_upper = ticker.upper()
    global WATCHLIST
    WATCHLIST = [item for item in WATCHLIST if item['ticker'] != ticker_upper]
    return jsonify({"success": True, "message": f"[{ticker_upper}] 종목이 삭제되었습니다.", "watchlist": WATCHLIST})

@app.route('/api/briefing', methods=['GET'])
def get_briefing():
    market_filter = request.args.get('market', 'all')
    
    triggers = [
        {
            "ticker": "AAPL",
            "name": "애플",
            "market": "international",
            "reason": "밤사이 주가 -4.2% 급락 & 중국 유통망 수요 경고",
            "recommended_skill": "가격 판독기 (Price Decoder)",
            "action_desc": "Reverse DCF로 현재 하락 주가 반영 필요 성장률 역산 점검"
        },
        {
            "ticker": "000660",
            "name": "SK하이닉스",
            "market": "domestic",
            "reason": "카톡 정보 수집기에서 HBM3e 공급 확대 호재 포착 & 환율 수혜",
            "recommended_skill": "스토리 리더 (Story Reader)",
            "action_desc": "최근 3개년 공시 문구 및 어닝콜 가이던스 변화 추적"
        },
        {
            "ticker": "NVDA",
            "name": "엔비디아",
            "market": "international",
            "reason": "카톡 추천 리포트 목표가 $150 상향 소식 입수",
            "recommended_skill": "기업 해독기 (Company Decoder)",
            "action_desc": "데이터센터 사업부 매출 비중 및 10-Q 세부 검증"
        },
        {
            "ticker": "005930",
            "name": "삼성전자",
            "market": "domestic",
            "reason": "국내 2나노 파운드리 수주 공시 및 HBM 12단 퀄테스트 임박",
            "recommended_skill": "기업 해독기 (Company Decoder)",
            "action_desc": "DS 부문 반도체 마진율 및 수율 지표 체크"
        }
    ]

    if market_filter in ['domestic', 'international']:
        triggers = [t for t in triggers if t['market'] == market_filter]

    return jsonify({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "macro": {
            "usdkrw": {"value": 1384.50, "change": "+4.20", "status": "환율 상승 (수출주 수혜 / 원자재 부담)"},
            "sp500": {"value": 5420.10, "change": "+0.45%", "status": "해외 강보합"},
            "nasdaq": {"value": 17150.80, "change": "+0.82%", "status": "해외 빅테크 반등"},
            "kospi": {"value": 2680.40, "change": "-0.15%", "status": "국내 기관 순매도"},
            "kosdaq": {"value": 855.20, "change": "+0.32%", "status": "국내 바이오 반등"}
        },
        "action_triggers": triggers,
        "portfolio_summary": {
            "total_value_krw": "452,300,000 원",
            "domestic_value_krw": "98,400,000 원 (22%)",
            "international_value_krw": "353,900,000 원 (78%)",
            "daily_pnl_krw": "+3,850,000 원 (+0.86%)",
            "hhi_index": 0.22,
            "hhi_status": "적정 분산 (HHI < 0.25)"
        }
    })

@app.route('/api/portfolio/cockpit', methods=['GET'])
def get_portfolio_cockpit():
    market_filter = request.args.get('market', 'all')
    
    asset_alloc = [
        {"type": "미국 개별 빅테크 (NVDA, AAPL)", "market": "international", "weight": 46, "fundamental_eval": "펀더멘털 & 역DCF 가능"},
        {"type": "미국 지수 ETF (QQQ, SPY)", "market": "international", "weight": 32, "fundamental_eval": "지수 총계 밸류에이션"},
        {"type": "국내 반도체 (SK하이닉스, 삼성전자)", "market": "domestic", "weight": 14, "fundamental_eval": "어닝콜 & HBM 수율 추적"},
        {"type": "금/원자재 ETF (GLD)", "market": "international", "weight": 8, "fundamental_eval": "실질금리 & 달러 인덱스 연동"}
    ]

    if market_filter in ['domestic', 'international']:
        asset_alloc = [a for a in asset_alloc if a['market'] == market_filter]

    return jsonify({
        "hhi": {
            "score": 0.218,
            "evaluation": "안정적 분산 (Safe Diversification)",
            "desc": "해외 자산(78%) 및 국내 자산(22%)이 균형 있게 배분됨."
        },
        "etf_overlap": [
            {
                "holding_etf": "QQQ (Invesco QQQ Trust)",
                "market": "international",
                "overlapping_single_stock": "NVDA, AAPL, MSFT",
                "effective_nvda_weight": "개별주 28% + QQQ 경유 2.1% = 실질 노출 30.1%",
                "effective_aapl_weight": "개별주 18% + QQQ 경유 2.2% = 실질 노출 20.2%",
                "alert": "해외 기술주 비중이 높아 나스닥 지수 변동성에 민감함."
            }
        ],
        "asset_allocation": asset_alloc
    })

@app.route('/api/stock/decoder/<ticker>', methods=['GET'])
def get_stock_decoder(ticker):
    ticker_upper = ticker.upper()
    data = STOCK_DECODER_DATA.get(ticker_upper)
    if not data:
        data = {
            "name": f"{ticker_upper} Corp",
            "ticker": ticker_upper,
            "market": "domestic" if ticker_upper.isdigit() else "international",
            "price": 100.0,
            "currency": "KRW" if ticker_upper.isdigit() else "USD",
            "segment_revenue": [{"segment": "주력 주 사업부", "share": 100, "amount": 10000}],
            "geo_revenue": [{"region": "글로벌/내수", "share": 100}],
            "business_model": "신규 관심 종목 데이터 로딩 완료. 사업 구조 세부 해독 지원.",
            "kpis": [{"name": "매출 성장률 (YoY)", "value": "+12%", "status": "양호"}],
            "source_doc": "공시 보고서 (Form 10-K / 사업보고서)"
        }
    return jsonify(data)

@app.route('/api/stock/story/<ticker>', methods=['GET'])
def get_stock_story(ticker):
    ticker_upper = ticker.upper()
    data = STORY_READER_DATA.get(ticker_upper)
    if not data:
        data = {
            "ticker": ticker_upper,
            "market": "domestic" if ticker_upper.isdigit() else "international",
            "period": "최근 2개년 공시 및 어닝콜",
            "tone_changes": [
                {
                    "topic": "실적 모멘텀 표현",
                    "old_text": "전년도: '지속적인 두 자릿수 성장을 기대합니다'",
                    "new_text": "금년도: '시장 불확실성에 대응하며 안정적인 수익성을 유지합니다'",
                    "shift": "Tone-Down",
                    "significance": "중요"
                }
            ],
            "guidance_track_record": [
                {"quarter": "최근 분기", "promised": "가이던스 부합", "actual": "달성", "result": "부합"}
            ]
        }
    return jsonify(data)

@app.route('/api/stock/price-decoder', methods=['POST'])
def calculate_reverse_dcf():
    req = request.json or {}
    ticker = req.get('ticker', 'AAPL')
    price = float(req.get('price', 218.20))
    fcf = float(req.get('fcf', 108.0))
    shares = float(req.get('shares', 15.3))
    wacc = float(req.get('wacc', 9.0)) / 100.0
    terminal_g = float(req.get('terminal_g', 3.0)) / 100.0
    years = 10

    market_cap = price * shares
    low_g, high_g = -0.50, 1.00

    for _ in range(50):
        mid_g = (low_g + high_g) / 2.0
        pv_fcf = 0.0
        cur_cash = fcf
        for t in range(1, years + 1):
            cur_cash *= (1 + mid_g)
            pv_fcf += cur_cash / ((1 + wacc) ** t)
        
        terminal_val = (cur_cash * (1 + terminal_g)) / (wacc - terminal_g)
        pv_tv = terminal_val / ((1 + wacc) ** years)
        total_pv = pv_fcf + pv_tv

        if total_pv > market_cap:
            high_g = mid_g
        else:
            low_g = mid_g
    
    implied_g = (low_g + high_g) / 2.0 * 100.0
    past_cagr = 11.2 if ticker == 'AAPL' else (28.5 if ticker == 'NVDA' else 14.0)
    gap = implied_g - past_cagr

    matrix = []
    for w in [wacc - 0.01, wacc, wacc + 0.01]:
        row = []
        for tg in [terminal_g - 0.005, terminal_g, terminal_g + 0.005]:
            l_g, h_g = -0.50, 1.00
            for _ in range(30):
                mg = (l_g + h_g) / 2.0
                pv = 0.0
                c = fcf
                for t in range(1, years + 1):
                    c *= (1 + mg)
                    pv += c / ((1 + w) ** t)
                tv = (c * (1 + tg)) / (w - tg)
                pv += tv / ((1 + w) ** years)
                if pv > market_cap: h_g = mg
                else: l_g = mg
            row.append(round((l_g + h_g) / 2.0 * 100.0, 1))
        matrix.append({"wacc": f"{w*100:.1f}%", "rates": row})

    return jsonify({
        "ticker": ticker,
        "current_price": price,
        "market_cap_billion": round(market_cap, 1),
        "implied_annual_growth": round(implied_g, 2),
        "past_5y_cagr": past_cagr,
        "gap": round(gap, 2),
        "evaluation_summary": f"현재 주가 ${price:.2f}가 성립하려면 회사가 향후 10년간 매년 연 {implied_g:.1f}%의 FCF 성장을 달성해야 합니다. (과거 5년 실제 성장은 {past_cagr}%였습니다)",
        "safety_assessment": "적정가 반영" if gap < 2.0 else ("과열 경고 (고성장 요구됨)" if gap > 5.0 else "성장 동인 요구됨"),
        "sensitivity_matrix": matrix,
        "wacc_used": f"{wacc*100:.1f}%",
        "terminal_g_used": f"{terminal_g*100:.1f}%"
    })

@app.route('/api/kakaotalk/ingest', methods=['POST'])
def ingest_kakaotalk():
    data = request.json or {}
    raw_text = data.get('text', '').strip()
    sender = data.get('sender', '카카오톡 수집기')
    
    if not raw_text:
        return jsonify({"success": False, "message": "수집할 텍스트가 비어있습니다."}), 400

    ticker_match = re.findall(r'[A-Z]{2,5}|\b\d{6}\b', raw_text)
    unique_tickers = list(set(ticker_match))

    market = "domestic" if any(t.isdigit() for t in unique_tickers) or "삼성" in raw_text or "하이닉스" in raw_text or "카카오" in raw_text else "international"
    sentiment = "호재" if any(w in raw_text for w in ["상향", "증가", "급등", "호실적", "계약", "수혜"]) else ("악재" if any(w in raw_text for w in ["하락", "감소", "급락", "우려", "경고", "손실"]) else "중립")

    new_msg = {
        "id": len(KAKAOTALK_MESSAGES) + 1,
        "sender": sender,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "raw": raw_text,
        "tickers": unique_tickers if unique_tickers else ["관심종목"],
        "market": market,
        "sentiment": sentiment,
        "summary": raw_text[:60] + "..." if len(raw_text) > 60 else raw_text,
        "action": f"{unique_tickers[0] if unique_tickers else '해당 종목'} 온디맨드 딥다이브 연동 추천"
    }

    KAKAOTALK_MESSAGES.insert(0, new_msg)
    return jsonify({"success": True, "message": "카톡 정보가 성공적으로 수집되어 일일 브리핑에 반영되었습니다.", "item": new_msg})

@app.route('/api/kakaotalk/messages', methods=['GET'])
def get_kakaotalk_messages():
    market_filter = request.args.get('market', 'all')
    if market_filter in ['domestic', 'international']:
        filtered = [m for m in KAKAOTALK_MESSAGES if m['market'] == market_filter]
        return jsonify(filtered)
    return jsonify(KAKAOTALK_MESSAGES)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"★ Stock Alpha Hub Server running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
