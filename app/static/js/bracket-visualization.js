/**
 * Tournament Bracket Visualization
 * 
 * This JavaScript file enhances the visualization of tournament brackets
 * with interactive features and proper layout.
 */

class BracketVisualization {
    /**
     * Initialize the bracket visualization
     * @param {string} containerId - The ID of the bracket container element
     */
    constructor(containerId = 'tournament-bracket') {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Bracket container with ID '${containerId}' not found`);
            return;
        }
        
        this.rounds = this.container.querySelectorAll('.bracket-round');
        this.matches = this.container.querySelectorAll('.bracket-match');
        
        this.init();
    }
    
    /**
     * Initialize the bracket visualization
     */
    init() {
        this.resizeBracket();
        this.drawConnectors();
        this.setupMatchHover();
        
        // Handle window resize events
        window.addEventListener('resize', () => {
            this.resizeBracket();
            this.clearConnectors();
            this.drawConnectors();
        });
    }
    
    /**
     * Resize the bracket container and rounds to ensure proper layout
     */
    resizeBracket() {
        if (!this.container || !this.rounds || !this.rounds.length) return;
        
        // Calculate the max height needed based on the number of matches
        let maxMatches = 0;
        this.rounds.forEach(round => {
            const matchCount = round.querySelectorAll('.bracket-match').length;
            maxMatches = Math.max(maxMatches, matchCount);
        });
        
        // Set the minimum height of the container
        const matchHeight = 90; // Average height of a match element with margins
        const containerMinHeight = maxMatches * matchHeight + 80; // Add extra space for round titles
        this.container.style.minHeight = `${containerMinHeight}px`;
        
        // Set equal width for each round
        const roundWidth = `${100 / this.rounds.length}%`;
        this.rounds.forEach(round => {
            round.style.minWidth = roundWidth;
            round.style.maxWidth = roundWidth;
        });
        
        // Adjust spacing between matches to distribute them evenly
        this.rounds.forEach(round => {
            const matches = round.querySelectorAll('.bracket-match');
            if (matches.length <= 1) return;
            
            const roundHeight = this.container.offsetHeight - 60; // Subtract header height
            const matchSpacing = roundHeight / matches.length;
            
            matches.forEach((match, index) => {
                match.style.marginTop = index === 0 ? '0' : `${matchSpacing - match.offsetHeight}px`;
            });
        });
    }
    
    /**
     * Draw connector lines between matches across rounds
     */
    drawConnectors() {
        if (!this.container || !this.rounds || this.rounds.length <= 1) return;
        
        // Create SVG overlay for drawing connectors
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'bracket-connectors');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.pointerEvents = 'none';
        svg.style.zIndex = '1';
        
        this.container.style.position = 'relative';
        this.container.appendChild(svg);
        
        // Draw connectors between matches
        for (let r = 0; r < this.rounds.length - 1; r++) {
            const currentRound = this.rounds[r];
            const nextRound = this.rounds[r + 1];
            
            const currentMatches = currentRound.querySelectorAll('.bracket-match');
            const nextMatches = nextRound.querySelectorAll('.bracket-match');
            
            // Skip if there are no matches in either round
            if (!currentMatches.length || !nextMatches.length) continue;
            
            // For each match in the current round, draw connector to the corresponding match in the next round
            currentMatches.forEach((match, index) => {
                const nextMatchIndex = Math.floor(index / 2);
                if (nextMatchIndex >= nextMatches.length) return;
                
                const nextMatch = nextMatches[nextMatchIndex];
                
                // Calculate the coordinates
                const matchRect = match.getBoundingClientRect();
                const nextMatchRect = nextMatch.getBoundingClientRect();
                const containerRect = this.container.getBoundingClientRect();
                
                // Adjust coordinates relative to the container
                const x1 = matchRect.right - containerRect.left;
                const y1 = matchRect.top + matchRect.height / 2 - containerRect.top;
                const x2 = nextMatchRect.left - containerRect.left;
                const y2 = nextMatchRect.top + nextMatchRect.height / 2 - containerRect.top;
                
                // Create path for the connector
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const controlX = x1 + (x2 - x1) / 2;
                
                // Use curved paths for better visualization
                const d = `M ${x1} ${y1} C ${controlX} ${y1}, ${controlX} ${y2}, ${x2} ${y2}`;
                
                path.setAttribute('d', d);
                path.setAttribute('stroke', '#cbd5e1'); // Use a light gray color
                path.setAttribute('stroke-width', '1.5');
                path.setAttribute('fill', 'none');
                
                // Add data attributes to identify the connected matches
                path.dataset.fromMatch = match.id;
                path.dataset.toMatch = nextMatch.id;
                
                svg.appendChild(path);
            });
        }
    }
    
    /**
     * Clear all connector lines
     */
    clearConnectors() {
        const svg = this.container.querySelector('.bracket-connectors');
        if (svg) {
            svg.remove();
        }
    }
    
    /**
     * Set up hover effects for matches to highlight match paths
     */
    setupMatchHover() {
        this.matches.forEach(match => {
            match.addEventListener('mouseenter', () => {
                this.highlightMatchPath(match.id);
            });
            
            match.addEventListener('mouseleave', () => {
                this.resetHighlights();
            });
        });
    }
    
    /**
     * Highlight a match and all connected matches in its path
     * @param {string} matchId - The ID of the match to highlight
     */
    highlightMatchPath(matchId) {
        // Highlight the match itself
        const match = document.getElementById(matchId);
        if (match) {
            match.classList.add('bracket-match-highlighted');
        }
        
        // Highlight all connected matches (both previous and next)
        this.highlightPreviousMatches(matchId);
        this.highlightNextMatches(matchId);
        
        // Highlight connectors
        const connectors = this.container.querySelectorAll(`.bracket-connectors path[data-from-match="${matchId}"], .bracket-connectors path[data-to-match="${matchId}"]`);
        connectors.forEach(connector => {
            connector.setAttribute('stroke', '#3b82f6'); // Highlight with blue
            connector.setAttribute('stroke-width', '2.5');
        });
    }
    
    /**
     * Highlight all previous matches that led to this match
     * @param {string} matchId - The ID of the current match
     */
    highlightPreviousMatches(matchId) {
        const match = document.getElementById(matchId);
        if (!match) return;
        
        // Find previous matches that connect to this match
        const previousConnectors = this.container.querySelectorAll(`.bracket-connectors path[data-to-match="${matchId}"]`);
        previousConnectors.forEach(connector => {
            const prevMatchId = connector.dataset.fromMatch;
            if (prevMatchId) {
                const prevMatch = document.getElementById(prevMatchId);
                if (prevMatch && !prevMatch.classList.contains('bracket-match-highlighted')) {
                    prevMatch.classList.add('bracket-match-highlighted');
                    this.highlightPreviousMatches(prevMatchId); // Recursive call for previous matches
                }
            }
        });
    }
    
    /**
     * Highlight all next matches that this match leads to
     * @param {string} matchId - The ID of the current match
     */
    highlightNextMatches(matchId) {
        const match = document.getElementById(matchId);
        if (!match) return;
        
        // Find next matches that this match connects to
        const nextConnectors = this.container.querySelectorAll(`.bracket-connectors path[data-from-match="${matchId}"]`);
        nextConnectors.forEach(connector => {
            const nextMatchId = connector.dataset.toMatch;
            if (nextMatchId) {
                const nextMatch = document.getElementById(nextMatchId);
                if (nextMatch && !nextMatch.classList.contains('bracket-match-highlighted')) {
                    nextMatch.classList.add('bracket-match-highlighted');
                    this.highlightNextMatches(nextMatchId); // Recursive call for next matches
                }
            }
        });
    }
    
    /**
     * Reset all highlights
     */
    resetHighlights() {
        // Reset match highlights
        this.matches.forEach(match => {
            match.classList.remove('bracket-match-highlighted');
        });
        
        // Reset connector highlights
        const connectors = this.container.querySelectorAll('.bracket-connectors path');
        connectors.forEach(connector => {
            connector.setAttribute('stroke', '#cbd5e1'); // Reset to light gray
            connector.setAttribute('stroke-width', '1.5');
        });
    }
}

// Initialize the bracket visualization when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize for the main tournament bracket
    const tournamentBracket = new BracketVisualization('tournament-bracket');
    
    // Add CSS styles for bracket highlighting
    const style = document.createElement('style');
    style.textContent = `
        .bracket-match-highlighted {
            box-shadow: 0 0 0 2px #3b82f6;
            z-index: 10;
            position: relative;
        }
        
        .bracket-match {
            transition: box-shadow 0.2s ease;
        }
    `;
    document.head.appendChild(style);
});