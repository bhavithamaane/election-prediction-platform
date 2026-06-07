// Chart visualizations module
(function() {
    let seatsChartInstance = null;
    let voteShareChartInstance = null;
    let simChartInstance = null;
    let historicalChartInstance = null;

    // Chart.js default styling updates for premium dark mode
    Chart.defaults.color = '#94a3b8'; // text-secondary
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
    Chart.defaults.plugins.tooltip.titleFont = { family: "'Outfit', sans-serif", weight: 'bold' };
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.08)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;

    // Initialize Dashboard Charts (Seats Bar and Vote Share Doughnut)
    function initDashboardCharts(prediction) {
        if (!prediction) return;
        
        const partyColors = window.voteCast.state.partyColors;
        const seatData = prediction.seats;
        const voteData = prediction.vote_shares;
        
        // Filter out parties with 0 seats from displaying in seatsChart
        const sortedParties = Object.keys(seatData)
            .filter(p => seatData[p] > 0 || voteData[p] > 1.0)
            .sort((a, b) => seatData[b] - seatData[a]);
            
        const seatValues = sortedParties.map(p => seatData[p]);
        const voteValues = sortedParties.map(p => voteData[p]);
        const colors = sortedParties.map(p => partyColors[p] || '#777777');

        // 1. Projected Seats Chart
        const seatsCtx = document.getElementById('seatsChart');
        if (seatsCtx) {
            if (seatsChartInstance) seatsChartInstance.destroy();
            seatsChartInstance = new Chart(seatsCtx, {
                type: 'bar',
                data: {
                    labels: sortedParties,
                    datasets: [{
                        label: 'Projected Seats',
                        data: seatValues,
                        backgroundColor: colors,
                        borderRadius: 8,
                        borderWidth: 0,
                        barThickness: 32
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y', // Horizontal bar chart
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return ` Seats: ${context.parsed.x} / 28`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            border: { dash: [5, 5] },
                            max: 28,
                            title: { display: true, text: 'Number of Seats (out of 28)' }
                        },
                        y: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        // 2. Vote Share Doughnut Chart
        const voteCtx = document.getElementById('voteShareChart');
        if (voteCtx) {
            if (voteShareChartInstance) voteShareChartInstance.destroy();
            
            // Map labels for vote shares (only display if vote share > 0.5%)
            const voteParties = Object.keys(voteData).filter(p => voteData[p] > 0.5);
            const voteShareValues = voteParties.map(p => voteData[p]);
            const voteColors = voteParties.map(p => partyColors[p] || '#777777');
            
            voteShareChartInstance = new Chart(voteCtx, {
                type: 'doughnut',
                data: {
                    labels: voteParties,
                    datasets: [{
                        data: voteShareValues,
                        backgroundColor: voteColors,
                        borderWidth: 2,
                        borderColor: '#0f172a',
                        hoverOffset: 12
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                padding: 20,
                                font: { size: 12 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return ` Vote Share: ${context.parsed.toFixed(1)}%`;
                                }
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
        }
    }

    // Update Swing Simulation outcome chart
    function updateSimChart(prediction) {
        if (!prediction) return;
        
        const partyColors = window.voteCast.state.partyColors;
        const seatData = prediction.seats;
        
        const sortedParties = Object.keys(seatData)
            .filter(p => seatData[p] > 0)
            .sort((a, b) => seatData[b] - seatData[a]);
            
        const seatValues = sortedParties.map(p => seatData[p]);
        const colors = sortedParties.map(p => partyColors[p] || '#777777');

        const simCtx = document.getElementById('simChart');
        if (simCtx) {
            if (simChartInstance) simChartInstance.destroy();
            simChartInstance = new Chart(simCtx, {
                type: 'bar',
                data: {
                    labels: sortedParties,
                    datasets: [{
                        label: 'Seats',
                        data: seatValues,
                        backgroundColor: colors,
                        borderRadius: 6,
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            border: { dash: [5, 5] },
                            max: 28,
                            title: { display: true, text: 'Projected Seats (out of 28)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    }

    // Initialize Historical Chart Comparison (2014, 2019, 2024 trends)
    function initHistoricalChart() {
        const histData = window.voteCast.state.historicalResults;
        if (!histData) return;
        
        const histCtx = document.getElementById('historicalChart');
        if (!histCtx || historicalChartInstance) return; // Only init once
        
        // Filter Karnataka data
        const karData = histData.filter(d => d.State === "Karnataka");
        
        // Extract years and parties
        const years = [2014, 2019, 2024];
        
        // Parties: BJP, INC, JD(S), Others
        const parties = ["BJP", "INC", "JD(S)", "Others"];
        const partyColors = window.voteCast.state.partyColors;
        
        const datasets = parties.map(party => {
            const seatsPerYear = years.map(year => {
                const record = karData.find(d => d.Year === year && d.PartyID === party);
                return record ? record.SeatsWon : 0;
            });
            
            return {
                label: party,
                data: seatsPerYear,
                borderColor: partyColors[party] || '#777777',
                backgroundColor: (partyColors[party] || '#777777') + '22', // transparent fill
                borderWidth: 3,
                tension: 0.3,
                fill: true,
                pointRadius: 6,
                pointHoverRadius: 8
            };
        });

        historicalChartInstance = new Chart(histCtx, {
            type: 'line',
            data: {
                labels: years.map(y => `${y} Election`),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { padding: 15 }
                    }
                },
                scales: {
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        border: { dash: [5, 5] },
                        title: { display: true, text: 'Seats Won' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // Export Charts Module Globally
    window.voteCastCharts = {
        initDashboardCharts: initDashboardCharts,
        updateSimChart: updateSimChart,
        initHistoricalChart: initHistoricalChart
    };
})();
