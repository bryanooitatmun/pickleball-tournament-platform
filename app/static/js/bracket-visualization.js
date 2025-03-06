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
        
        this.rounds = Array.from(this.container.querySelectorAll('.bracket-round'));
        this.matches = Array.from(this.container.querySelectorAll('.bracket-match'));
        
        // Add a wrapper to help with positioning
        this.wrapBracket();
        this.init();
    }
    
    /**
     * Wrap the bracket in a positioning container
     */
    wrapBracket() {
        // Check if the bracket is already wrapped
        const existingWrapper = this.container.querySelector('.bracket-wrapper');
        if (existingWrapper) {
            this.innerContainer = existingWrapper;
            return;
        }
        
        // Create a wrapper to help with positioning
        const wrapper = document.createElement('div');
        wrapper.className = 'bracket-wrapper';
        wrapper.style.position = 'relative';
        wrapper.style.width = '100%';
        wrapper.style.height = '100%';

        
        // Clone the container's content into the wrapper
        while(this.container.firstChild) {
            wrapper.appendChild(this.container.firstChild);
        }
        
        // Add the wrapper to the container
        this.container.appendChild(wrapper);
        
        // Update reference to the container for drawing
        this.innerContainer = wrapper;
    }
    
    /**
     * Initialize the bracket visualization
     */
    init() {
        // Process rounds to make sure they're in the correct order (round of 16, quarterfinals, etc.)
        this.organizeRounds();
        
        // Set up the container
        this.setupContainer();
        
        // First distribute all matches by their round
        this.distributeRoundPositions();
        
        // Then perform a two-pass positioning
        this.distributeMatchPositions();
        
        // Clear and redraw connectors
        this.clearConnectors();
        this.drawConnectors();
        
        // Set up interactivity
        this.setupMatchHover();
        
        // Handle window resize events with throttling
        let resizeTimeout;
        window.addEventListener('resize', () => {
            // Clear any previous timeout
            if (resizeTimeout) {
                clearTimeout(resizeTimeout);
            }
            
            // Set a new timeout to prevent multiple rapid executions
            resizeTimeout = setTimeout(() => {
                this.clearConnectors();
                this.distributeMatchPositions();
                this.drawConnectors();
            }, 200);
        });
    }

    /**
     * Set up the container with proper styles
     */
    setupContainer() {
        // Set up flex container
        this.innerContainer.style.display = 'flex';
        this.innerContainer.style.flexDirection = 'row';
        this.innerContainer.style.justifyContent = 'space-between';
        this.innerContainer.style.minHeight = '1000px'; // Increase min height for better spacing
        this.innerContainer.style.gap = '20px'; // Space between rounds
        
        // Set fixed height for the container to ensure consistent spacing
        this.container.style.height = '1000px';
        this.innerContainer.style.height = '100%';
        
        // Set up each round
        this.rounds.forEach(round => {
            round.style.flex = '1';
            round.style.display = 'flex';
            round.style.flexDirection = 'column';
            round.style.position = 'relative';
            round.style.minWidth = '220px';
            round.style.height = '100%';
        });
    }
    
    /**
     * Organize rounds to ensure they're in the correct order
     */
    organizeRounds() {
        // Get round titles to determine their order
        const roundOrder = ['Round of 64', 'Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Final'];
        
        // Create a map of round titles to indices
        const roundTitles = this.rounds.map(round => {
            const title = round.querySelector('h3');
            return title ? title.textContent.trim() : '';
        });
        
        // Sort rounds based on their titles or keep original order if titles don't match
        this.rounds.sort((a, b) => {
            const titleA = a.querySelector('h3') ? a.querySelector('h3').textContent.trim() : '';
            const titleB = b.querySelector('h3') ? b.querySelector('h3').textContent.trim() : '';
            
            const indexA = roundOrder.indexOf(titleA);
            const indexB = roundOrder.indexOf(titleB);
            
            if (indexA !== -1 && indexB !== -1) {
                return indexA - indexB;
            }
            return 0;
        });
    }
    
    /**
     * Distribute rounds with proper spacing
     */
    distributeRoundPositions() {
        const roundCount = this.rounds.length;
        
        // Preprocess matches to calculate their logical positions in a perfect bracket
        for (let i = 0; i < roundCount; i++) {
            const round = this.rounds[i];
            const matches = Array.from(round.querySelectorAll('.bracket-match'));
            
            matches.forEach((match, matchIndex) => {
                // Clear any previous inline styles that might interfere
                match.style.marginTop = '';
                match.style.marginBottom = '';
                match.style.position = 'relative';
                
                // Store the round and match indices for later use
                match.dataset.roundIndex = i;
                match.dataset.matchIndex = matchIndex;
                
                // Calculate and store the logical position of this match in a perfect bracket
                // This value represents where this match would be in a full bracket structure
                const perfectBracketPosition = matchIndex * Math.pow(2, roundCount - i - 1);
                match.dataset.bracketPosition = perfectBracketPosition;
            });
        }
    }
    
    /**
     * Distribute matches evenly in vertical space using a two-pass approach
     */
    distributeMatchPositions() {
        const roundCount = this.rounds.length;
        const containerHeight = 1000; // Use fixed height for consistent spacing
        const matchHeight = 85; // Approximate height of each match
        
        // FIRST PASS: Position first round matches evenly
        const firstRound = this.rounds[0];
        const firstRoundMatches = Array.from(firstRound.querySelectorAll('.bracket-match'));
        
        if (firstRoundMatches.length > 0) {
            // Position first round matches with even spacing
            this.positionMatchesEvenly(firstRound, containerHeight, matchHeight);
        }
        
        // SECOND PASS: Position subsequent rounds based on their parent matches
        for (let i = 1; i < roundCount; i++) {
            const currentRound = this.rounds[i];
            const currentMatches = Array.from(currentRound.querySelectorAll('.bracket-match'));
            const previousRound = this.rounds[i - 1];
            const previousMatches = Array.from(previousRound.querySelectorAll('.bracket-match'));
            
            if (currentMatches.length === 0 || previousMatches.length === 0) continue;
            
            // Position each match based on the position of its parent matches
            currentMatches.forEach((match, matchIndex) => {
                // Find parent matches
                const parentIndex1 = matchIndex * 2;
                const parentIndex2 = matchIndex * 2 + 1;
                
                let parent1Position = 0;
                let parent2Position = containerHeight;
                
                // Get position of first parent if it exists
                if (parentIndex1 < previousMatches.length) {
                    const parent1 = previousMatches[parentIndex1];
                    const parent1Rect = parent1.getBoundingClientRect();
                    const roundRect = previousRound.getBoundingClientRect();
                    parent1Position = parent1Rect.top - roundRect.top + (parent1Rect.height / 2);
                }
                
                // Get position of second parent if it exists
                if (parentIndex2 < previousMatches.length) {
                    const parent2 = previousMatches[parentIndex2];
                    const parent2Rect = parent2.getBoundingClientRect();
                    const roundRect = previousRound.getBoundingClientRect();
                    parent2Position = parent2Rect.top - roundRect.top + (parent2Rect.height / 2);
                }
                
                // Position the match at the midpoint between parents
                const position = (parent1Position + parent2Position) / 2;
                
                // Apply position - use absolute positioning for precision
                match.style.position = 'absolute';
                match.style.top = `${position - (matchHeight / 2)}px`;
                match.style.left = '0';
                match.style.right = '0';
            });
        }
    }
    
    /**
     * Position matches evenly within a round
     */
    positionMatchesEvenly(round, containerHeight, matchHeight) {
        const matches = Array.from(round.querySelectorAll('.bracket-match'));
        const matchCount = matches.length;
        
        if (matchCount === 0) return;
        
        // Calculate the spacing between matches
        const totalMatchHeight = matchCount * matchHeight;
        const availableHeight = containerHeight - totalMatchHeight;
        const spacing = availableHeight / (matchCount + 1);
        
        // Position each match with absolute positioning
        matches.forEach((match, index) => {
            // Calculate the top position for this match
            const matchTop = spacing + (index * (matchHeight + spacing));
            
            // Apply absolute positioning
            match.style.position = 'absolute';
            match.style.top = `${matchTop}px`;
            match.style.left = '0';
            match.style.right = '0';
        });
    }
    
    /**
     * Draw connector lines between matches across rounds
     */
    drawConnectors() {
        if (!this.innerContainer || !this.rounds || this.rounds.length <= 1) return;
        
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
        
        this.innerContainer.style.position = 'relative';
        this.innerContainer.appendChild(svg);
        
        // Process each round and draw connectors to the next round
        for (let i = 0; i < this.rounds.length - 1; i++) {
            // Get matches for the current and next rounds
            const currentRound = this.rounds[i];
            const nextRound = this.rounds[i + 1];
            
            const currentMatches = Array.from(currentRound.querySelectorAll('.bracket-match'));
            const nextMatches = Array.from(nextRound.querySelectorAll('.bracket-match'));
            
            // Skip if either round has no matches
            if (currentMatches.length === 0 || nextMatches.length === 0) continue;
            
            // For each match in the current round, find its next match in the tournament
            currentMatches.forEach((currentMatch, currentIndex) => {
                // In a single elimination tournament, each match feeds into
                // the next round at position floor(index / 2)
                const nextMatchIndex = Math.floor(currentIndex / 2);
                
                // Make sure we have a valid next match
                if (nextMatchIndex < nextMatches.length) {
                    const nextMatch = nextMatches[nextMatchIndex];
                    
                    // Get the positions for drawing
                    const currentRect = currentMatch.getBoundingClientRect();
                    const nextRect = nextMatch.getBoundingClientRect();
                    const containerRect = this.innerContainer.getBoundingClientRect();
                    
                    // Calculate connector endpoints
                    const x1 = currentRect.right - containerRect.left;
                    const y1 = currentRect.top + (currentRect.height / 2) - containerRect.top;
                    
                    const x2 = nextRect.left - containerRect.left;
                    const y2 = nextRect.top + (nextRect.height / 2) - containerRect.top;
                    
                    // Create a curved path
                    const controlX = x1 + (x2 - x1) / 2;
                    
                    // Draw the path
                    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    path.setAttribute('d', `M ${x1} ${y1} C ${controlX} ${y1}, ${controlX} ${y2}, ${x2} ${y2}`);
                    path.setAttribute('stroke', '#cbd5e1'); // Light gray
                    path.setAttribute('stroke-width', '1.5');
                    path.setAttribute('fill', 'none');
                    
                    // Add data attributes for hover effects
                    path.dataset.fromMatch = currentMatch.id;
                    path.dataset.toMatch = nextMatch.id;
                    
                    svg.appendChild(path);
                }
            });
        }
    }
    
    /**
     * Clear all connector lines
     */
    clearConnectors() {
        const svg = this.innerContainer.querySelector('.bracket-connectors');
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
        const connectors = this.innerContainer.querySelectorAll(`.bracket-connectors path[data-from-match="${matchId}"], .bracket-connectors path[data-to-match="${matchId}"]`);
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
        const previousConnectors = this.innerContainer.querySelectorAll(`.bracket-connectors path[data-to-match="${matchId}"]`);
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
        const nextConnectors = this.innerContainer.querySelectorAll(`.bracket-connectors path[data-from-match="${matchId}"]`);
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
        const connectors = this.innerContainer.querySelectorAll('.bracket-connectors path');
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
            background-color: white;
            border: 1px solid #e5e7eb;
            border-radius: 0.375rem;
            padding: 0.5rem;
            width: 100%;
            min-height: 80px;
            position: relative;
        }
        
        .bracket-team {
            padding: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .bracket-round {
            min-width: 220px;
            margin: 0 10px;
            position: relative;
        }
        
        .bracket-wrapper {
            padding: 1rem 0;
            width: 100%;
            height: 100%;
        }
        
        /* Make sure the container has proper spacing */
        #tournament-bracket {
            margin-bottom: 2rem;
            min-height: 1000px;
            height: 1000px;
        }
    `;
    document.head.appendChild(style);
});