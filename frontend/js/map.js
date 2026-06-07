// Interactive Map & State Projections Module
(function() {
    let stateVoteChartInstance = null;
    let selectedState = null;

    // Render interactive state tiles and populate selector
    function renderMap() {
        const prediction = window.voteCast.state.nationalPrediction;
        if (!prediction || !prediction.state_wise) return;

        const container = document.getElementById('states-grid-map');
        const selector = document.getElementById('region-selector');
        if (!container) return;

        // Clear previous tiles
        container.innerHTML = '';
        
        // Setup dropdown options if empty
        const hasOptions = selector.options.length > 1;

        // Sort states by total seats descending
        const statesData = [...prediction.state_wise].sort((a, b) => b.total_seats - a.total_seats);

        statesData.forEach(state => {
            // Create tile
            const tile = document.createElement('div');
            tile.className = `state-tile winner-${state.winner.toLowerCase().replace(/[^a-z0-9]/g, '')}`;
            tile.setAttribute('data-state', state.state);
            tile.innerHTML = `
                <h4>${state.state}</h4>
                <span class="state-tile-seats">${state.total_seats} Seats</span>
                <span class="state-tile-winner" style="color: ${window.voteCast.state.partyColors[state.winner]}">${state.winner}</span>
            `;

            // Click listener
            tile.addEventListener('click', () => {
                selectState(state.state);
            });

            container.appendChild(tile);

            // Add selector option if not already populated
            if (!hasOptions) {
                const opt = document.createElement('option');
                opt.value = state.state;
                opt.textContent = `${state.state} (${state.total_seats} Seats)`;
                selector.appendChild(opt);
            }
        });

        // Setup selector change listener
        if (!hasOptions) {
            selector.addEventListener('change', (e) => {
                const val = e.target.value;
                if (val) {
                    selectState(val);
                } else {
                    resetStateDetail();
                }
            });
        }
    }

    // Select a state and show detailed prediction panel
    function selectState(stateName) {
        selectedState = stateName;
        
        // Highlight active tile
        document.querySelectorAll('.state-tile').forEach(tile => {
            tile.classList.remove('selected');
            if (tile.getAttribute('data-state') === stateName) {
                tile.classList.add('selected');
            }
        });

        // Sync dropdown
        const selector = document.getElementById('region-selector');
        if (selector) selector.value = stateName;

        const prediction = window.voteCast.state.nationalPrediction;
        if (!prediction || !prediction.state_wise) return;

        const stateData = prediction.state_wise.find(s => s.state === stateName);
        if (!stateData) return;

        // Display contents
        const placeholder = document.querySelector('.detail-placeholder');
        const content = document.getElementById('state-detail-content');
        
        if (placeholder) placeholder.classList.add('hidden');
        if (content) content.classList.remove('hidden');

        // Populate elements
        document.getElementById('detail-state-name').textContent = stateData.state;
        document.getElementById('detail-state-seats').textContent = `${stateData.total_seats} Seats`;
        
        const winnerEl = document.getElementById('detail-state-winner');
        winnerEl.textContent = stateData.winner;
        winnerEl.style.color = window.voteCast.state.partyColors[stateData.winner] || '#ffffff';
        
        document.getElementById('detail-state-confidence').textContent = `${stateData.confidence}%`;
        document.getElementById('detail-state-conf-bar').style.width = `${stateData.confidence}%`;

        // Render seats breakdown progress list
        const seatsList = document.getElementById('detail-state-seats-list');
        seatsList.innerHTML = '';

        const partyColors = window.voteCast.state.partyColors;
        const seats = stateData.seats;
        
        // Sort parties by seats won in this state
        const stateParties = Object.keys(seats)
            .filter(p => seats[p] > 0)
            .sort((a, b) => seats[b] - seats[a]);

        stateParties.forEach(party => {
            const count = seats[party];
            const pct = (count / stateData.total_seats) * 100;
            const color = partyColors[party] || '#777777';

            seatsList.innerHTML += `
                <div class="party-progress-item">
                    <span class="party-progress-label">${party}</span>
                    <div class="party-progress-bar-wrapper">
                        <div class="party-progress-bar" style="width: ${pct}%; background-color: ${color}"></div>
                    </div>
                    <span class="party-progress-count">${count}</span>
                </div>
            `;
        });

        // Initialize state-wise vote share chart
        renderStateVoteChart(stateData);
    }

    // Render minor state vote share comparison
    function renderStateVoteChart(stateData) {
        const ctx = document.getElementById('stateVoteChart');
        if (!ctx) return;

        if (stateVoteChartInstance) {
            stateVoteChartInstance.destroy();
        }

        const partyColors = window.voteCast.state.partyColors;
        const votes = stateData.vote_shares;
        
        // Filter out parties with extremely low vote shares (<1%)
        const activeParties = Object.keys(votes)
            .filter(p => votes[p] > 1.0)
            .sort((a, b) => votes[b] - votes[a]);

        const voteValues = activeParties.map(p => votes[p]);
        const colors = activeParties.map(p => partyColors[p] || '#777777');

        stateVoteChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: activeParties,
                datasets: [{
                    data: voteValues,
                    backgroundColor: colors,
                    borderRadius: 4,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` Vote Share: ${context.parsed.toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        border: { display: false },
                        ticks: {
                            callback: function(value) { return value + '%'; }
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // Reset details panel state
    function resetStateDetail() {
        selectedState = null;
        document.querySelectorAll('.state-tile').forEach(t => t.classList.remove('selected'));
        
        const placeholder = document.querySelector('.detail-placeholder');
        const content = document.getElementById('state-detail-content');
        
        if (placeholder) placeholder.classList.remove('hidden');
        if (content) content.classList.add('hidden');
        if (stateVoteChartInstance) {
            stateVoteChartInstance.destroy();
            stateVoteChartInstance = null;
        }
    }

    // Export module globally
    window.voteCastMap = {
        renderMap: renderMap,
        selectState: selectState,
        resetStateDetail: resetStateDetail
    };
})();
