/**
 * Main JavaScript file for the Pickleball Tournament Platform
 */

// DOM Content Loaded Event
document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile menu
    initMobileMenu();
    
    // Initialize flash message dismissal
    initFlashMessages();
    
    // Initialize tabs if they exist
    initTabs();
    
    // Initialize tournament bracket view if on bracket page
    if (document.querySelector('.bracket-container')) {
        initBracketView();
    }
    
    // Initialize live scoring if on live scoring page
    if (document.querySelector('.live-scoring')) {
        initLiveScoring();
    }
});

/**
 * Initialize mobile menu functionality
 */
function initMobileMenu() {
    const menuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (menuButton && mobileMenu) {
        menuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }
}

/**
 * Initialize flash message dismissal
 */
function initFlashMessages() {
    const closeButtons = document.querySelectorAll('.close-flash');
    
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const flashMessage = this.closest('.flash-message');
            flashMessage.style.opacity = '0';
            setTimeout(() => {
                flashMessage.style.display = 'none';
            }, 300);
        });
    });
}

/**
 * Initialize tabs functionality
 */
function initTabs() {
    const tabContainers = document.querySelectorAll('.tabs-container');
    
    tabContainers.forEach(container => {
        const tabs = container.querySelectorAll('.tab');
        const tabContents = container.querySelectorAll('.tab-content');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // Get the target tab content id
                const target = this.getAttribute('data-target');
                
                // Reset all tabs and contents
                tabs.forEach(t => t.classList.remove('tab-active'));
                tabs.forEach(t => t.classList.add('tab-inactive'));
                tabContents.forEach(c => c.classList.add('hidden'));
                
                // Activate clicked tab and content
                this.classList.add('tab-active');
                this.classList.remove('tab-inactive');
                
                const targetContent = document.getElementById(target);
                if (targetContent) {
                    targetContent.classList.remove('hidden');
                }
            });
        });
    });
}

/**
 * Initialize tournament bracket view
 */
function initBracketView() {
    // Set bracket container height to fit all rounds
    const bracketContainer = document.querySelector('.bracket-container');
    const rounds = bracketContainer.querySelectorAll('.bracket-round');
    
    // Calculate and set the minimum height for the bracket container
    let maxMatches = 0;
    rounds.forEach(round => {
        const matchCount = round.querySelectorAll('.bracket-match').length;
        maxMatches = Math.max(maxMatches, matchCount);
    });
    
    // Set min-height based on match count (adjust multiplier as needed)
    bracketContainer.style.minHeight = `${maxMatches * 120 + 50}px`;
}

/**
 * Initialize live scoring updates
 */
function initLiveScoring() {
    const tournamentId = document.querySelector('.live-scoring').getAttribute('data-tournament-id');
    
    if (tournamentId) {
        // Set up polling for live score updates every 30 seconds
        setInterval(() => {
            fetchLiveScores(tournamentId);
        }, 30000);
        
        // Initial fetch
        fetchLiveScores(tournamentId);
    }
}

/**
 * Fetch live scores from the API
 */
function fetchLiveScores(tournamentId) {
    fetch(`/tournament/api/${tournamentId}/scores`)
        .then(response => response.json())
        .then(data => {
            updateLiveScores(data);
        })
        .catch(error => {
            console.error('Error fetching live scores:', error);
        });
}

/**
 * Update live scores in the DOM
 */
function updateLiveScores(data) {
    data.forEach(match => {
        const matchElement = document.getElementById(`match-${match.match_id}`);
        
        if (matchElement) {
            const scoreContainer = matchElement.querySelector('.match-scores');
            
            if (scoreContainer) {
                let scoreHtml = '';
                
                match.scores.forEach(score => {
                    scoreHtml += `<div class="match-set">
                        <span class="match-score ${score.player1_score > score.player2_score ? 'font-bold' : ''}">${score.player1_score}</span>
                        <span>-</span>
                        <span class="match-score ${score.player2_score > score.player1_score ? 'font-bold' : ''}">${score.player2_score}</span>
                    </div>`;
                });
                
                scoreContainer.innerHTML = scoreHtml;
            }
        }
    });
}

/**
 * Tournament registration form validation
 */
function validateTournamentRegistration() {
    const form = document.getElementById('tournament-registration-form');
    
    if (form) {
        const categorySelect = form.querySelector('select[name="category_id"]');
        const partnerSelect = form.querySelector('select[name="partner_id"]');
        
        if (categorySelect && partnerSelect) {
            categorySelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex].text;
                
                // If selected category is doubles, show partner field
                if (selectedOption.includes('Doubles')) {
                    partnerSelect.parentElement.classList.remove('hidden');
                    partnerSelect.required = true;
                } else {
                    partnerSelect.parentElement.classList.add('hidden');
                    partnerSelect.required = false;
                }
            });
            
            // Trigger change event to set initial state
            categorySelect.dispatchEvent(new Event('change'));
        }
    }
}
