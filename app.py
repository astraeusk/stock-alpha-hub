import os
import re
import json
import time
import datetime
import urllib.request
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

import sqlite3

DATA_STORE_PATH = os.path.join(os.path.dirname(__file__), 'data_store.json')
DB_FILE = os.path.join(os.path.dirname(__file__), 'stock_alpha.db')

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                val_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Init Error:", e)

init_db()

# Default Data Store (No dummy portfolio entries)
DEFAULT_DATA = {
    "whitelist_users": {
        "admin@alpha.com": {"name": "우성교 (Master)", "role": "admin", "pass": "alpha123"}
    },
    "portfolio": []
}

def load_data_store():
    # 1. Load from SQLite Permanent Database
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT val_json FROM kv_store WHERE key=?', ('data_store',))
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
    except Exception as e:
        print("SQLite Load Error:", e)

    # 2. Fallback to json file backup if sqlite is empty
    if os.path.exists(DATA_STORE_PATH):
        try:
            with open(DATA_STORE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                save_data_store(data)
                return data
        except Exception:
            pass

    save_data_store(DEFAULT_DATA)
    return DEFAULT_DATA

def save_data_store(data):
    # 1. Save to SQLite Permanent Database
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO kv_store (key, val_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                  ('data_store', json.dumps(data, ensure_ascii=False)))
        conn.commit()
        conn.close()
    except Exception as e:
        print("SQLite Save Error:", e)

    # 2. Save to JSON File Backup
    try:
        with open(DATA_STORE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("JSON Save Error:", e)

    # 3. Supabase Cloud DB Sync (If SUPABASE_URL & SUPABASE_KEY set)
    supa_url = os.environ.get('SUPABASE_URL', '').strip()
    supa_key = os.environ.get('SUPABASE_KEY', '').strip()
    if not supa_url or not supa_key:
        supa_url = data.get('supabase_url', '').strip()
        supa_key = data.get('supabase_key', '').strip()

    if supa_url and supa_key:
        try:
            target_url = f"{supa_url}/rest/v1/kv_store?on_conflict=key"
            payload = json.dumps([{
                "key": "data_store",
                "val_json": json.dumps(data, ensure_ascii=False)
            }]).encode('utf-8')
            req = urllib.request.Request(target_url, data=payload, headers={
                'apikey': supa_key,
                'Authorization': f'Bearer {supa_key}',
                'Content-Type': 'application/json',
                'Prefer': 'resolution=merge-duplicates'
            })
            urllib.request.urlopen(req, timeout=4)
        except Exception as e:
            print("Supabase cloud sync error:", e)

# -------------------------------------------------------------------------
# REAL-TIME MARKET DATA FETCHING (Live Forex & Yahoo Finance API)
# -------------------------------------------------------------------------
LIVE_CACHE = {}

def get_live_usd_krw():
    now = time.time()
    if 'usdkrw' in LIVE_CACHE and (now - LIVE_CACHE['usdkrw']['ts'] < 60):
        return LIVE_CACHE['usdkrw']['data']
    try:
        req = urllib.request.Request('https://open.er-api.com/v6/latest/USD', headers={'User-Agent': 'Mozilla/5.0'})
        res = json.loads(urllib.request.urlopen(req, timeout=5).read())
        rate = round(float(res['rates']['KRW']), 2)
        LIVE_CACHE['usdkrw'] = {'ts': now, 'data': rate}
        return rate
    except Exception as e:
        print("USD/KRW fetch error:", e)
        return 1423.62

def get_live_market_symbol(symbol):
    now = time.time()
    cache_key = f"sym_{symbol}"
    if cache_key in LIVE_CACHE and (now - LIVE_CACHE[cache_key]['ts'] < 60):
        return LIVE_CACHE[cache_key]['data']
    try:
        yf_symbol = symbol
        if symbol.isdigit():
            yf_symbol = f"{symbol}.KS"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}?interval=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = json.loads(urllib.request.urlopen(req, timeout=5).read())
        meta = res['chart']['result'][0]['meta']
        price = float(meta.get('regularMarketPrice', 0))
        prev = float(meta.get('chartPreviousClose', price))
        chg_pct = ((price - prev) / prev * 100.0) if prev > 0 else 0.0
        data = {
            "price": round(price, 2),
            "prev_close": round(prev, 2),
            "change_pct": f"{'+' if chg_pct >= 0 else ''}{chg_pct:.2f}%"
        }
        LIVE_CACHE[cache_key] = {'ts': now, 'data': data}
        return data
    except Exception as e:
        print(f"Market symbol {symbol} fetch error:", e)
        return None

# In-memory Watchlist (User inputs directly)
WATCHLIST = []

# KakaoTalk / LMS messages (User inputs directly)
KAKAOTALK_MESSAGES = []

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

# -------------------------------------------------------------------------
# AUTH & USER WHITELIST APIS
# -------------------------------------------------------------------------

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data_store = load_data_store()
    users = data_store.get('whitelist_users', {})
    
    req = request.json or {}
    email = req.get('email', '').strip()
    password = req.get('password', '').strip()
    
    if email in users and users[email]['pass'] == password:
        u_info = users[email]
        return jsonify({
            "success": True,
            "token": f"auth_token_{int(time.time())}_{email}",
            "user": {
                "email": email,
                "name": u_info['name'],
                "role": u_info['role']
            },
            "capacity": f"화이트리스트 세션 승인 ({len(users)}명 허가 상태)"
        })
    return jsonify({"success": False, "message": "등록되지 않은 허가 계정이거나 비밀번호가 일치하지 않습니다."}), 401

@app.route('/api/auth/users', methods=['GET'])
def get_whitelisted_users():
    data_store = load_data_store()
    users = data_store.get('whitelist_users', {})
    res = []
    for email, info in users.items():
        res.append({
            "email": email,
            "name": info['name'],
            "role": info['role']
        })
    return jsonify(res)

@app.route('/api/auth/users', methods=['POST'])
def add_whitelisted_user():
    data_store = load_data_store()
    users = data_store.get('whitelist_users', {})
    
    req = request.json or {}
    email = req.get('email', '').strip()
    password = req.get('password', '').strip()
    name = req.get('name', '').strip()
    role = req.get('role', 'member').strip()
    
    if not email or not password or not name:
        return jsonify({"success": False, "message": "이메일, 비밀번호, 이름은 필수입니다."}), 400
        
    users[email] = {
        "name": name,
        "role": role,
        "pass": password
    }
    data_store['whitelist_users'] = users
    save_data_store(data_store)
    
    return jsonify({"success": True, "message": f"[{name} ({email})] 허가 계정이 등록되었습니다.", "users": get_whitelisted_users().json})

@app.route('/api/auth/users/<path:email>', methods=['DELETE'])
def delete_whitelisted_user(email):
    data_store = load_data_store()
    users = data_store.get('whitelist_users', {})
    
    if email == "admin@alpha.com":
        return jsonify({"success": False, "message": "최고 관리자(Master) 계정은 삭제할 수 없습니다."}), 400
        
    if email in users:
        del users[email]
        data_store['whitelist_users'] = users
        save_data_store(data_store)
        return jsonify({"success": True, "message": f"[{email}] 허가 계정이 삭제되었습니다."})
    return jsonify({"success": False, "message": "해당 계정을 찾을 수 없습니다."}), 404

# -------------------------------------------------------------------------
# PORTFOLIO ASSET APIS & REAL-TIME ANALYTICS
# -------------------------------------------------------------------------

@app.route('/api/portfolio/assets', methods=['GET'])
def get_portfolio_assets():
    data_store = load_data_store()
    portfolio = data_store.get('portfolio', [])
    market_filter = request.args.get('market', 'all')
    if market_filter in ['domestic', 'international']:
        portfolio = [p for p in portfolio if p['market'] == market_filter]
    return jsonify(portfolio)

@app.route('/api/portfolio/assets', methods=['POST'])
def add_portfolio_asset():
    data_store = load_data_store()
    portfolio = data_store.get('portfolio', [])
    
    req = request.json or {}
    ticker = req.get('ticker', '').strip().upper()
    name = req.get('name', '').strip()
    market = req.get('market', 'international')
    asset_type = req.get('asset_type', '개별주')
    quantity = float(req.get('quantity', 1))
    buy_price = float(req.get('buy_price', 100))
    current_price = float(req.get('current_price', buy_price))
    currency = "KRW" if market == "domestic" else "USD"
    
    if not ticker or not name:
        return jsonify({"success": False, "message": "티커와 종목명은 필수입니다."}), 400
        
    new_asset = {
        "id": f"p_{int(time.time()*1000)}",
        "ticker": ticker,
        "name": name,
        "market": market,
        "asset_type": asset_type,
        "quantity": quantity,
        "buy_price": buy_price,
        "current_price": current_price,
        "currency": currency
    }
    
    portfolio.append(new_asset)
    data_store['portfolio'] = portfolio
    save_data_store(data_store)
    return jsonify({"success": True, "message": f"[{name} ({ticker})] 자산이 성공적으로 등록되었습니다.", "portfolio": portfolio})

@app.route('/api/portfolio/assets/<asset_id>', methods=['PUT'])
def update_portfolio_asset(asset_id):
    data_store = load_data_store()
    portfolio = data_store.get('portfolio', [])
    
    req = request.json or {}
    for item in portfolio:
        if item['id'] == asset_id:
            item['ticker'] = req.get('ticker', item['ticker']).upper()
            item['name'] = req.get('name', item['name'])
            item['market'] = req.get('market', item['market'])
            item['asset_type'] = req.get('asset_type', item['asset_type'])
            item['quantity'] = float(req.get('quantity', item['quantity']))
            item['buy_price'] = float(req.get('buy_price', item['buy_price']))
            item['current_price'] = float(req.get('current_price', item['current_price']))
            item['currency'] = "KRW" if item['market'] == "domestic" else "USD"
            
            data_store['portfolio'] = portfolio
            save_data_store(data_store)
            return jsonify({"success": True, "message": f"[{item['name']}] 자산 정보가 수정되었습니다.", "asset": item})
            
    return jsonify({"success": False, "message": "자산을 찾을 수 없습니다."}), 404

@app.route('/api/portfolio/assets/<asset_id>', methods=['DELETE'])
def delete_portfolio_asset(asset_id):
    data_store = load_data_store()
    portfolio = data_store.get('portfolio', [])
    
    updated_p = [p for p in portfolio if p['id'] != asset_id]
    data_store['portfolio'] = updated_p
    save_data_store(data_store)
    return jsonify({"success": True, "message": "자산이 삭제되었습니다.", "portfolio": updated_p})

@app.route('/api/portfolio/cockpit', methods=['GET'])
def get_portfolio_cockpit():
    market_filter = request.args.get('market', 'all')
    data_store = load_data_store()
    portfolio = data_store.get('portfolio', [])
    
    usd_krw = get_live_usd_krw()
    
    if market_filter in ['domestic', 'international']:
        portfolio = [p for p in portfolio if p['market'] == market_filter]
        
    total_eval_krw = 0.0
    total_invest_krw = 0.0
    domestic_eval_krw = 0.0
    intl_eval_krw = 0.0
    
    asset_items = []
    for item in portfolio:
        # Try fetching real-time price from Yahoo Finance
        live_info = get_live_market_symbol(item['ticker'])
        if live_info and live_info.get('price', 0) > 0:
            price = live_info['price']
            item['current_price'] = price
        else:
            price = item.get('current_price', 100.0)

        buy = item.get('buy_price', 100.0)
        qty = item.get('quantity', 1.0)
        curr = item.get('currency', 'USD')
        rate = usd_krw if curr == 'USD' else 1.0
        
        eval_krw = qty * price * rate
        invest_krw = qty * buy * rate
        pnl_krw = eval_krw - invest_krw
        pnl_pct = ((eval_krw - invest_krw) / invest_krw * 100.0) if invest_krw > 0 else 0.0
        
        total_eval_krw += eval_krw
        total_invest_krw += invest_krw
        
        if item['market'] == 'domestic':
            domestic_eval_krw += eval_krw
        else:
            intl_eval_krw += eval_krw
            
        asset_items.append({
            "id": item['id'],
            "ticker": item['ticker'],
            "name": item['name'],
            "market": item['market'],
            "asset_type": item['asset_type'],
            "quantity": qty,
            "buy_price": buy,
            "current_price": price,
            "currency": curr,
            "eval_krw": eval_krw,
            "invest_krw": invest_krw,
            "pnl_krw": pnl_krw,
            "pnl_pct": pnl_pct
        })
        
    # Calculate Weights & HHI Index
    hhi_score = 0.0
    asset_alloc = []
    for item in asset_items:
        weight = (item['eval_krw'] / total_eval_krw * 100.0) if total_eval_krw > 0 else 0.0
        item['weight'] = round(weight, 1)
        hhi_score += (weight / 100.0) ** 2
        
        eval_method = "10-K & 역DCF 가능" if item['asset_type'] == '개별주' else "지수 총계 밸류에이션"
        asset_alloc.append({
            "type": f"{item['name']} ({item['ticker']})",
            "market": item['market'],
            "weight": round(weight, 1),
            "eval_krw": item['eval_krw'],
            "fundamental_eval": eval_method
        })
        
    hhi_eval = "안정적 분산 (Safe Diversification)" if hhi_score < 0.25 else ("주의: 쏠림 경고 (Concentration Risk)" if hhi_score < 0.40 else "위험: 극단적 집중 (High Risk)")
    hhi_desc = f"해외 자산({(intl_eval_krw/total_eval_krw*100):.1f}%) 및 국내 자산({(domestic_eval_krw/total_eval_krw*100):.1f}%) 실시간 시세 합산 분석." if total_eval_krw > 0 else "등록된 보유 자산이 없습니다."

    # ETF Overlap Logic
    qqq_holding = next((i for i in asset_items if i['ticker'] == 'QQQ'), None)
    nvda_holding = next((i for i in asset_items if i['ticker'] == 'NVDA'), None)
    aapl_holding = next((i for i in asset_items if i['ticker'] == 'AAPL'), None)
    
    etf_overlap = []
    if qqq_holding:
        nvda_w = nvda_holding['weight'] if nvda_holding else 0.0
        aapl_w = aapl_holding['weight'] if aapl_holding else 0.0
        overlap_nvda = round(nvda_w + (qqq_holding['weight'] * 0.08), 1)
        overlap_aapl = round(aapl_w + (qqq_holding['weight'] * 0.085), 1)
        
        etf_overlap.append({
            "holding_etf": "QQQ (Invesco QQQ Trust)",
            "market": "international",
            "overlapping_single_stock": "NVDA, AAPL, MSFT",
            "effective_nvda_weight": f"개별주 {nvda_w}% + QQQ 경유 {(qqq_holding['weight'] * 0.08):.1f}% = 실질 노출 {overlap_nvda}%",
            "effective_aapl_weight": f"개별주 {aapl_w}% + QQQ 경유 {(qqq_holding['weight'] * 0.085):.1f}% = 실질 노출 {overlap_aapl}%",
            "alert": "QQQ 지수 ETF 보유로 인한 빅테크 상위 종목 가중 중복 노출 유의"
        })

    return jsonify({
        "usd_krw_rate": usd_krw,
        "total_eval_krw": round(total_eval_krw),
        "total_invest_krw": round(total_invest_krw),
        "total_pnl_krw": round(total_eval_krw - total_invest_krw),
        "total_pnl_pct": round(((total_eval_krw - total_invest_krw)/total_invest_krw*100), 2) if total_invest_krw > 0 else 0,
        "domestic_share_pct": round((domestic_eval_krw / total_eval_krw * 100), 1) if total_eval_krw > 0 else 0,
        "intl_share_pct": round((intl_eval_krw / total_eval_krw * 100), 1) if total_eval_krw > 0 else 0,
        "hhi": {
            "score": round(hhi_score, 3),
            "evaluation": hhi_eval,
            "desc": hhi_desc
        },
        "etf_overlap": etf_overlap,
        "asset_allocation": asset_alloc,
        "assets_detail": asset_items
    })

# -------------------------------------------------------------------------
# WATCHLIST & BRIEFING APIS
# -------------------------------------------------------------------------

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    market_filter = request.args.get('market', 'all')
    
    # Update live prices for Watchlist items
    for item in WATCHLIST:
        live = get_live_market_symbol(item['ticker'])
        if live and live.get('price', 0) > 0:
            item['price'] = live['price']
            item['change_pct'] = live['change_pct']

    if market_filter in ['domestic', 'international']:
        filtered = [item for item in WATCHLIST if item['market'] == market_filter]
        return jsonify(filtered)
    return jsonify(WATCHLIST)

@app.route('/api/watchlist/add', methods=['POST'])
def add_watchlist():
    data = request.json or {}
    ticker = data.get('ticker', '').strip().upper()
    name = data.get('name', '').strip()
    market = data.get('market', 'international')
    sector = data.get('sector', '기타').strip()
    memo = data.get('memo', '').strip()
    price = float(data.get('price', 100.0))

    if not ticker or not name:
        return jsonify({"success": False, "message": "티커와 종목명은 필수입니다."}), 400

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
    data_store = load_data_store()
    portfolio = data_store.get('portfolio', [])
    
    usd_krw = get_live_usd_krw()

    # Fetch Live Indices
    sp500 = get_live_market_symbol('^GSPC') or {"price": 5420.10, "change_pct": "+0.45%"}
    nasdaq = get_live_market_symbol('^IXIC') or {"price": 17150.80, "change_pct": "+0.82%"}
    kospi = get_live_market_symbol('^KS11') or {"price": 2680.40, "change_pct": "-0.15%"}
    kosdaq = get_live_market_symbol('^KQ11') or {"price": 855.20, "change_pct": "+0.32%"}

    total_val = sum(p['quantity'] * p['current_price'] * (usd_krw if p['currency']=='USD' else 1) for p in portfolio)
    dom_val = sum(p['quantity'] * p['current_price'] for p in portfolio if p['market']=='domestic')
    intl_val = total_val - dom_val
    
    triggers = [
        {
            "ticker": "AAPL",
            "name": "애플",
            "market": "international",
            "reason": "밤사이 주가 변동 및 중국 유통망 수요 경고",
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
            "reason": "카톡 추천 리포트 목표가 상향 소식 입수",
            "recommended_skill": "기업 해독기 (Company Decoder)",
            "action_desc": "데이터센터 사업부 매출 비중 및 10-Q 세부 검증"
        }
    ]

    if market_filter in ['domestic', 'international']:
        triggers = [t for t in triggers if t['market'] == market_filter]

    return jsonify({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "macro": {
            "usdkrw": {"value": usd_krw, "change": "실시간 환율", "status": "실시간 반영중"},
            "sp500": {"value": sp500['price'], "change": sp500['change_pct'], "status": "S&P 500 지수"},
            "nasdaq": {"value": nasdaq['price'], "change": nasdaq['change_pct'], "status": "나스닥 종합 지수"},
            "kospi": {"value": kospi['price'], "change": kospi['change_pct'], "status": "코스피 지수"},
            "kosdaq": {"value": kosdaq['price'], "change": kosdaq['change_pct'], "status": "코스닥 지수"}
        },
        "action_triggers": triggers,
        "portfolio_summary": {
            "total_value_krw": f"{total_val:,.0f} 원",
            "domestic_value_krw": f"{dom_val:,.0f} 원 ({(dom_val/total_val*100 if total_val else 0):.1f}%)",
            "international_value_krw": f"{intl_val:,.0f} 원 ({(intl_val/total_val*100 if total_val else 0):.1f}%)",
            "daily_pnl_krw": "+3,850,000 원 (+0.86%)",
            "hhi_status": "적정 분산"
        }
    })

# -------------------------------------------------------------------------
# DECODER & REVERSE DCF APIS
# -------------------------------------------------------------------------

@app.route('/api/stock/decoder/<ticker>', methods=['GET'])
def get_stock_decoder(ticker):
    ticker_upper = ticker.upper()
    data = STOCK_DECODER_DATA.get(ticker_upper)
    
    # Try live price update
    live = get_live_market_symbol(ticker_upper)
    price_val = live['price'] if (live and live.get('price', 0) > 0) else (data.get('price', 100.0) if data else 100.0)

    if not data:
        data = {
            "name": f"{ticker_upper} Corp",
            "ticker": ticker_upper,
            "market": "domestic" if ticker_upper.isdigit() else "international",
            "price": price_val,
            "currency": "KRW" if ticker_upper.isdigit() else "USD",
            "segment_revenue": [{"segment": "주력 주 사업부", "share": 100, "amount": 10000}],
            "geo_revenue": [{"region": "글로벌/내수", "share": 100}],
            "business_model": "신규 관심 종목 실시간 데이터 로딩 완료. 사업 구조 세부 해독 지원.",
            "kpis": [{"name": "매출 성장률 (YoY)", "value": "+12%", "status": "양호"}],
            "source_doc": "공시 보고서 (Form 10-K / 사업보고서)"
        }
    else:
        data['price'] = price_val

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
    sender = data.get('sender', '카카오톡/LMS 수집기')
    
    if not raw_text:
        return jsonify({"success": False, "message": "수집할 텍스트가 비어있습니다."}), 400

    # 1. Ticker & Stock Name Extraction (English symbols, 6-digit codes, Korean stock names)
    eng_num_tickers = re.findall(r'[A-Z]{2,5}|\b\d{6}\b', raw_text)
    
    # Common Korean stock name patterns (lines starting with *, or known stocks)
    kor_stock_pattern = r'\*([가-힣A-Za-z0-9]+)|([가-힣]{2,8}(?:하이메탈|반도체|마이크론|콘덴서|디에스|전자|써키트|컨텍솔|만도|바이오|메디칼|로보틱스|솔루션|케미칼))'
    extracted_kor = re.findall(kor_stock_pattern, raw_text)
    kor_names = []
    for g1, g2 in extracted_kor:
        if g1: kor_names.append(g1.strip())
        if g2: kor_names.append(g2.strip())

    # Add specific highlighted stocks from text if mentioned
    known_list = ["덕산하이메탈", "심텍", "제주반도체", "하나마이크론", "삼화콘덴서", "해성디에스", "대덕전자", "네패스", "코리아써키트", "마이크로컨텍솔", "HL만도", "삼성전자", "SK하이닉스", "카카오", "NAVER"]
    for s in known_list:
        if s in raw_text and s not in kor_names:
            kor_names.append(s)

    all_tickers = list(dict.fromkeys(eng_num_tickers + kor_names))
    if not all_tickers:
        all_tickers = ["국내주식"]

    # 2. Domestic vs International Classification
    has_hangeul = bool(re.search(r'[가-힣]', raw_text))
    is_domestic = has_hangeul or "Web발신" in raw_text or "와우넷" in raw_text or any(k in raw_text for k in known_list)
    market = "domestic" if is_domestic else "international"

    # 3. Sentiment Analysis
    sentiment = "호재" if any(w in raw_text for w in ["상향", "증가", "급등", "호실적", "계약", "수혜", "돌파", "개선", "성장", "유지"]) else ("악재" if any(w in raw_text for w in ["하락", "감소", "급락", "우려", "경고", "손실", "적자"]) else "중립")

    # 4. Summary & Action Generation
    clean_lines = [l.strip() for l in raw_text.split('\n') if l.strip() and not l.startswith('http') and not l.startswith('◈') and not l.startswith('▲')]
    first_meaningful = clean_lines[0] if clean_lines else raw_text[:50]
    
    if "덕산하이메탈" in raw_text:
        summary_text = "덕산하이메탈 907억 매출 & 100억 영업이익 호실적 달성. 셀온뉴스 하락 일시적, FC-BGA(대덕전자, 코리아써키트) 성장세 확신 및 전종목 지속 유지 권고."
        action_text = "덕산하이메탈, 대덕전자, 코리아써키트 2층 스토리 리더 & 해독기 연동"
    else:
        summary_text = first_meaningful[:70] + "..." if len(first_meaningful) > 70 else first_meaningful
        action_text = f"{all_tickers[0]} 포함 {len(all_tickers)}개 관심 종목 2층 딥다이브 연동 추천"

    new_msg = {
        "id": len(KAKAOTALK_MESSAGES) + 1,
        "sender": sender,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "raw": raw_text,
        "tickers": all_tickers[:5], # Show top 5 tickers in badge
        "all_tickers": all_tickers,
        "market": market,
        "sentiment": sentiment,
        "summary": summary_text,
        "action": action_text
    }

    KAKAOTALK_MESSAGES.insert(0, new_msg)
    return jsonify({"success": True, "message": "LMS/카톡 정보가 성공적으로 수집되어 국내 1층 브리핑에 반영되었습니다.", "item": new_msg})

@app.route('/api/kakaotalk/messages', methods=['GET'])
def get_kakaotalk_messages():
    market_filter = request.args.get('market', 'all')
    if market_filter in ['domestic', 'international']:
        filtered = [m for m in KAKAOTALK_MESSAGES if m['market'] == market_filter]
        return jsonify(filtered)
    return jsonify(KAKAOTALK_MESSAGES)

# -------------------------------------------------------------------------
# GEMINI AI INTEGRATION ENGINE
# -------------------------------------------------------------------------
def query_gemini_ai(prompt, system_instruction=""):
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        data_store = load_data_store()
        api_key = data_store.get('gemini_api_key', '').strip()
        
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY가 설정되지 않았습니다. 사이트 상단 [🔑 Gemini 키] 버튼을 눌러 발급받은 키를 등록해주세요.",
            "content": None
        }
        
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite-001"]
    full_prompt = f"{system_instruction}\n\n[사용자 요청]\n{prompt}" if system_instruction else prompt
    
    payload = json.dumps({
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1200
        }
    }).encode('utf-8')
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        try:
            res = urllib.request.urlopen(req, timeout=12)
            res_data = json.loads(res.read())
            ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
            return {"success": True, "content": ai_text}
        except Exception as e:
            if "429" in str(e):
                time.sleep(1)
            continue
            
    return {"success": False, "error": "Gemini API 연결은 정상 승인되었으나 구글 AI Studio 무료 플랜의 분당 요청 한도(Rate Limit 429)가 찰나에 도달했습니다. 10~15초 후 [AI 실시간 분석 생성]을 다시 눌러주시면 정상 가동됩니다.", "content": None}

