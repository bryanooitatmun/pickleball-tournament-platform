/**
 * Mobile Bracket Visualization
 * 
 * This JavaScript file handles the mobile-specific bracket navigation
 * and display for tournament brackets.
 */

class MobileBracketView {
    /**
     * Initialize the mobile bracket view
     */
    constructor() {
        this.roundTabs = document.querySelectorAll('.mobile-round-tab');
        this.roundViews = document.querySelectorAll('.mobile-round-view');
        
        this.initializeTabs();
        this.showDefaultRound();
    }
    
    /**
     * Set up tab click handlers
     */
    initializeTabs() {
        if (!this.roundTabs.length) return;
        
        this.roundTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                // Deactivate all tabs
                this.roundTabs.forEach(t => t.classList.remove('active'));
                
                // Activate clicked tab
                tab.classList.add('active');
                
                // Show corresponding round view
                const roundId = tab.getAttribute('data-round');
                this.showRound(roundId);
            });
        });
    }
    
    /**
     * Show a specific round
     * @param {string} roundId - The ID of the round to show
     */
    showRound(roundId) {
        // Hide all round views
        this.roundViews.forEach(view => {
            view.classList.remove('active');
        });
        
        // Show selected round view
        const selectedView = document.getElementById(`mobile-round-${roundId}`);
        if (selectedView) {
            selectedView.classList.add('active');
        }
    }
    
    /**
     * Show the default (first available) round
     */
    showDefaultRound() {
        // Show the first round by default
        if (this.roundTabs.length > 0) {
            const defaultTab = this.roundTabs[0];
            defaultTab.classList.add('active');
            
            const defaultRoundId = defaultTab.getAttribute('data-round');
            this.showRound(defaultRoundId);
        }
    }
}

// Initialize the mobile bracket view when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on mobile screens
    if (window.innerWidth < 768) {
        const mobileBracketView = new MobileBracketView();
    }
    
    // Handle window resize to initialize on mobile or switch to desktop
    window.addEventListener('resize', function() {
        // Show desktop view on larger screens
        const desktopBracket = document.getElementById('tournament-bracket');
        const mobileBracket = document.getElementById('mobile-tournament-bracket');
        
        if (window.innerWidth >= 768) {
            if (desktopBracket) desktopBracket.style.display = '';
            if (mobileBracket) mobileBracket.style.display = 'none';
        } else {
            if (desktopBracket) desktopBracket.style.display = 'none';
            if (mobileBracket) mobileBracket.style.display = '';
            
            // Reinitialize mobile view
            const mobileBracketView = new MobileBracketView();
        }
    });
    
    // Initial check to set correct view
    if (window.innerWidth < 768) {
        const desktopBracket = document.getElementById('tournament-bracket');
        const mobileBracket = document.getElementById('mobile-tournament-bracket');
        
        if (desktopBracket) desktopBracket.style.display = 'none';
        if (mobileBracket) mobileBracket.style.display = '';
    }
});
