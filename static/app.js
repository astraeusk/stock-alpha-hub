/**
 * AlphaHub - Frontend Application Logic v2.5
 * Domestic / International Dual Market Filtering & Custom Watchlist Management
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
                pageTitle.innerText = '1.5층: 포트폴리오 콕핏 (Portfolio Cockpit)';
                pageSubtext.innerText = 'HHI 집중도 지수, ETF 경유 중복 노출 및 환율 감응도 평가';
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
                    <div class="trigger-item">
                        <div class="trig-info">
                            <h4>
                                <span class="badge ${trig.market === 'domestic' ? 'up' : 'normal'}">${trig.market === 'domestic' ? '🇰🇷 국내' : '🇺🇸 해외'}</span>
                                [${trig.ticker}] ${trig.name}
                            </h4>
                            <p>${trig.reason}</p>
                            <p style="font-size:0.75rem; color:var(--color-subtext0); margin-top:2px;">↳ ${trig.action_desc}</p>
                        </div>
                        <div class="trig-action">
                            <span class="skill-pill"><i class="fa-solid fa-cube"></i> ${trig.recommended_skill}</span>
                            <button class="btn-primary btn-sm btn-run-trig" data-ticker="${trig.ticker}" data-skill="${trig.recommended_skill}">
                                스킬 실행 <i class="fa-solid fa-arrow-right"></i>
                            </button>
                        </div>
                    </div>
                `).join('');

                document.querySelectorAll('.btn-run-trig').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const ticker = btn.getAttribute('data-ticker');
                        const skill = btn.getAttribute('data-skill');
                        if (skill.includes('가격 판독기') || skill.includes('Price')) {
                            document.getElementById('dcfTicker').value = ticker;
                            switchTab('tab-price');
                            runReverseDcf();
                        } else if (skill.includes('스토리') || skill.includes('Story')) {
                            document.getElementById('storyTickerInput').value = ticker;
                            switchTab('tab-story');
                            runStoryReader(ticker);
                        } else {
                            document.getElementById('decoderTickerInput').value = ticker;
                            switchTab('tab-decoder');
                            runCompanyDecoder(ticker);
                        }
                    });
                });
            }

            loadKakaoMessages();
        } catch (err) {
            console.error('Error loading briefing:', err);
        }
    }

    // 2. Fetch Watchlist (관심 종목)
    async function loadWatchlist() {
        try {
            const res = await fetch(`/api/watchlist?market=${currentMarketFilter}`);
            const items = await res.json();

            if (items.length === 0) {
                watchlistContainer.innerHTML = `<div class="content-card col-2 text-sub">등록된 관심 종목이 없습니다. 우측 상단의 '+ 관심 종목 추가' 버튼을 눌러보세요.</div>`;
                return;
            }

            watchlistContainer.innerHTML = items.map(item => `
                <div class="watchlist-card">
                    <div class="watch-header">
                        <div class="watch-title">
                            <h4>
                                <span class="badge ${item.market === 'domestic' ? 'up' : 'normal'}">${item.market === 'domestic' ? '🇰🇷 국내' : '🇺🇸 해외'}</span>
                                ${item.name} (${item.ticker})
                            </h4>
                            <span style="font-size:0.75rem; color:var(--color-overlay0);">${item.sector}</span>
                        </div>
                        <div class="watch-price-box">
                            <div class="watch-price" style="color:${item.change_pct.includes('-') ? 'var(--color-red)' : 'var(--color-green)'};">
                                ${item.currency === 'USD' ? '$' : ''}${item.price.toLocaleString()} ${item.currency === 'KRW' ? '원' : ''}
                            </div>
                            <span class="badge ${item.change_pct.includes('-') ? 'down' : 'up'}">${item.change_pct}</span>
                        </div>
                    </div>
                    <div class="watch-body">
                        <p><i class="fa-solid fa-note-sticky text-yellow"></i> ${item.memo}</p>
                    </div>
                    <div class="watch-actions">
                        <button class="btn-sm btn-outline btn-watch-skill" data-ticker="${item.ticker}" data-type="decoder">
                            <i class="fa-solid fa-microscope"></i> 기업해독기
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

            // Attach Skill & Delete Handlers
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

    // 4. Load Portfolio Cockpit
    async function loadPortfolioCockpit() {
        try {
            const res = await fetch(`/api/portfolio/cockpit?market=${currentMarketFilter}`);
            const data = await res.json();

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
                        backgroundColor: ['#cba6f7', '#89b4fa', '#a6e3a1', '#f9e2af'],
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

                    <div class="card-grid col-2 mb-4">
                        <div>
                            <h4 style="font-size:0.9rem; color:var(--color-mauve); margin-bottom:8px;"><i class="fa-solid fa-chart-bar"></i> 사업 부문별 매출 비중</h4>
                            <div class="table-responsive">
                                <table class="data-table">
                                    <thead><tr><th>부문 (Segment)</th><th>비중 (%)</th></tr></thead>
                                    <tbody>
                                        ${data.segment_revenue.map(s => `<tr><td>${s.segment}</td><td><strong>${s.share}%</strong></td></tr>`).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div>
                            <h4 style="font-size:0.9rem; color:var(--color-teal); margin-bottom:8px;"><i class="fa-solid fa-earth-americas"></i> 지역별 매출 분포</h4>
                            <div class="table-responsive">
                                <table class="data-table">
                                    <thead><tr><th>지역 (Region)</th><th>비중 (%)</th></tr></thead>
                                    <tbody>
                                        ${data.geo_revenue.map(g => `<tr><td>${g.region}</td><td><strong>${g.share}%</strong></td></tr>`).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <h4 style="font-size:0.9rem; color:var(--color-yellow); margin-bottom:8px;"><i class="fa-solid fa-key"></i> 업종 핵심 추적 KPI</h4>
                    <div class="card-grid col-4 mb-3">
                        ${data.kpis.map(k => `
                            <div class="metric-card">
                                <span class="m-label">${k.name}</span>
                                <span class="m-value" style="font-size:1.1rem; color:var(--color-mauve);">${k.value}</span>
                                <span class="badge success" style="width:fit-content;">${k.status}</span>
                            </div>
                        `).join('')}
                    </div>

                    <p style="font-size:0.75rem; color:var(--color-overlay0); text-align:right;">📌 문서 출처: ${data.source_doc}</p>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div class="content-card text-red">오류가 발생했습니다: ${err.message}</div>`;
        }
    }

    // 6. Run Story Reader Skill
    async function runStoryReader(ticker) {
        const container = document.getElementById('storyResultContainer');
        container.innerHTML = `<div class="content-card"><i class="fa-solid fa-spinner fa-spin text-flamingo"></i> [${ticker}] 최근 3개년 공시 및 어닝콜 문구 변화 대조 중...</div>`;

        try {
            const res = await fetch(`/api/stock/story/${ticker}`);
            const data = await res.json();

            container.innerHTML = `
                <div class="content-card mb-4">
                    <div class="card-header">
                        <h3>
                            <span class="badge ${data.market === 'domestic' ? 'up' : 'normal'}">${data.market === 'domestic' ? '🇰🇷 국내' : '🇺🇸 해외'}</span>
                            <i class="fa-solid fa-film text-flamingo"></i> [${data.ticker}] 3개년 변화 비교 및 톤변화 포착
                        </h3>
                        <span class="info-tag">${data.period}</span>
                    </div>

                    <h4 style="font-size:0.95rem; color:var(--color-mauve); margin-bottom:10px;"><i class="fa-solid fa-magnifying-glass-chart"></i> 주요 공시 문구 표현 변화 (Tone Shift)</h4>
                    <div class="trigger-list mb-4">
                        ${data.tone_changes.map(tc => `
                            <div class="trigger-item" style="flex-direction:column; align-items:flex-start;">
                                <div style="display:flex; justify-content:space-between; width:100%; font-size:0.85rem;">
                                    <strong style="color:var(--color-yellow);">${tc.topic}</strong>
                                    <span class="badge ${tc.shift.includes('Tone-Down') ? 'down' : 'up'}">${tc.shift}</span>
                                </div>
                                <p style="font-size:0.8rem; color:var(--color-subtext0); margin-top:4px;">❌ 과거: "${tc.old_text}"</p>
                                <p style="font-size:0.82rem; color:var(--color-text); margin-top:2px;">👉 변경: "${tc.new_text}"</p>
                            </div>
                        `).join('')}
                    </div>

                    <h4 style="font-size:0.95rem; color:var(--color-teal); margin-bottom:10px;"><i class="fa-solid fa-list-check"></i> 경영진 가이던스 이행 이력 (Guidance Track Record)</h4>
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead><tr><th>분기</th><th>약속 가이던스</th><th>실제 성과</th><th>결과</th></tr></thead>
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
            container.innerHTML = `<div class="content-card text-red">오류가 발생했습니다: ${err.message}</div>`;
        }
    }

    // 7. Run Reverse DCF Price Decoder
    async function runReverseDcf() {
        const container = document.getElementById('priceDecoderResult');
        container.innerHTML = `<div class="content-card"><i class="fa-solid fa-spinner fa-spin text-peach"></i> 역DCF 방정식을 통한 요구 성장률 계산 중...</div>`;

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
                        <h3><i class="fa-solid fa-balance-scale text-peach"></i> [${data.ticker}] 역DCF 요구 성장률 산출 결과</h3>
                        <span class="badge ${data.gap > 5 ? 'down' : 'success'}">${data.safety_assessment}</span>
                    </div>

                    <div class="card-grid col-2 mb-4">
                        <div class="metric-card" style="border-color:var(--color-peach);">
                            <span class="m-label"><i class="fa-solid fa-bullseye"></i> 시가총액 반영 필요 연간 FCF 성장률</span>
                            <span class="m-value text-peach" style="font-size:1.8rem;">연 +${data.implied_annual_growth}%</span>
                            <p class="m-desc">현재 주가 ${data.current_price}가 설명되기 위해 회사가 달성해야 하는 10년 성장률</p>
                        </div>
                        <div class="metric-card">
                            <span class="m-label"><i class="fa-solid fa-history"></i> 과거 5년 실제 FCF 성장률 (CAGR)</span>
                            <span class="m-value text-teal" style="font-size:1.8rem;">연 +${data.past_5y_cagr}%</span>
                            <p class="m-desc">실제 과거 실적 성장치와 요구 성장률의 갭: <strong class="${data.gap > 5 ? 'text-red' : 'text-green'}">${data.gap > 0 ? '+' : ''}${data.gap}%p</strong></p>
                        </div>
                    </div>

                    <div class="hhi-box mb-4" style="background:rgba(49, 50, 68, 0.4); padding:1rem; border-radius:12px;">
                        <h4 style="color:var(--color-mauve); font-size:0.9rem; margin-bottom:4px;"><i class="fa-solid fa-circle-info"></i> 가격 판독기 종합 가치 진단</h4>
                        <p style="font-size:0.88rem; color:var(--color-text);">${data.evaluation_summary}</p>
                    </div>

                    <h4 style="font-size:0.95rem; color:var(--color-sapphire); margin-bottom:10px;"><i class="fa-solid fa-table-cells"></i> WACC & 영구성장률 민감도 표 (Sensitivity Matrix)</h4>
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
    const openWatchModalBtns = [document.getElementById('btnOpenAddWatchlistModal'), document.getElementById('btnOpenAddWatchlistModal2')];
    
    openWatchModalBtns.forEach(b => {
        if (b) b.addEventListener('click', () => addWatchlistModal.classList.add('active'));
    });

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

    // Login Modal
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
                document.getElementById('userNameDisplay').innerText = currentUser.name;
                alert(`환영합니다 ${currentUser.name}님!`);
                loginModal.classList.remove('active');
            } else {
                alert(data.message);
            }
        } catch (err) {
            alert('로그인 실패: ' + err.message);
        }
    });

    // Initialize App
    loadDailyBriefing();
    loadWatchlist();
    runCompanyDecoder('NVDA');
    runStoryReader('AAPL');
    runReverseDcf();
});