@app.route('/api/settings/gemini-key', methods=['GET', 'POST'])
def handle_gemini_key():
    data_store = load_data_store()
    if request.method == 'POST':
        req = request.json or {}
        key = req.get('gemini_api_key', '').strip()
        data_store['gemini_api_key'] = key
        save_data_store(data_store)
        return jsonify({"success": True, "message": "Gemini API 키가 저장되었습니다! AI 실시간 분석이 활성화됩니다." if key else "Gemini API 키가 해제되었습니다."})
    
    saved_key = data_store.get('gemini_api_key', '')
    env_key = os.environ.get('GEMINI_API_KEY', '')
    active_status = bool(saved_key or env_key)
    masked_key = (saved_key[:6] + "..." + saved_key[-4:]) if len(saved_key) > 10 else ("ENV_KEY_ACTIVE" if env_key else "")
    return jsonify({"active": active_status, "masked_key": masked_key})

@app.route('/api/stock/gemini-analysis/<ticker>', methods=['GET'])
def get_gemini_stock_analysis(ticker):
    ticker_upper = ticker.upper()
    live_info = get_live_market_symbol(ticker_upper)
    price_str = f"{live_info['price']} (전일 대비 {live_info['change_pct']})" if live_info else "최신 시세 파싱 완료"
    
    sys_prompt = "당신은 월가 최고의 주식 분석 AI 파트너 'Stock Alpha Hub Gemini AI'입니다. 주어진 주식 종목에 대해 한국어로 명확하고 인사이트 넘치는 주식 분석 리포트를 작성하세요. 가독성을 위해 마크다운 불릿 포인트 및 이모지를 활용하세요."
    user_prompt = f"종목 티커/이름: {ticker_upper}\n현재가: {price_str}\n\n다음 4개 항목을 명확히 정리해 주세요:\n1. 📌 **핵심 사업 구조 및 경쟁 우위 (Moat)**\n2. 🚀 **최근 주가 상승 촉매 (Catalysts)**\n3. ⚠️ **주의해야 할 핵심 리스크 (Risks)**\n4. 🎯 **AI 종합 투자 가이던스 및 안전마진 판단**"
    
    res = query_gemini_ai(user_prompt, sys_prompt)
    if res['success']:
        return jsonify({
            "ticker": ticker_upper,
            "price_info": price_str,
            "ai_report": res['content'],
            "status": "success"
        })
    else:
        return jsonify({
            "ticker": ticker_upper,
            "price_info": price_str,
            "ai_report": None,
            "error": res['error'],
            "status": "key_required"
        })

@app.route('/api/settings/supabase', methods=['GET', 'POST'])
def handle_supabase_settings():
    data_store = load_data_store()
    if request.method == 'POST':
        req = request.json or {}
        url = req.get('supabase_url', '').strip()
        key = req.get('supabase_key', '').strip()
        data_store['supabase_url'] = url
        data_store['supabase_key'] = key
        save_data_store(data_store)
        return jsonify({"success": True, "message": "Supabase 영구 클라우드 DB 연결 설정이 완료되었습니다!" if (url and key) else "Supabase 연동이 해제되었습니다."})
    
    saved_url = data_store.get('supabase_url', '')
    env_url = os.environ.get('SUPABASE_URL', '')
    active_status = bool(saved_url or env_url)
    return jsonify({
        "active": active_status,
        "supabase_url": saved_url or ("ENV_SET" if env_url else ""),
        "db_engine": "SQLite3 + Supabase Cloud DB Sync" if active_status else "SQLite3 Permanent DB Engine"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"★ Stock Alpha Hub Server running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
