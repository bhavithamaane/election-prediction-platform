// Admin Features & Swing Simulation Module
(function() {
    // Reference shortcut to AppState
    const getAppState = () => window.voteCast.state;

    function init() {
        setupAdminLogin();
        setupPollUpload();
        setupModelRetraining();
        setupSimulationSliders();
    }

    // --- Admin Authentication ---
    function setupAdminLogin() {
        const loginForm = document.getElementById('admin-login-form');
        if (!loginForm) return;

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('admin-email').value;
            const password = document.getElementById('admin-password').value;
            const errorMsg = document.getElementById('login-error-msg');

            errorMsg.classList.add('hidden');

            try {
                const response = await fetch(`${getAppState().apiBase}/api/admin/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();

                if (response.ok) {
                    // Save admin session
                    localStorage.setItem('admin_token', data.access_token);
                    localStorage.setItem('admin_name', data.name);
                    localStorage.setItem('admin_role', data.role);

                    getAppState().adminToken = data.access_token;
                    getAppState().adminName = data.name;
                    getAppState().adminRole = data.role;

                    // Update UI status badges
                    window.voteCast.checkLoginStatus();
                    loginForm.reset();
                } else {
                    errorMsg.textContent = data.detail || 'Authentication failed.';
                    errorMsg.classList.remove('hidden');
                }
            } catch (error) {
                console.error("Login connection error:", error);
                errorMsg.textContent = 'Network error. Cannot reach API server.';
                errorMsg.classList.remove('hidden');
            }
        });
    }

    // --- Upload Opinion Polls ---
    function setupPollUpload() {
        const uploadForm = document.getElementById('upload-poll-form');
        if (!uploadForm) return;

        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const statusMsg = document.getElementById('upload-status-msg');
            statusMsg.className = 'status-message hidden';

            const agency = document.getElementById('poll-agency').value;
            const sampleSize = parseInt(document.getElementById('poll-sample-size').value);
            const date = document.getElementById('poll-date').value;
            
            const bjp = parseFloat(document.getElementById('poll-bjp').value);
            const inc = parseFloat(document.getElementById('poll-inc').value);
            const jds = parseFloat(document.getElementById('poll-jds').value);
            const others = parseFloat(document.getElementById('poll-others').value);

            // Basic validation
            const sum = bjp + inc + jds + others;
            if (Math.abs(sum - 100) > 2) {
                statusMsg.textContent = `Warning: Vote shares sum to ${sum.toFixed(1)}%. It should equal 100% (+/- 2%).`;
                statusMsg.classList.add('error');
                statusMsg.classList.remove('hidden');
                return;
            }

            const formData = new FormData();
            formData.append('agency', agency);
            formData.append('sample_size', sampleSize);
            formData.append('date', date);
            formData.append('bjp', bjp);
            formData.append('inc', inc);
            formData.append('jds', jds);
            formData.append('others', others);
            formData.append('token', getAppState().adminToken);

            try {
                const response = await fetch(`${getAppState().apiBase}/api/admin/polls/upload`, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    statusMsg.textContent = 'Opinion poll uploaded & seeded successfully!';
                    statusMsg.classList.add('success');
                    statusMsg.classList.remove('hidden');
                    uploadForm.reset();
                    
                    // Reload polls in background
                    window.voteCast.fetchInitialData();
                } else {
                    statusMsg.textContent = data.detail || 'Upload failed.';
                    statusMsg.classList.add('error');
                    statusMsg.classList.remove('hidden');
                }
            } catch (error) {
                console.error("Upload connection error:", error);
                statusMsg.textContent = 'Connection error. Check backend server status.';
                statusMsg.classList.add('error');
                statusMsg.classList.remove('hidden');
            }
        });
    }

    // --- Retrain Prediction Engine Model ---
    function setupModelRetraining() {
        const retrainBtn = document.getElementById('btn-retrain-model');
        if (!retrainBtn) return;

        retrainBtn.addEventListener('click', async () => {
            const statusMsg = document.getElementById('retrain-status-msg');
            statusMsg.className = 'status-message hidden';
            
            retrainBtn.disabled = true;
            retrainBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Training ML Pipelines...';

            try {
                const response = await fetch(`${getAppState().apiBase}/api/admin/model/retrain?token=${getAppState().adminToken}`, {
                    method: 'POST'
                });

                const data = await response.json();

                if (response.ok) {
                    statusMsg.textContent = data.message;
                    statusMsg.classList.add('success');
                    statusMsg.classList.remove('hidden');
                } else {
                    statusMsg.textContent = data.detail || 'Retraining failed.';
                    statusMsg.classList.add('error');
                    statusMsg.classList.remove('hidden');
                }
            } catch (error) {
                console.error("Retrain connection error:", error);
                statusMsg.textContent = 'Connection error. Check backend status.';
                statusMsg.classList.add('error');
                statusMsg.classList.remove('hidden');
            } finally {
                retrainBtn.disabled = false;
                retrainBtn.innerHTML = '<i class="fa-solid fa-gears"></i> Retrain ML Pipeline';
            }
        });
    }

    // --- Win Prediction Simulation Sliders ---
    function setupSimulationSliders() {
        const sliders = {
            "BJP": document.getElementById('slider-bjp'),
            "INC": document.getElementById('slider-inc'),
            "JD(S)": document.getElementById('slider-jds'),
            "Others": document.getElementById('slider-others')
        };

        const values = {
            "BJP": document.getElementById('val-bjp'),
            "INC": document.getElementById('val-inc'),
            "JD(S)": document.getElementById('val-jds'),
            "Others": document.getElementById('val-others')
        };

        const recalcBtn = document.getElementById('btn-recalculate');
        const resetBtn = document.getElementById('btn-reset-sliders');
        const warningEl = document.getElementById('slider-total-warning');
        const totalValEl = document.getElementById('slider-total-value');

        if (!recalcBtn) return;

        // Helper to update slider labels and validate total
        function updateSliderLabels() {
            let total = 0;
            for (let party in sliders) {
                if (sliders[party]) {
                    const val = parseFloat(sliders[party].value);
                    total += val;
                    values[party].textContent = `${val}%`;
                }
            }
            // Show warning if total != 100
            if (warningEl && totalValEl) {
                totalValEl.textContent = total;
                if (Math.abs(total - 100) > 2) {
                    warningEl.style.display = 'block';
                    warningEl.style.color = '#ef4444';
                } else {
                    warningEl.style.display = 'none';
                }
            }
        }

        // Gather slider values and post to API
        async function runSimulation() {
            recalcBtn.disabled = true;
            recalcBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Recalculating...';

            const userPercentages = {};
            for (let party in sliders) {
                if (sliders[party]) {
                    userPercentages[party] = parseFloat(sliders[party].value);
                }
            }

            // Social popularity defaults (mock)
            const socialPopularity = {
                "BJP": 46, "INC": 44, "JD(S)": 7, "Others": 3
            };

            const payload = {
                user_percentages: userPercentages,
                social_popularity: socialPopularity
            };

            try {
                const response = await fetch(`${getAppState().apiBase}/api/prediction/simulate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    const data = await response.json();
                    
                    // Update simulation dashboard view
                    const winnerEl = document.getElementById('sim-winner');
                    const seatsEl = document.getElementById('sim-winner-seats');

                    winnerEl.textContent = data.winner;
                    winnerEl.style.color = getAppState().partyColors[data.winner] || '#ffffff';
                    
                    const winnerSeats = data.seats[data.winner] || 0;
                    seatsEl.textContent = `${winnerSeats} Seats Projected`;

                    // Redraw simulation chart
                    if (window.voteCastCharts) {
                        window.voteCastCharts.updateSimChart(data);
                    }
                } else {
                    console.error("Simulation endpoint error.");
                }
            } catch (error) {
                console.error("Simulation error:", error);
            } finally {
                recalcBtn.disabled = false;
                recalcBtn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Run Simulation';
            }
        }

        // Add slider input change events
        for (let party in sliders) {
            if (sliders[party]) {
                sliders[party].addEventListener('input', updateSliderLabels);
            }
        }

        // Recalculate seats click
        recalcBtn.addEventListener('click', runSimulation);

        // Reset sliders
        resetBtn.addEventListener('click', () => {
            if (sliders['BJP']) sliders['BJP'].value = 46;
            if (sliders['INC']) sliders['INC'].value = 44;
            if (sliders['JD(S)']) sliders['JD(S)'].value = 7;
            if (sliders['Others']) sliders['Others'].value = 3;
            updateSliderLabels();
            runSimulation();
        });

        // Run initial simulation on load
        updateSliderLabels();
        setTimeout(runSimulation, 500);
    }

    // Run on script load
    document.addEventListener('DOMContentLoaded', init);
})();
