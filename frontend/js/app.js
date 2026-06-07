// Global App Controller
(function() {
    // App Configuration & Global State
    const AppState = {
        apiBase: window.location.origin,
        activeView: 'dashboard',
        nationalPrediction: null,
        historicalResults: null,
        polls: [],
        socialData: null,
        adminToken: localStorage.getItem('admin_token'),
        adminName: localStorage.getItem('admin_name'),
        adminRole: localStorage.getItem('admin_role'),
        partyColors: {
            "BJP": "#FF9933",
            "INC": "#19AAED",
            "JD(S)": "#006400",
            "Others": "#777777"
        }
    };

    // Initialize application
    function init() {
        setupRouting();
        checkLoginStatus();
        fetchInitialData();
        setupEventListeners();
    }

    // Single Page Routing
    function setupRouting() {
        const navItems = document.querySelectorAll('.nav-item');
        
        function handleRoute(hash) {
            let viewName = 'dashboard';
            if (hash) {
                const matched = hash.replace('#', '');
                const validViews = ['dashboard', 'map', 'simulation', 'historical', 'admin'];
                if (validViews.includes(matched)) {
                    viewName = matched;
                }
            }

            AppState.activeView = viewName;
            
            // Toggle view visibility
            document.querySelectorAll('.content-view').forEach(view => {
                view.classList.remove('active-view');
            });
            
            const targetView = document.getElementById(`view-${viewName}`);
            if (targetView) {
                targetView.classList.add('active-view');
            }

            // Update Navigation Menu Active State
            navItems.forEach(item => {
                item.classList.remove('active');
                if (item.getAttribute('data-view') === viewName) {
                    item.classList.add('active');
                }
            });

            // Update Top Header Title
            const titleMap = {
                'dashboard': 'Prediction Dashboard',
                'map': 'Interactive Election Map',
                'simulation': 'Swing Simulator Engine',
                'historical': 'Historical Election Trends',
                'admin': 'Admin Operations Panel'
            };
            document.getElementById('page-title').textContent = titleMap[viewName] || 'VoteCast';
            
            // Trigger specific page load actions
            if (viewName === 'map' && window.voteCastMap) {
                window.voteCastMap.renderMap();
            }
            if (viewName === 'historical' && window.voteCastCharts) {
                window.voteCastCharts.initHistoricalChart();
            }
        }

        // Listen for URL hash changes
        window.addEventListener('hashchange', () => {
            handleRoute(window.location.hash);
        });

        // Trigger initial route
        handleRoute(window.location.hash);
    }

    // Check Login Status & Update UI Badges
    function checkLoginStatus() {
        const widget = document.getElementById('user-status-widget');
        if (AppState.adminToken) {
            widget.innerHTML = `
                <span class="status-badge" style="color: #10b981; background: rgba(16, 185, 129, 0.08); border-color: rgba(16, 185, 129, 0.2)">
                    <i class="fa-solid fa-user-shield"></i> ${AppState.adminRole}: ${AppState.adminName}
                </span>
            `;
            
            // Show admin panel details and hide login
            const loginBox = document.getElementById('admin-login-box');
            const dashboardBox = document.getElementById('admin-dashboard-box');
            if (loginBox) loginBox.classList.add('hidden');
            if (dashboardBox) {
                dashboardBox.classList.remove('hidden');
                document.getElementById('admin-user-name').textContent = AppState.adminName;
            }
        } else {
            widget.innerHTML = `
                <span class="status-badge">
                    <i class="fa-solid fa-globe"></i> Public View Mode
                </span>
            `;
            const loginBox = document.getElementById('admin-login-box');
            const dashboardBox = document.getElementById('admin-dashboard-box');
            if (loginBox) loginBox.classList.remove('hidden');
            if (dashboardBox) dashboardBox.classList.add('hidden');
        }
    }

    // Fetch Initial Datasets
    async function fetchInitialData() {
        try {
            // Fetch National Prediction
            const predResponse = await fetch(`${AppState.apiBase}/api/prediction/national`);
            if (predResponse.ok) {
                AppState.nationalPrediction = await predResponse.json();
                updateDashboardMetrics();
                
                // Initialize national dashboard charts
                if (window.voteCastCharts) {
                    window.voteCastCharts.initDashboardCharts(AppState.nationalPrediction);
                }
            } else {
                console.error("Failed to load national predictions.");
            }

            // Fetch Polls
            const pollsResponse = await fetch(`${AppState.apiBase}/api/polls`);
            if (pollsResponse.ok) {
                AppState.polls = await pollsResponse.json();
                populatePollsTable();
            }

            // Fetch Historical
            const histResponse = await fetch(`${AppState.apiBase}/api/historical`);
            if (histResponse.ok) {
                AppState.historicalResults = await histResponse.json();
            }
        } catch (error) {
            console.error("Connection error while fetching initial datasets:", error);
            showOfflineNotification();
        }

        // Fetch real-time social data separately (non-blocking)
        fetchSocialPulse();

        // Auto-refresh social data every 5 minutes
        setInterval(fetchSocialPulse, 5 * 60 * 1000);
    }

    // ── Real-Time Social Pulse ─────────────────────────────────────────────

    async function fetchSocialPulse(forceRefresh = false) {
        const refreshBtn = document.getElementById('btn-refresh-social');
        if (refreshBtn) refreshBtn.classList.add('spinning');

        try {
            const url = `${AppState.apiBase}/api/social/realtime${forceRefresh ? '?force_refresh=true' : ''}`;
            const resp = await fetch(url);
            if (!resp.ok) throw new Error('Social API returned ' + resp.status);
            const data = await resp.json();
            AppState.socialData = data;
            renderSocialPulse(data);
        } catch (err) {
            console.error('Social pulse fetch failed:', err);
            // Show error state in widget
            const container = document.getElementById('pulse-bars-container');
            if (container) {
                container.innerHTML = '<p style="color: var(--text-secondary); font-size: 13px; padding: 8px 0;"><i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b"></i> Could not fetch live social data. Predictions use historical fallback.</p>';
            }
        } finally {
            if (refreshBtn) refreshBtn.classList.remove('spinning');
        }
    }

    function renderSocialPulse(data) {
        const scores  = data.scores  || {};
        const news    = data.news    || {};
        const sources = data.sources || [];
        const fetchedAt = data.fetched_at || '';
        const cached  = data.cached;

        // Update source tag
        const sourceEl = document.getElementById('pulse-sources');
        if (sourceEl) {
            const labels = [];
            if (sources.includes('google_trends'))  labels.push('<i class="fa-brands fa-google"></i> Trends');
            if (sources.includes('google_news'))    labels.push('<i class="fa-solid fa-newspaper"></i> News');
            if (sources.includes('historical_fallback')) labels.push('<i class="fa-solid fa-database"></i> Fallback');
            sourceEl.innerHTML = labels.join(' · ');
        }

        // Update timestamp
        const updatedEl = document.getElementById('pulse-updated');
        if (updatedEl && fetchedAt) {
            const t = new Date(fetchedAt);
            const timeStr = t.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
            updatedEl.innerHTML = `<i class="fa-solid fa-clock"></i> Updated ${timeStr}${cached ? ' (cached)' : ''}`;
        }

        // Render party score bars
        const container = document.getElementById('pulse-bars-container');
        if (!container) return;

        const parties  = ['BJP', 'INC', 'JD(S)', 'Others'];
        const maxScore = Math.max(...parties.map(p => scores[p] || 0), 1);

        container.innerHTML = parties.map(party => {
            const score = scores[party] || 0;
            const color = AppState.partyColors[party] || '#777';
            const pct   = Math.min(100, (score / maxScore) * 100).toFixed(1);
            const trend = score > 30 ? '▲' : score > 15 ? '—' : '▼';
            const trendClass = score > 30 ? 'sentiment-positive' : score > 15 ? 'sentiment-neutral' : 'sentiment-negative';

            return `
            <div class="pulse-bar-row">
                <span class="pulse-party-label" style="color:${color}">${party}</span>
                <div class="pulse-bar-track">
                    <div class="pulse-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,${color}aa,${color})"></div>
                </div>
                <span class="pulse-score-label" style="color:${color}">${score.toFixed(1)}</span>
                <span class="pulse-trend-icon ${trendClass}">${trend}</span>
            </div>`;
        }).join('');

        // Render news headlines if available
        const newsContainer = document.getElementById('pulse-news-container');
        const newsList      = document.getElementById('pulse-news-list');
        if (newsContainer && newsList) {
            if (news && Object.keys(news).length > 0) {
                const allHeadlines = [];
                for (const [party, nData] of Object.entries(news)) {
                    if (nData) {
                        (nData.headlines || []).slice(0, 2).forEach(h => {
                            allHeadlines.push({ party, ...h });
                        });
                    }
                }

                if (allHeadlines.length > 0) {
                    newsList.innerHTML = allHeadlines.map(h => {
                        const color = AppState.partyColors[h.party] || '#777';
                        const polarity = h.polarity || 0;
                        const sentClass = polarity > 0.05 ? 'sentiment-positive' : polarity < -0.05 ? 'sentiment-negative' : 'sentiment-neutral';
                        const sentLabel = polarity > 0.05 ? '+ Positive' : polarity < -0.05 ? '− Negative' : '· Neutral';

                        return `
                        <div class="news-item">
                            <span class="news-party-dot" style="background:${color}"></span>
                            <span>${h.title}</span>
                            <span class="news-sentiment ${sentClass}">${sentLabel}</span>
                        </div>`;
                    }).join('');
                    newsContainer.style.display = 'block';
                } else {
                    newsContainer.style.display = 'none';
                }
            } else {
                newsContainer.style.display = 'none';
            }
        }
    }

    // Update National Metrics on Dashboard Page
    function updateDashboardMetrics() {
        if (!AppState.nationalPrediction) return;
        
        const data = AppState.nationalPrediction;
        
        // Update winner
        const winnerEl = document.getElementById('projected-winner');
        const winnerSubEl = document.getElementById('projected-winner-sub');
        
        winnerEl.textContent = data.winner;
        winnerEl.style.color = AppState.partyColors[data.winner] || '#ffffff';
        
        const winnerSeats = data.seats[data.winner] || 0;
        winnerSubEl.innerHTML = `Projected to win <strong>${winnerSeats}</strong> seats (Majority is 15)`;
        
        // Update confidence
        const confidenceEl = document.getElementById('confidence-score');
        const confidenceBar = document.getElementById('confidence-bar');
        
        confidenceEl.textContent = `${data.confidence}%`;
        confidenceBar.style.width = `${data.confidence}%`;
    }

    // Populate Polls Table on Dashboard View
    function populatePollsTable() {
        const tbody = document.getElementById('polls-table-body');
        if (!tbody) return;
        
        if (AppState.polls.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center">No opinion polls seeded. Log in as admin to upload.</td></tr>`;
            return;
        }

        tbody.innerHTML = AppState.polls.map(poll => {
            const share = poll.PartyVoteShare || {};
            const bjp = share.BJP ? `${(share.BJP * 100).toFixed(1)}%` : '-';
            const inc = share.INC ? `${(share.INC * 100).toFixed(1)}%` : '-';
            const jds = share['JD(S)'] ? `${(share['JD(S)'] * 100).toFixed(1)}%` : '-';
            const others = share.Others ? `${(share.Others * 100).toFixed(1)}%` : '-';
            
            return `
                <tr>
                    <td><strong>${poll.Agency}</strong></td>
                    <td>${poll.Date}</td>
                    <td>${poll.SampleSize.toLocaleString()}</td>
                    <td style="color: #FF9933; font-weight: 600;">${bjp}</td>
                    <td style="color: #19AAED; font-weight: 600;">${inc}</td>
                    <td style="color: #006400; font-weight: 600;">${jds}</td>
                    <td style="color: #777777; font-weight: 600;">${others}</td>
                </tr>
            `;
        }).join('');
    }

    // Local Event Listeners
    function setupEventListeners() {
        // Logout handler
        const logoutBtn = document.getElementById('btn-admin-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                localStorage.removeItem('admin_token');
                localStorage.removeItem('admin_name');
                localStorage.removeItem('admin_role');
                AppState.adminToken = null;
                AppState.adminName = null;
                AppState.adminRole = null;
                checkLoginStatus();
                document.getElementById('upload-poll-form').reset();
                window.location.hash = '#dashboard';
            });
        }

        // Manual social refresh button
        const refreshSocialBtn = document.getElementById('btn-refresh-social');
        if (refreshSocialBtn) {
            refreshSocialBtn.addEventListener('click', () => fetchSocialPulse(true));
        }
    }

    // Helper for error state
    function showOfflineNotification() {
        const header = document.querySelector('.top-header');
        const errDiv = document.createElement('div');
        errDiv.className = 'error-message';
        errDiv.style.margin = '10px 0';
        errDiv.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Server connection failed. Predictions are running in offline fallback mode.';
        header.parentNode.insertBefore(errDiv, header.nextSibling);
    }

    // Export AppState globally so other scripts can access it
    window.voteCast = {
        state: AppState,
        checkLoginStatus: checkLoginStatus,
        fetchInitialData: fetchInitialData
    };

    // Allow admin.js to read AppState
    window.getAppState = () => AppState;

    // Run on script load
    document.addEventListener('DOMContentLoaded', init);
})();
