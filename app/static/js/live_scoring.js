/**
 * Live Scoring Module for Pickleball Tournament Platform
 * 
 * This JavaScript file handles real-time updates for tournament match scores
 * using polling to fetch updates from the server and update the display.
 */

class LiveScoring {
    /**
     * Initialize the live scoring system
     * @param {string} tournamentId - The ID of the tournament
     * @param {number} updateInterval - Polling interval in milliseconds (default: 15000 - 15 seconds)
     */
    constructor(tournamentId, updateInterval = 15000) {
        this.tournamentId = tournamentId;
        this.updateInterval = updateInterval;
        this.apiEndpoint = `/tournament/api/${tournamentId}/scores`;
        this.polling = null;
        this.lastUpdate = new Date();
        this.matchData = {};
    }

    /**
     * Start the polling for score updates
     */
    startPolling() {
        // Initial fetch
        this.fetchScores();
        
        // Set up interval for regular updates
        this.polling = setInterval(() => {
            this.fetchScores();
        }, this.updateInterval);
        
        // Display the last update time and start the timer
        this.updateLastUpdateTime();
        setInterval(() => {
            this.updateLastUpdateTime();
        }, 10000); // Update every 10 seconds
        
        console.log(`Live scoring started for tournament ${this.tournamentId}`);
    }

    /**
     * Stop polling for updates
     */
    stopPolling() {
        if (this.polling) {
            clearInterval(this.polling);
            this.polling = null;
            console.log('Live scoring stopped');
        }
    }

    /**
     * Fetch the latest scores from the server
     */
    fetchScores() {
        fetch(this.apiEndpoint)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.processScoreData(data);
                this.lastUpdate = new Date();
            })
            .catch(error => {
                console.error('Error fetching live scores:', error);
            });
    }

    /**
     * Process the score data and update the UI
     * @param {Array} data - The array of match data from the server
     */
    processScoreData(data) {
        data.forEach(match => {
            const matchId = match.match_id;
            const matchElement = document.getElementById(`match-${matchId}`);
            
            if (matchElement) {
                // Check if the data has changed before updating
                if (this.hasDataChanged(matchId, match)) {
                    this.updateMatchDisplay(matchElement, match);
                    
                    // Highlight the match that was updated with a pulsing effect
                    matchElement.classList.add('score-updated');
                    setTimeout(() => {
                        matchElement.classList.remove('score-updated');
                    }, 3000);
                    
                    // Store the updated data
                    this.matchData[matchId] = match;
                }
            }
        });
    }

    /**
     * Check if the match data has changed since the last update
     * @param {string} matchId - The ID of the match
     * @param {Object} newData - The new match data
     * @returns {boolean} True if the data has changed
     */
    hasDataChanged(matchId, newData) {
        if (!this.matchData[matchId]) {
            return true; // First update for this match
        }
        
        const oldData = this.matchData[matchId];
        
        // Compare score lengths
        if (oldData.scores.length !== newData.scores.length) {
            return true;
        }
        
        // Compare each score
        for (let i = 0; i < newData.scores.length; i++) {
            const oldScore = oldData.scores[i];
            const newScore = newData.scores[i];
            
            if (oldScore.player1_score !== newScore.player1_score || 
                oldScore.player2_score !== newScore.player2_score) {
                return true;
            }
        }
        
        return false;
    }

    /**
     * Update the match display with the latest scores
     * @param {HTMLElement} matchElement - The match container element
     * @param {Object} match - The match data
     */
    updateMatchDisplay(matchElement, match) {
        // Update player1 scores
        const player1ScoresContainer = matchElement.querySelector('.match-player1-scores');
        if (player1ScoresContainer) {
            let player1ScoreHtml = '<div class="flex space-x-3">';
            match.scores.forEach(score => {
                player1ScoreHtml += `
                    <div class="w-8 h-8 flex items-center justify-center ${score.player1_score > score.player2_score ? 'bg-green-100 text-green-800 font-bold' : 'bg-gray-100 text-gray-600'} rounded">
                        ${score.player1_score}
                    </div>
                `;
            });
            player1ScoreHtml += '</div>';
            player1ScoresContainer.innerHTML = player1ScoreHtml;
        }
        
        // Update player2 scores
        const player2ScoresContainer = matchElement.querySelector('.match-player2-scores');
        if (player2ScoresContainer) {
            let player2ScoreHtml = '<div class="flex space-x-3">';
            match.scores.forEach(score => {
                player2ScoreHtml += `
                    <div class="w-8 h-8 flex items-center justify-center ${score.player2_score > score.player1_score ? 'bg-green-100 text-green-800 font-bold' : 'bg-gray-100 text-gray-600'} rounded">
                        ${score.player2_score}
                    </div>
                `;
            });
            player2ScoreHtml += '</div>';
            player2ScoresContainer.innerHTML = player2ScoreHtml;
        }
        
        // Update match status if needed
        const statusElement = matchElement.querySelector('.match-status');
        if (statusElement) {
            // Determine if match is in progress based on scores
            const isInProgress = match.scores.length > 0;
            if (isInProgress) {
                statusElement.innerHTML = '<span class="text-orange-600">In Progress</span>';
            }
        }
    }

    /**
     * Update the "last updated" time display
     */
    updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById('last-update-time');
        if (lastUpdateElement) {
            const now = new Date();
            const timeDiff = Math.floor((now - this.lastUpdate) / 1000); // difference in seconds
            
            let timeText;
            if (timeDiff < 10) {
                timeText = 'Just now';
            } else if (timeDiff < 60) {
                timeText = `${timeDiff} seconds ago`;
            } else if (timeDiff < 120) {
                timeText = '1 minute ago';
            } else if (timeDiff < 3600) {
                timeText = `${Math.floor(timeDiff / 60)} minutes ago`;
            } else {
                timeText = `${Math.floor(timeDiff / 3600)} hours ago`;
            }
            
            lastUpdateElement.textContent = `Last updated: ${timeText}`;
        }
    }

    /**
     * Manual refresh of scores (for refresh button)
     */
    manualRefresh() {
        this.fetchScores();
        
        // Show refresh indicator
        const refreshButton = document.getElementById('refresh-scores-btn');
        if (refreshButton) {
            refreshButton.classList.add('refreshing');
            setTimeout(() => {
                refreshButton.classList.remove('refreshing');
            }, 1000);
        }
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', function() {
    const liveScoring = document.querySelector('.live-scoring');
    
    if (liveScoring) {
        const tournamentId = liveScoring.dataset.tournamentId;
        const scorer = new LiveScoring(tournamentId);
        scorer.startPolling();
        
        // Add manual refresh handler
        const refreshButton = document.getElementById('refresh-scores-btn');
        if (refreshButton) {
            refreshButton.addEventListener('click', function() {
                scorer.manualRefresh();
            });
        }
        
        // Clean up when leaving page
        window.addEventListener('beforeunload', function() {
            scorer.stopPolling();
        });
    }
});

// Add styles for the score update animation
document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes scoreUpdatePulse {
            0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.5); }
            70% { box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
            100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
        }
        
        .score-updated {
            animation: scoreUpdatePulse 2s 1;
        }
        
        #refresh-scores-btn.refreshing {
            animation: spin 1s linear;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
});