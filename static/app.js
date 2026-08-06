/**
 * AlphaHub - Frontend Application Logic v3.0
 * Secure Whitelist Access Control & Real-Time Portfolio Asset Management
 */

document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------------------------
    // Global State
    // ----------------------------------------------------------------------
    let currentMarketFilter = 'all'; // 'all' | 'domestic' | 'international'
    let currentUser = { name: "우성교 (Master)", email: "admin@alpha.com", role: "admin" };
    let assetChartInstance = null;

    // ----------------------------------------------------------------------
    // DOM Elements
    // ----------------------------------------------------------------------
    const navLinks = document.querySelectorAll('.nav-link');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const pageTitle = document.getElementById('pageTitle');
    const pageSubtext = document.getElementById('pageSubtext');

    const marketFilterBtns = document.querySelectorAll('.btn-m-filter');
    const currentMarketPill = document.getElementById('currentMarketPill');
    const marketPillText = document.getElementById('marketPillText');

    const triggerList = document.getElementById('triggerList');
    const kakaoFeedContainer = document.getElementById('kakaoFeedContainer');
    const kakaoArchiveTbody = document.getElementById('kakaoArchiveTbody');
    const watchlistContainer = document.getElementById('watchlistContainer');

    const btnRefreshBriefing = document.getElementById('btnRefreshBriefing');
    const btnOpenUserMgmt = document.getElementById('btnOpenUserMgmt');

    // ----------------------------------------------------------------------
    // Market Selector Logic (국내 / 해외 / 전체)
    // ----------------------------------------------------------------------
    marketFilterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            marketFilterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            currentMarketFilter = btn.getAttribute('data-market');
            
            // Update Top Header Pill
            if (currentMarketFilter === 'domestic') {
                marketPillText.innerText = '🇰🇷 국내 주식 시장';
            } else if (currentMarketFilter === 'international') {
                marketPillText.innerText = '🇺🇸 해외 주식 시장';
            } else {
                marketPillText.innerText = '전체 (국내 & 해외)';
            }

            // Reload Active Views
            loadDailyBriefing();
            loadWatchlist();
            loadPortfolioCockpit();
        });
    });

    // ----------------------------------------------------------------------
    // Navigation & Tab Switching
    // ----------------------------------------------------------------------
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetTabId = link.getAttribute('data-tab');
            switchTab(targetTabId);
        });
    });

    function switchTab(tabId) {
        navLinks.forEach(l => l.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));

        const activeLink = document.querySelector(`.nav-link[data-tab="${tabId}"]`);
        const activePane = document.getElementById(tabId);

        if (activeLink && activePane) {
            activeLink.classList.add('active');
            activePane.classList.add('active');

            if (tabId === 'tab-layer1') {
                pageTitle.innerText = '1층: 일일 브리핑 & 카카오톡 실시간 서머리';
                pageSubtext.innerText = '밤사이 주요 시장 움직임, 환율, 관심 테마 및 액션 신호 모니터링';
            } else if (tabId === 'tab-watchlist') {
                pageTitle.innerText = '관심 종목 관리 (Domestic & International Watchlist)';
                pageSubtext.innerText = '국내/해외 관심 종목 등록 및 원클릭 2층 딥다이브 연동';
                loadWatchlist();
            } else if (tabId === 'tab-layer15') {
                pageTitle.innerText = '1.5층: 실시간 포트폴리오 콕핏 (Portfolio Cockpit)';
                pageSubtext.innerText = '실제 보유 자산 등록, HHI 집중도 지수 및 손익률 실시간 계산';
                loadPortfolioCockpit();
            } else if (tabId === 'tab-decoder') {
                pageTitle.innerText = '2층 딥다이브: ① 기업 해독기 (Company Decoder)';
                pageSubtext.innerText = '사업 모델 쪼개기, 사업부문/지역별 매출 다이어그램 및 핵심 KPI 요약';
            } else if (tabId === 'tab-story') {
                pageTitle.innerText = '2층 딥다이브: ② 스토리 리더 (Story Reader)';
                pageSubtext.innerText = '최근 3개년 10-K 문구 비교 및 톤변화(Tone-Down) 포착, 가이던스 이행 추적';
            } else if (tabId === 'tab-price') {
                pageTitle.innerText = '2층 딥다이브: ③ 가격 판독기 (Price Decoder - 역DCF)';
                pageSubtext.innerText = '현재 주가가 내포한 요구 성장률 역산 및 WACC/Terminal g 민감도 분석';
            } else if (tabId === 'tab-kakao') {
                pageTitle.innerText = '카카오톡 정보 수집기 (KakaoTalk Collector)';
                pageSubtext.innerText = '단톡방 정보 텍스트 수동/자동 수집 및 AI 종목/감성 파싱 피드';
            }
        }
    }

    // ----------------------------------------------------------------------
    // User Authentication & Whitelist Management
    // ----------------------------------------------------------------------
    function updateUserUI() {
        document.getElementById('userNameDisplay').innerText = currentUser.name;
        document.getElementById('userRoleDisplay').innerHTML = currentUser.role === 'admin' 
            ? `<i class="fa-solid fa-user-shield text-mauve"></i> 관리자 (Master)` 
            : `<i class="fa-solid fa-user text-teal"></i> 일반 회원 (Member)`;
        
        if (currentUser.role === 'admin') {
            btnOpenUserMgmt.style.display = 'inline-block';
        } else {
            btnOpenUserMgmt.style.display = 'none';
        }
    }

    async function loadWhitelistedUsers() {
        try {
            const res = await fetch('/api/auth/users');
            const users = await res.json();
            const tbody = document.getElementById('userMgmtTbody');
            
            tbody.innerHTML = users.map(u => `
                <tr>
                    <td><strong>${u.email}</strong></td>
                    <td>${u.name}</td>
                    <td><span class="badge ${u.role === 'admin' ? 'up' : 'normal'}">${u.role === 'admin' ? '최고 관리자' : '일반 회원'}</span></td>
                    <td>
                        ${u.email !== 'admin@alpha.com' ? `
                            <button class="btn-danger btn-xs btn-del-user" data-email="${u.email}">
                                <i class="fa-solid fa-trash"></i> 삭제
                            </button>
                        ` : '<span class="text-sub">삭제 불가</span>'}
                    </td>
                </tr>
            `).join('');

            document.querySelectorAll('.btn-del-user').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const email = btn.getAttribute('data-email');
                    if (confirm(`[${email}] 계정을 접근 허가 목록에서 삭제하시겠습니까?`)) {
                        const delRes = await fetch(`/api/auth/users/${encodeURIComponent(email)}`, { method: 'DELETE' });
                        const delData = await delRes.json();
                        alert(delData.message);
                        loadWhitelistedUsers();
                    }
                });
            });
        } catch (err) {
            console.error('Error loading users:', err);
        }
    }

    // ----------------------------------------------------------------------
    // API Fetchers & Renderers
    // ----------------------------------------------------------------------

    // 1. Fetch Daily Briefing (Filtered by Market)
    async function loadDailyBriefing() {
        try {
            const res = await fetch(`/api/briefing?market=${currentMarketFilter}`);
            const data = await res.json();

            // Render Action Triggers
            if (data.action_triggers) {
                triggerList.innerHTML = data.action_triggers.map(trig => `
                    <div class="trigger-card">
                        <div class="trig-header">
                            <span class="t-name">
                                <span class="badge ${trig.market === 'domestic' ? 'up' : 'normal'}">${trig.market === 'domestic' ? '🇰🇷 국내' : '🇺🇸 해외'}</span>
                                ${trig.name} (${trig.ticker})
                            </span>
                            <span class="skill-pill"><i class="fa-solid fa-wand-magic-sparkles"></i> ${trig.recommended_skill}</span>
                        </div>
                        <p class="trig-reason">${trig.reason}</p>
                        <p class="trig-action">→ ${trig.action_desc}</p>
                        <button class="btn-secondary btn-sm mt-2 btn-run-trigger" data-ticker="${trig.ticker}" data-skill="${trig.recommended_skill}">
                            <i class="fa-solid fa-play"></i> 딥다이브 스킬 가동
                        </button>
                    </div>
                `).join('');

                document.querySelectorAll('.btn-run-trigger').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const ticker = btn.getAttribute('data-ticker');
                        const skill = btn.getAttribute('data-skill');
                        if (skill.includes('기업 해독기')) {
                            document.getElementById('decoderTickerInput').value = ticker;
                            switchTab('tab-decoder');
                            runCompanyDecoder(ticker);
                        } else if (skill.includes('스토리 리더')) {
                            document.getElementById('storyTickerInput').value = ticker;
                            switchTab('tab-story');
                            runStoryReader(ticker);
                        } else if (skill.includes('가격 판독기')) {
                            document.getElementById('dcfTicker').value = ticker;
                            switchTab('tab-price');
                            runReverseDcf();
                        }
                    });
                });
            }

            loadKakaoMessages();
        } catch (err) {
            console.error('Error loading briefing:', err);
        }
    }

    // 2. Fetch Watchlist
    async function loadWatchlist() {
        try {
            const res = await fetch(`/api/watchlist?market=${currentMarketFilter}`);
            const list = await res.json();

            watchlistContainer.innerHTML = list.map(item => `
                <div class="watchlist-card">
                    <div class="wl-header">
                        <div class="wl-title">
                            <span class="badge ${item.market === 'domestic' ? 'up' : 'normal'}">${item.market === 'domestic' ? '🇰🇷 국내' : '🇺🇸 해외'}</span>
                            <strong>${item.name}</strong> (${item.ticker})
                        </div>
                        <div class="wl-price">
                            ${item.currency === 'USD' ? '$' : ''}${item.price.toLocaleString()} ${item.currency === 'KRW' ? '원' : ''}
                            <span class="${item.change_pct.includes('+') ? 'up' : 'down'}">${item.change_pct}</span>
                        </div>
                    </div>
                    <div class="wl-sector"><i class="fa-solid fa-tag"></i> ${item.sector}</div>
                    <p class="wl-memo">${item.memo}</p>
                    <div class="wl-actions mt-3">
                        <button class="btn-sm btn-outline btn-watch-skill" data-ticker="${item.ticker}" data-type="decoder">
                            <i class="fa-solid fa-microscope"></i> 기업해독
                        </button>
                        <button class="btn-sm btn-outline btn-watch-skill" data-ticker="${item.ticker}" data-type="story">
                            <i class="fa-solid fa-book-open"></i> 스토리리더
                        </button>
                        <button class="btn-sm btn-outline btn-watch-skill" data-ticker="${item.ticker}" data-type="price">
                            <i class="fa-solid fa-calculator"></i> 역DCF판독
                        </button>
                        <button class="btn-sm btn-secondary btn-del-watch" data-ticker="${item.ticker}" style="margin-left:auto; color:var(--color-red);">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.btn-watch-skill').forEach(btn => {
                btn.addEventListener('click', () => {
                    const ticker = btn.getAttribute('data-ticker');
                    const type = btn.getAttribute('data-type');
                    if (type === 'decoder') {
                        document.getElementById('decoderTickerInput').value = ticker;
                        switchTab('tab-decoder');
                        runCompanyDecoder(ticker);
                    } else if (type === 'story') {
                        document.getElementById('storyTickerInput').value = ticker;
                        switchTab('tab-story');
                        runStoryReader(ticker);
                    } else if (type === 'price') {
                        document.getElementById('dcfTicker').value = ticker;
                        switchTab('tab-price');
                        runReverseDcf();
                    }
                });
            });

            document.querySelectorAll('.btn-del-watch').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const ticker = btn.getAttribute('data-ticker');
                    if (confirm(`[${ticker}] 관심 종목에서 삭제하시겠습니까?`)) {
                        await fetch(`/api/watchlist/delete/${ticker}`, { method: 'DELETE' });
                        loadWatchlist();
                    }
                });
            });
        } catch (err) {
            console.error('Error loading watchlist:', err);
        }
    }

    // 3. Fetch Kakao Messages
    async function loadKakaoMessages() {
        try {
            const res = await fetch(`/api/kakaotalk/messages?market=${currentMarketFilter}`);
            const messages = await res.json();

            kakaoFeedContainer.innerHTML = messages.slice(0, 3).map(m => `
                <div class="kakao-feed-card">
                    <div class="kf-header">
                        <span class="kf-sender">
                            <span class="badge ${m.market === 'domestic' ? 'up' : 'normal'}">${m.market === 'domestic' ? '국내' : '해외'}</span>
                            <i class="fa-comment fab"></i> ${m.sender}
                        </span>
                        <span>${m.time}</span>
                    </div>
                    <div class="kf-raw">${m.raw}</div>
                    <div class="kf-footer">
                        <div class="kf-tags">
                            ${m.tickers.map(t => `<span class="ticker-tag">$${t}</span>`).join('')}
                            <span class="badge ${m.sentiment === '호재' ? 'up' : (m.sentiment === '악재' ? 'down' : 'normal')}">${m.sentiment}</span>
                        </div>
                        <span style="font-size:0.75rem; color:var(--color-peach); font-weight:600;">⚡ ${m.action}</span>
                    </div>
                </div>
            `).join('');

            kakaoArchiveTbody.innerHTML = messages.map(m => `
                <tr>
                    <td>${m.time}</td>
                    <td><strong class="text-yellow">${m.sender}</strong></td>
                    <td><span class="badge ${m.market === 'domestic' ? 'up' : 'normal'}">${m.market === 'domestic' ? '🇰🇷 국내' : '🇺🇸 해외'}</span></td>
                    <td>${m.tickers.map(t => `<span class="ticker-tag">$${t}</span>`).join(' ')}</td>
                    <td><span class="badge ${m.sentiment === '호재' ? 'up' : (m.sentiment === '악재' ? 'down' : 'normal')}">${m.sentiment}</span></td>
                    <td>${m.summary}</td>
                    <td><span class="text-mauve" style="font-weight:600;">${m.action}</span></td>
                </tr>
            `).join('');
        } catch (err) {
            console.error('Error loading Kakao messages:', err);
        }
    }

    // 4. Load Portfolio Cockpit & Real-Time Holdings
    async function loadPortfolioCockpit() {
        try {
            const res = await fetch(`/api/portfolio/cockpit?market=${currentMarketFilter}`);
            const data = await res.json();

            // Stat Cards Update
            document.getElementById('statTotalVal').innerText = `${data.total_eval_krw.toLocaleString()} 원`;
            const pnlElem = document.getElementById('statPnlRatio');
            const isUp = data.total_pnl_pct >= 0;
            pnlElem.className = `trend ${isUp ? 'up' : 'down'}`;
            pnlElem.innerHTML = `<i class="fa-solid fa-${isUp ? 'caret-up' : 'caret-down'}"></i> ${isUp ? '+' : ''}${data.total_pnl_pct}% (${data.total_pnl_krw.toLocaleString()} 원)`;

            document.getElementById('statAssetRatio').innerText = `해외 ${data.intl_share_pct}% / 국내 ${data.domestic_share_pct}%`;
            document.getElementById('statHhiStatus').innerText = `HHI: ${data.hhi.score} (${data.hhi.evaluation})`;

            // Render HHI Score Box
            document.getElementById('hhiScoreVal').innerText = data.hhi.score;
            document.getElementById('hhiEvalText').innerText = data.hhi.evaluation;
            document.getElementById('hhiDescText').innerText = data.hhi.desc;

            // Render Holdings Table
            const tbody = document.getElementById('portfolioHoldingsTbody');
            tbody.innerHTML = data.assets_detail.map(a => `
                <tr>
                    <td><strong class="text-yellow">${a.ticker}</strong></td>
                    <td>${a.name}</td>
                    <td><span class="badge ${a.market === 'domestic' ? 'up' : 'normal'}">${a.market === 'domestic' ? '🇰🇷 국내' : '🇺🇸 해외'}</span></td>
                    <td><span class="info-tag">${a.asset_type}</span></td>
                    <td>${a.quantity.toLocaleString()}주</td>
                    <td>${a.currency === 'USD' ? '$' : ''}${a.buy_price.toLocaleString()}</td>
                    <td>${a.currency === 'USD' ? '$' : ''}${a.current_price.toLocaleString()}</td>
                    <td><strong>${a.eval_krw.toLocaleString()} 원</strong></td>
                    <td><span class="${a.pnl_pct >= 0 ? 'text-green' : 'text-red'}" style="font-weight:700;">${a.pnl_pct >= 0 ? '+' : ''}${a.pnl_pct.toFixed(2)}%</span></td>
                    <td>
                        <button class="btn-secondary btn-xs btn-edit-asset" data-asset='${JSON.stringify(a)}'><i class="fa-solid fa-pen"></i></button>
                        <button class="btn-danger btn-xs btn-del-asset" data-id="${a.id}"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');

            // Attach Asset Edit / Delete Event Listeners
            document.querySelectorAll('.btn-edit-asset').forEach(btn => {
                btn.addEventListener('click', () => {
                    const item = JSON.parse(btn.getAttribute('data-asset'));
                    document.getElementById('assetEditId').value = item.id;
                    document.getElementById('assetMarket').value = item.market;
                    document.getElementById('assetTicker').value = item.ticker;
                    document.getElementById('assetName').value = item.name;
                    document.getElementById('assetType').value = item.asset_type;
                    document.getElementById('assetQuantity').value = item.quantity;
                    document.getElementById('assetBuyPrice').value = item.buy_price;
                    document.getElementById('assetCurrentPrice').value = item.current_price;
                    document.getElementById('assetModalTitle').innerText = '보유 자산 수정';
                    document.getElementById('assetModal').classList.add('active');
                });
            });

            document.querySelectorAll('.btn-del-asset').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.getAttribute('data-id');
                    if (confirm('선택한 자산을 포트폴리오에서 삭제하시겠습니까?')) {
                        await fetch(`/api/portfolio/assets/${id}`, { method: 'DELETE' });
                        loadPortfolioCockpit();
                        loadDailyBriefing();
                    }
                });
            });

            // Render ETF Overlap List
            const etfContainer = document.getElementById('etfOverlapList');
            if (data.etf_overlap && data.etf_overlap.length > 0) {
                etfContainer.innerHTML = data.etf_overlap.map(ov => `
                    <div class="overlap-card">
                        <div class="ov-title"><i class="fa-solid fa-box-archive"></i> ${ov.holding_etf}</div>
                        <p class="ov-detail">${ov.effective_nvda_weight}</p>
                        <p class="ov-detail">${ov.effective_aapl_weight}</p>
                        <div class="alert-pill warning"><i class="fa-solid fa-triangle-exclamation"></i> ${ov.alert}</div>
                    </div>
                `).join('');
            } else {
                etfContainer.innerHTML = `<div class="text-sub">감지된 ETF 중복 노출 항목이 없습니다.</div>`;
            }

            // Doughnut Chart Render
            const ctx = document.getElementById('assetDoughnutChart').getContext('2d');
            if (assetChartInstance) assetChartInstance.destroy();

            const labels = data.asset_allocation.map(a => a.type);
            const weights = data.asset_allocation.map(a => a.weight);

            assetChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: weights,
                        backgroundColor: ['#cba6f7', '#89b4fa', '#a6e3a1', '#f9e2af', '#fab387', '#f38ba8'],
                        borderColor: '#1e1e2e',
                        borderWidth: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { color: '#cdd6f4', font: { family: 'Inter' } } }
                    }
                }
            });
        } catch (err) {
            console.error('Error loading cockpit:', err);
        }
    }

    // 5. Run Company Decoder Skill
    async function runCompanyDecoder(ticker) {
        const container = document.getElementById('decoderResultContainer');
        container.innerHTML = `<div class="content-card"><i class="fa-solid fa-spinner fa-spin text-mauve"></i> [${ticker}] 10-K 및 사업보고서 파싱 중...</div>`;

        try {
            const res = await fetch(`/api/stock/decoder/${ticker}`);
            const data = await res.json();

            container.innerHTML = `
                <div class="content-card mb-4">
                    <div class="card-header">
                        <h3>
                            <span class="badge ${data.market === 'domestic' ? 'up' : 'normal'}">${data.market === 'domestic' ? '🇰🇷 국내' : '🇺🇸 해외'}</span>
                            <i class="fa-solid fa-building text-mauve"></i> ${data.name} (${data.ticker}) 사업 구조 해독 카드
                        </h3>
                        <span class="badge success">현재 주가: ${data.currency === 'USD' ? '$' : ''}${data.price} ${data.currency === 'KRW' ? '원' : ''}</span>
                    </div>

                    <div class="hhi-box mb-3" style="background:rgba(49, 50, 68, 0.4); padding:1rem; border-radius:12px;">
                        <h4 style="color:var(--color-peach); font-size:0.9rem; margin-bottom:4px;"><i class="fa-solid fa-bullseye"></i> 비즈니스 모델 요약</h4>
                        <p style="font-size:0.85rem; color:var(--color-subtext1);">${data.business_model}</p>
                    </div>

                    <div class="card-grid col-2 mb-3">
                        <div>
                            <h4 style="font-size:0.85rem; margin-bottom:6px;"><i class="fa-solid fa-pie-chart text-mauve"></i> 사업부문별 매출 비중</h4>
                            ${data.segment_revenue.map(s => `
                                <div style="font-size:0.8rem; margin-bottom:4px; display:flex; justify-between;">
                                    <span>${s.segment}</span>
                                    <strong class="text-mauve">${s.share}%</strong>
                                </div>
                            `).join('')}
                        </div>
                        <div>
                            <h4 style="font-size:0.85rem; margin-bottom:6px;"><i class="fa-solid fa-globe text-teal"></i> 지역별 매출 비중</h4>
                            ${data.geo_revenue.map(g => `
                                <div style="font-size:0.8rem; margin-bottom:4px; display:flex; justify-between;">
                                    <span>${g.region}</span>
                                    <strong class="text-teal">${g.share}%</strong>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <h4 style="font-size:0.85rem; margin-bottom:6px;"><i class="fa-solid fa-list-check text-yellow"></i> 핵심 모니터링 KPI</h4>
                    <div class="card-grid col-3">
                        ${data.kpis.map(k => `
                            <div style="background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:8px;">
                                <div style="font-size:0.75rem; color:var(--color-subtext0);">${k.name}</div>
                                <strong style="font-size:1rem; color:var(--color-mauve);">${k.value}</strong>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div class="content-card text-red">해독 실패: ${err.message}</div>`;
        }
    }

    // 6. Run Story Reader Skill
    async function runStoryReader(ticker) {
        const container = document.getElementById('storyResultContainer');
        container.innerHTML = `<div class="content-card"><i class="fa-solid fa-spinner fa-spin text-flamingo"></i> [${ticker}] 최근 3개년 공시 및 어닝콜 문구 대조 중...</div>`;

        try {
            const res = await fetch(`/api/stock/story/${ticker}`);
            const data = await res.json();

            container.innerHTML = `
                <div class="content-card mb-4">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-timeline text-flamingo"></i> ${data.ticker} 지난 3개년 스토리 추적</h3>
                        <span class="info-tag">${data.period}</span>
                    </div>

                    <h4 style="font-size:0.9rem; color:var(--color-flamingo); margin-bottom:8px;"><i class="fa-solid fa-quote-left"></i> 10-K & 공시 문구 톤 변화 (Tone Shift)</h4>
                    <div class="mb-4">
                        ${data.tone_changes.map(t => `
                            <div style="background:rgba(49, 50, 68, 0.4); border-left:3px solid var(--color-flamingo); padding:10px 14px; margin-bottom:8px; border-radius:0 8px 8px 0;">
                                <div style="font-size:0.8rem; font-weight:700; color:var(--color-peach);">${t.topic} [${t.shift}]</div>
                                <div style="font-size:0.78rem; color:var(--color-subtext0); margin-top:2px;">이전: ${t.old_text}</div>
                                <div style="font-size:0.78rem; color:var(--color-text); font-weight:600; margin-top:2px;">최근: ${t.new_text}</div>
                            </div>
                        `).join('')}
                    </div>

                    <h4 style="font-size:0.9rem; color:var(--color-green); margin-bottom:8px;"><i class="fa-solid fa-handshake"></i> 경영진 어닝콜 약속 vs 실제 실적</h4>
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead>
                                <tr><th>분기</th><th>약속 가이던스</th><th>실제 달성치</th><th>결과</th></tr>
                            </thead>
                            <tbody>
                                ${data.guidance_track_record.map(g => `
                                    <tr>
                                        <td><strong>${g.quarter}</strong></td>
                                        <td>${g.promised}</td>
                                        <td>${g.actual}</td>
                                        <td><span class="badge success">${g.result}</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div class="content-card text-red">스토리 조회 실패: ${err.message}</div>`;
        }
    }

    // 7. Run Reverse DCF Calculation
    async function runReverseDcf() {
        const container = document.getElementById('priceDecoderResult');
        container.innerHTML = `<div class="content-card"><i class="fa-solid fa-spinner fa-spin text-peach"></i> 요구 성장률 역산 매트릭스 계산 중...</div>`;

        const payload = {
            ticker: document.getElementById('dcfTicker').value,
            price: document.getElementById('dcfPrice').value,
            fcf: document.getElementById('dcfFcf').value,
            shares: document.getElementById('dcfShares').value,
            wacc: document.getElementById('dcfWacc').value,
            terminal_g: document.getElementById('dcfTerminalG').value
        };

        try {
            const res = await fetch('/api/stock/price-decoder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            container.innerHTML = `
                <div class="content-card mb-4">
                    <div class="card-header">
                        <h3><i class="fa-solid fa-scale-balanced text-peach"></i> ${data.ticker} 가격 판독 (Reverse DCF 결론)</h3>
                        <span class="badge ${data.gap > 5 ? 'down' : 'up'}">${data.safety_assessment}</span>
                    </div>

                    <div class="hhi-box mb-3" style="background:rgba(250, 179, 135, 0.1); border:1px solid rgba(250, 179, 135, 0.3); padding:1rem; border-radius:12px;">
                        <h4 style="color:var(--color-peach); font-size:1rem;"><i class="fa-solid fa-calculator"></i> 내포된 요구 성장률: 연 평균 +${data.implied_annual_growth}%</h4>
                        <p style="font-size:0.85rem; color:var(--color-subtext1); margin-top:4px;">${data.evaluation_summary}</p>
                    </div>

                    <h4 style="font-size:0.85rem; margin-bottom:6px;"><i class="fa-solid fa-table-cells text-mauve"></i> WACC & 영구성장률(g) 민감도 매트릭스</h4>
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>할인율 (WACC)</th>
                                    <th>Terminal g -0.5%</th>
                                    <th>적용 g (${data.terminal_g_used})</th>
                                    <th>Terminal g +0.5%</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.sensitivity_matrix.map(row => `
                                    <tr>
                                        <td><strong>WACC ${row.wacc}</strong></td>
                                        <td>연 +${row.rates[0]}%</td>
                                        <td style="background:rgba(203,166,247,0.15); font-weight:700; color:var(--color-mauve);">연 +${row.rates[1]}%</td>
                                        <td>연 +${row.rates[2]}%</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div class="content-card text-red">오류가 발생했습니다: ${err.message}</div>`;
        }
    }

    // ----------------------------------------------------------------------
    // Modals & Event Handlers
    // ----------------------------------------------------------------------
    btnRefreshBriefing.addEventListener('click', loadDailyBriefing);

    document.getElementById('btnRunDecoder').addEventListener('click', () => {
        runCompanyDecoder(document.getElementById('decoderTickerInput').value);
    });
    document.getElementById('btnRunStory').addEventListener('click', () => {
        runStoryReader(document.getElementById('storyTickerInput').value);
    });
    document.getElementById('btnCalculateReverseDcf').addEventListener('click', runReverseDcf);

    // Watchlist Modal Controls
    const addWatchlistModal = document.getElementById('addWatchlistModal');
    document.getElementById('btnOpenAddWatchlistModal').addEventListener('click', () => addWatchlistModal.classList.add('active'));
    document.getElementById('btnCloseAddWatchlistModal').addEventListener('click', () => addWatchlistModal.classList.remove('active'));

    document.getElementById('btnSubmitAddWatchlist').addEventListener('click', async () => {
        const payload = {
            market: document.getElementById('addWatchMarket').value,
            ticker: document.getElementById('addWatchTicker').value.trim(),
            name: document.getElementById('addWatchName').value.trim(),
            sector: document.getElementById('addWatchSector').value.trim(),
            price: document.getElementById('addWatchPrice').value || 100.0,
            memo: document.getElementById('addWatchMemo').value.trim()
        };

        if (!payload.ticker || !payload.name) {
            return alert('종목 티커와 종목명은 필수 입력 항목입니다.');
        }

        try {
            const res = await fetch('/api/watchlist/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                alert(data.message);
                addWatchlistModal.classList.remove('active');
                loadWatchlist();
            } else {
                alert(data.message);
            }
        } catch (err) {
            alert('관심 종목 등록 실패: ' + err.message);
        }
    });

    // Kakao Ingestion Submit
    document.getElementById('btnSubmitKakaoText').addEventListener('click', async () => {
        const text = document.getElementById('kakaoRawInput').value.trim();
        if (!text) return alert('텍스트를 입력해 주세요.');

        try {
            const res = await fetch('/api/kakaotalk/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, sender: "카톡 입수" })
            });
            const data = await res.json();
            if (data.success) {
                alert(data.message);
                document.getElementById('kakaoRawInput').value = '';
                loadDailyBriefing();
                switchTab('tab-layer1');
            }
        } catch (err) {
            alert('에러 발생: ' + err.message);
        }
    });

    // Login Modal Handlers
    const loginModal = document.getElementById('loginModal');
    document.getElementById('btnLoginModal').addEventListener('click', () => loginModal.classList.add('active'));
    document.getElementById('btnCloseLoginModal').addEventListener('click', () => loginModal.classList.remove('active'));

    document.getElementById('btnSubmitLogin').addEventListener('click', async () => {
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPass').value;
        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (data.success) {
                currentUser = data.user;
                updateUserUI();
                alert(`환영합니다 ${currentUser.name}님! 로그인 되었습니다.`);
                loginModal.classList.remove('active');
            } else {
                alert(data.message);
            }
        } catch (err) {
            alert('로그인 실패: ' + err.message);
        }
    });

    // User Whitelist Management Modal Handlers
    const userMgmtModal = document.getElementById('userMgmtModal');
    btnOpenUserMgmt.addEventListener('click', () => {
        userMgmtModal.classList.add('active');
        loadWhitelistedUsers();
    });
    document.getElementById('btnCloseUserMgmtModal').addEventListener('click', () => userMgmtModal.classList.remove('active'));

    document.getElementById('btnSubmitAddUser').addEventListener('click', async () => {
        const payload = {
            email: document.getElementById('newUserEmail').value.trim(),
            password: document.getElementById('newUserPass').value.trim(),
            name: document.getElementById('newUserName').value.trim(),
            role: document.getElementById('newUserRole').value
        };

        if (!payload.email || !payload.password || !payload.name) {
            return alert('이메일, 비밀번호, 이름은 필수 입력 항목입니다.');
        }

        try {
            const res = await fetch('/api/auth/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                alert(data.message);
                document.getElementById('newUserEmail').value = '';
                document.getElementById('newUserPass').value = '';
                document.getElementById('newUserName').value = '';
                loadWhitelistedUsers();
            } else {
                alert(data.message);
            }
        } catch (err) {
            alert('허가 계정 추가 실패: ' + err.message);
        }
    });

    // Asset Management Modal Handlers
    const assetModal = document.getElementById('assetModal');
    document.getElementById('btnOpenAddAssetModal').addEventListener('click', () => {
        document.getElementById('assetEditId').value = '';
        document.getElementById('assetTicker').value = '';
        document.getElementById('assetName').value = '';
        document.getElementById('assetQuantity').value = '';
        document.getElementById('assetBuyPrice').value = '';
        document.getElementById('assetCurrentPrice').value = '';
        document.getElementById('assetModalTitle').innerText = '보유 자산 등록';
        assetModal.classList.add('active');
    });
    document.getElementById('btnCloseAssetModal').addEventListener('click', () => assetModal.classList.remove('active'));

    document.getElementById('btnSubmitAsset').addEventListener('click', async () => {
        const editId = document.getElementById('assetEditId').value;
        const payload = {
            market: document.getElementById('assetMarket').value,
            ticker: document.getElementById('assetTicker').value.trim(),
            name: document.getElementById('assetName').value.trim(),
            asset_type: document.getElementById('assetType').value,
            quantity: document.getElementById('assetQuantity').value,
            buy_price: document.getElementById('assetBuyPrice').value,
            current_price: document.getElementById('assetCurrentPrice').value
        };

        if (!payload.ticker || !payload.name || !payload.quantity || !payload.buy_price) {
            return alert('종목 티커, 종목명, 수량, 매수 평단가는 필수 입력 항목입니다.');
        }

        try {
            const url = editId ? `/api/portfolio/assets/${editId}` : '/api/portfolio/assets';
            const method = editId ? 'PUT' : 'POST';
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                alert(data.message);
                assetModal.classList.remove('active');
                loadPortfolioCockpit();
                loadDailyBriefing();
            } else {
                alert(data.message);
            }
        } catch (err) {
            alert('자산 저장 실패: ' + err.message);
        }
    });

    // Initialize App
    updateUserUI();
    loadDailyBriefing();
    loadWatchlist();
    loadPortfolioCockpit();
    runCompanyDecoder('NVDA');
    runStoryReader('AAPL');
    runReverseDcf();
});
