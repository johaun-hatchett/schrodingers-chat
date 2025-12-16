// API Configuration
const API_BASE = window.location.origin + '/api';
let authToken = localStorage.getItem('authToken');
let currentUser = null;
let currentGameState = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        checkAuth();
    } else {
        showLogin();
    }
    
    setupEventListeners();
});

function setupEventListeners() {
    // Login/Signup
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('signupForm').addEventListener('submit', handleSignup);
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.dataset.tab;
            switchTab(tab);
        });
    });
    
    // Navigation
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    document.querySelectorAll('.nav-button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const view = e.target.dataset.view;
            switchView(view);
        });
    });
    
    // Game controls
    document.getElementById('startGameBtn').addEventListener('click', startGame);
    document.getElementById('resetGameBtn').addEventListener('click', resetGame);
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    document.getElementById('chatInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.target.disabled) sendMessage();
    });
    document.getElementById('newGameBtn').addEventListener('click', resetGame);
    
    // Summary tabs
    document.querySelectorAll('.summary-tab-button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.dataset.tab;
            const context = e.target.dataset.context || 'summary';
            switchSummaryTab(tab, context);
        });
    });
    
    // Sessions
    document.getElementById('backToSessions').addEventListener('click', () => {
        document.getElementById('sessionsList').classList.remove('hidden');
        document.getElementById('sessionDetail').classList.add('hidden');
    });
    
    // Admin
    document.getElementById('backToAdminSessions').addEventListener('click', () => {
        document.getElementById('adminSessionsList').classList.remove('hidden');
        document.getElementById('adminSessionDetail').classList.add('hidden');
    });
}

// Authentication
async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/sessions`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (response.ok) {
            showApp();
        } else {
            showLogin();
        }
    } catch (error) {
        showLogin();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    
    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        if (response.ok) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            showApp();
        } else {
            errorDiv.textContent = data.error || 'Login failed';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
    }
}

async function handleSignup(e) {
    e.preventDefault();
    const username = document.getElementById('signupUsername').value;
    const password = document.getElementById('signupPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const errorDiv = document.getElementById('signupError');
    
    try {
        const response = await fetch(`${API_BASE}/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, confirm_password: confirmPassword })
        });
        
        const data = await response.json();
        if (response.ok) {
            errorDiv.textContent = 'Account created! Please login.';
            setTimeout(() => switchTab('login'), 2000);
        } else {
            errorDiv.textContent = data.error || 'Signup failed';
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
    }
}

function handleLogout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    showLogin();
}

function switchTab(tab) {
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tab}Tab`);
    });
    document.querySelectorAll('.error-message').forEach(el => el.textContent = '');
}

function showLogin() {
    document.getElementById('loginModal').classList.remove('hidden');
    document.getElementById('app').classList.add('hidden');
}

function showApp() {
    document.getElementById('loginModal').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('usernameDisplay').textContent = `Logged in as: ${currentUser?.username || ''}`;
    
    if (currentUser?.is_admin) {
        document.getElementById('adminNav').classList.remove('hidden');
    } else {
        document.getElementById('adminNav').classList.add('hidden');
    }
    
    loadSessions();
    if (document.getElementById('adminView').classList.contains('active')) {
        loadAdminSessions();
    }
}

function switchView(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-button').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(`${view}View`).classList.add('active');
    document.querySelector(`[data-view="${view}"]`).classList.add('active');
    
    if (view === 'sessions') {
        loadSessions();
    } else if (view === 'admin') {
        loadAdminSessions();
    }
}

// Game Functions
async function startGame() {
    const problemType = document.getElementById('problemType').value;
    
    try {
        const response = await fetch(`${API_BASE}/game/start`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ problem_type: problemType })
        });
        
        const data = await response.json();
        if (response.ok) {
            currentGameState = {
                sessionId: data.session_id,
                problem: data.problem,
                problemType: data.problem_type,
                started: true
            };
            
            document.getElementById('problemDescription').textContent = data.problem;
            document.getElementById('problemDescription').classList.remove('hidden');
            document.getElementById('chatInputContainer').classList.remove('hidden');
            document.getElementById('startGameBtn').classList.add('hidden');
            document.getElementById('resetGameBtn').classList.remove('hidden');
            document.getElementById('problemType').disabled = true;
            document.getElementById('summarySection').classList.add('hidden');
            document.getElementById('messages').innerHTML = '';
            document.getElementById('chatInput').disabled = false;
            document.getElementById('sendBtn').disabled = false;
        }
    } catch (error) {
        alert('Error starting game: ' + error.message);
    }
}

function resetGame() {
    currentGameState = null;
    document.getElementById('problemDescription').classList.add('hidden');
    document.getElementById('chatInputContainer').classList.add('hidden');
    document.getElementById('chatInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('startGameBtn').classList.remove('hidden');
    document.getElementById('resetGameBtn').classList.add('hidden');
    document.getElementById('problemType').disabled = false;
    document.getElementById('summarySection').classList.add('hidden');
    document.getElementById('messages').innerHTML = '';
}

function switchSummaryTab(tab, context = 'summary') {
    let prefix, container, contentContainer;
    
    if (context === 'session') {
        prefix = 'sessionTab';
        container = document.querySelector('#sessionDetail .summary-tabs');
        contentContainer = document.querySelector('#sessionDetail');
    } else if (context === 'admin') {
        prefix = 'adminSessionTab';
        container = document.querySelector('#adminSessionDetail .summary-tabs');
        contentContainer = document.querySelector('#adminSessionDetail');
    } else {
        prefix = 'summaryTab';
        container = document.querySelector('#summarySection .summary-tabs');
        contentContainer = document.querySelector('#summarySection');
    }
    
    if (container) {
        container.querySelectorAll('.summary-tab-button').forEach(btn => {
            // For main summary section, buttons don't have data-context attribute
            // For session/admin, buttons have data-context attribute
            const btnContext = btn.dataset.context || 'summary';
            if (btnContext === context) {
                // Set active state: true if this button's tab matches, false otherwise
                btn.classList.toggle('active', btn.dataset.tab === tab);
            } else {
                // Remove active from buttons in other contexts
                btn.classList.remove('active');
            }
        });
    }
    
    if (contentContainer) {
        contentContainer.querySelectorAll('.summary-tab-content').forEach(content => {
            if (content.id.startsWith(prefix)) {
                content.classList.toggle('active', content.id === `${prefix}-${tab}`);
            } else {
                content.classList.remove('active');
            }
        });
    }
}

function showTypingIndicator() {
    const messagesDiv = document.getElementById('messages');
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typingIndicator';
    typingDiv.className = 'typing-indicator';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('div');
        dot.className = 'typing-dot';
        contentDiv.appendChild(dot);
    }
    
    typingDiv.appendChild(contentDiv);
    messagesDiv.appendChild(typingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message || !currentGameState) return;
    
    // Add user message to UI
    addMessage('user', message);
    input.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const response = await fetch(`${API_BASE}/game/message`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                model: 'gpt-5',
                use_fast_model: document.getElementById('fastModel').checked
            })
        });
        
        // Hide typing indicator before showing response
        hideTypingIndicator();
        
        const data = await response.json();
        if (response.ok) {
            data.messages.forEach(msg => {
                addMessage(msg.role, msg.content, msg.type);
            });
            
            if (data.game_completed) {
                document.getElementById('chatInputContainer').classList.add('hidden');
                document.getElementById('chatInput').disabled = true;
                document.getElementById('sendBtn').disabled = true;
                generateSummary();
            }
        }
    } catch (error) {
        hideTypingIndicator();
        addMessage('assistant', 'Error: ' + error.message, 'error');
    }
}

function addMessage(role, content, type = 'info') {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role} ${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatMarkdown(content);
    
    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // Re-render LaTeX if auto-render is available (for dynamically added content)
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(contentDiv, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\[', right: '\\]', display: true},
                {left: '\\(', right: '\\)', display: false}
            ],
            throwOnError: false
        });
    } else if (typeof katex !== 'undefined') {
        // Fallback: manually render any remaining LaTeX
        setTimeout(() => {
            if (typeof renderMathInElement !== 'undefined') {
                renderMathInElement(contentDiv, {
                    delimiters: [
                        {left: '$$', right: '$$', display: true},
                        {left: '$', right: '$', display: false},
                        {left: '\\[', right: '\\]', display: true},
                        {left: '\\(', right: '\\)', display: false}
                    ],
                    throwOnError: false
                });
            }
        }, 100);
    }
}

function formatMarkdown(text) {
    if (!text) return '';
    
    let html = text;
    
    // Preserve LaTeX blocks first (display math $$...$$ and \[...\])
    const latexBlocks = [];
    html = html.replace(/\$\$([\s\S]*?)\$\$/g, (match, math) => {
        const id = `LATEXBLOCK_${latexBlocks.length}`;
        latexBlocks.push({ type: 'display', math: math.trim() });
        return id;
    });
    html = html.replace(/\\\[([\s\S]*?)\\\]/g, (match, math) => {
        const id = `LATEXBLOCK_${latexBlocks.length}`;
        latexBlocks.push({ type: 'display', math: math.trim() });
        return id;
    });
    
    // Preserve LaTeX inline ($...$ and \(...\))
    html = html.replace(/\$([^$\n]+?)\$/g, (match, math) => {
        const id = `LATEXINLINE_${latexBlocks.length}`;
        latexBlocks.push({ type: 'inline', math: math.trim() });
        return id;
    });
    html = html.replace(/\\\(([^\)]+?)\\\)/g, (match, math) => {
        const id = `LATEXINLINE_${latexBlocks.length}`;
        latexBlocks.push({ type: 'inline', math: math.trim() });
        return id;
    });
    
    // Code blocks (to avoid processing inside them)
    const codeBlocks = [];
    html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
        const id = `CODEBLOCK_${codeBlocks.length}`;
        codeBlocks.push(`<pre><code>${code.trim()}</code></pre>`);
        return id;
    });
    
    // Headers (### Header)
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Bold (**text**)
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic (*text*) - but not if it's part of bold
    html = html.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em>$1</em>');
    
    // Inline code (`code`)
    html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
    
    // Unordered lists (- item or * item)
    html = html.replace(/^[-*] (.+)$/gim, '<li>$1</li>');
    
    // Wrap consecutive <li> elements in <ul>
    html = html.replace(/(<li>.*?<\/li>(\s*<li>.*?<\/li>)*)/gs, '<ul>$1</ul>');
    
    // Ordered lists (1. item)
    html = html.replace(/^\d+\. (.+)$/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>(\s*<li>.*?<\/li>)*)/gs, (match) => {
        if (!match.includes('<ul>')) {
            return '<ol>' + match + '</ol>';
        }
        return match;
    });
    
    // Restore code blocks
    codeBlocks.forEach((block, i) => {
        html = html.replace(`CODEBLOCK_${i}`, block);
    });
    
    // Restore LaTeX blocks - render with KaTeX if available, otherwise preserve delimiters
    latexBlocks.forEach((latex, i) => {
        if (typeof katex !== 'undefined') {
            try {
                if (latex.type === 'display') {
                    const rendered = katex.renderToString(latex.math, { displayMode: true, throwOnError: false });
                    html = html.replace(`LATEXBLOCK_${i}`, rendered);
                } else {
                    const rendered = katex.renderToString(latex.math, { displayMode: false, throwOnError: false });
                    html = html.replace(`LATEXINLINE_${i}`, rendered);
                }
            } catch (e) {
                // If KaTeX fails, show the original LaTeX
                const fallback = latex.type === 'display' ? `$$${latex.math}$$` : `$${latex.math}$`;
                html = html.replace(`LATEX${latex.type === 'display' ? 'BLOCK' : 'INLINE'}_${i}`, fallback);
            }
        } else {
            // KaTeX not loaded yet, preserve delimiters for auto-render
            const fallback = latex.type === 'display' ? `$$${latex.math}$$` : `$${latex.math}$`;
            html = html.replace(`LATEX${latex.type === 'display' ? 'BLOCK' : 'INLINE'}_${i}`, fallback);
        }
    });
    
    // Split into paragraphs (double newline)
    const paragraphs = html.split(/\n\n+/);
    html = paragraphs.map(para => {
        para = para.trim();
        if (!para) return '';
        // Don't wrap headers, lists, code blocks, or math blocks
        if (para.match(/^<(h[1-6]|ul|ol|pre|p|span)/)) {
            return para;
        }
        // Convert single newlines to <br> within paragraphs
        para = para.replace(/\n/g, '<br>');
        return '<p>' + para + '</p>';
    }).join('');
    
    return html;
}

async function generateSummary() {
    const summarySection = document.getElementById('summarySection');
    summarySection.classList.remove('hidden');
    document.getElementById('summaryTab-approach').innerHTML = '<p>Generating summary...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/game/summary`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'gpt-4o',
                problem_type: currentGameState.problemType
            })
        });
        
        const data = await response.json();
        if (response.ok) {
            // Store scores globally for use in dimensions tab
            window.summaryScores = data.scores;
            
            // Parse and display summary in tabs
            parseAndDisplaySummary(data.summary, data.scores);
            
            // Display chat transcript in chat tab - copy from main messages
            const mainMessages = document.getElementById('messages');
            const summaryMessages = document.getElementById('messagesSummary');
            summaryMessages.innerHTML = mainMessages.innerHTML;
            
            // Re-render LaTeX in chat tab
            setTimeout(() => {
                if (typeof renderMathInElement !== 'undefined') {
                    renderMathInElement(summaryMessages, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false},
                            {left: '\\[', right: '\\]', display: true},
                            {left: '\\(', right: '\\)', display: false}
                        ],
                        throwOnError: false
                    });
                }
            }, 100);
        }
    } catch (error) {
        document.getElementById('summaryTab-approach').innerHTML = '<p>Error generating summary: ' + error.message + '</p>';
    }
}

function parseAndDisplaySummary(summary, scores) {
    // Parse the summary into sections
    const sections = {
        approach: '',
        dimensions: '',
        strengths: '',
        nextsteps: ''
    };
    
    // Split by headers (with fallback for old format)
    const approachMatch = summary.match(/### (?:Summary of your approach|Overall approach)\s*\n([\s\S]*?)(?=###|$)/i);
    if (approachMatch) sections.approach = approachMatch[1].trim();
    
    const dimensionsMatch = summary.match(/### (?:Deep dive: how you showed up on the four dimensions|How you showed up on the four dimensions)\s*\n([\s\S]*?)(?=###|$)/i);
    if (dimensionsMatch) sections.dimensions = dimensionsMatch[1].trim();
    
    const strengthsMatch = summary.match(/### Strengths to keep building on\s*\n([\s\S]*?)(?=###|$)/i);
    if (strengthsMatch) {
        // Merge strengths into approach section
        sections.approach += '\n\n### Strengths to keep building on\n' + strengthsMatch[1].trim();
    }
    
    const growthMatch = summary.match(/### Opportunities to grow your problem-solving\s*\n([\s\S]*?)(?=###|$)/i);
    if (growthMatch) {
        // Merge growth into approach section
        sections.approach += '\n\n### Opportunities to grow your problem-solving\n' + growthMatch[1].trim();
    }
    
    const nextstepsMatch = summary.match(/### Suggested next practice steps\s*\n([\s\S]*?)(?=###|$)/i);
    if (nextstepsMatch) {
        sections.nextsteps = '### Suggested next practice steps\n' + nextstepsMatch[1].trim();
    }
    
    // Display approach (now includes strengths and growth)
    document.getElementById('summaryTab-approach').innerHTML = formatMarkdown(sections.approach);
    
    // Display dimensions with Likert scores
    renderDimensionsTab(sections.dimensions, scores);
    
    // Display next steps
    document.getElementById('summaryTab-nextsteps').innerHTML = formatMarkdown(sections.nextsteps);
    
    // Render LaTeX in all tabs
    setTimeout(() => {
        if (typeof renderMathInElement !== 'undefined') {
            ['approach', 'dimensions', 'nextsteps'].forEach(tab => {
                const tabEl = document.getElementById(`summaryTab-${tab}`);
                if (tabEl) {
                    renderMathInElement(tabEl, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false},
                            {left: '\\[', right: '\\]', display: true},
                            {left: '\\(', right: '\\)', display: false}
                        ],
                        throwOnError: false
                    });
                }
            });
        }
    }, 100);
}

function renderDimensionsTab(dimensionsText, scores, containerId = 'summaryTab-dimensions') {
    const container = document.getElementById(containerId);
    let html = '';
    
    // Parse dimension descriptions - look for lines starting with dimension name (not bullet points)
    scores.forEach(score => {
        const name = score.name;
        let description = '';
        
        // Try to find the dimension description in the text
        // Look for lines that start with the dimension name (with or without colon)
        const lines = dimensionsText.split('\n');
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            // Match if line starts with dimension name (case insensitive)
            if (line.match(new RegExp(`^${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[:]?\\s`, 'i'))) {
                // Extract everything after the dimension name and colon
                description = line.replace(new RegExp(`^${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[:]?\\s*`, 'i'), '').trim();
                // If description is short, check next line too
                if (description.length < 20 && i + 1 < lines.length) {
                    const nextLine = lines[i + 1].trim();
                    if (nextLine && !nextLine.match(/^(Conceptual Foundation|Strategic Insight|Mathematical Execution|Reflective Intuition)/i)) {
                        description += ' ' + nextLine;
                    }
                }
                break;
            }
        }
        
        // Clean up description - remove any weird formatting like ": 0."
        description = description.replace(/:\s*[0-9]+\.?\s*/g, ': ').trim();
        
        const position = ((score.scale + 2) / 4) * 100;
        html += `
            <div class="likert-dimension">
                <h4>${name}</h4>
                <div class="likert-labels">
                    <span>${score.low_label}</span>
                    <span>${score.high_label}</span>
                </div>
                <div class="likert-slider-container">
                    <div class="likert-slider" style="left: ${position}%"></div>
                </div>
                <div class="likert-rationale">${formatMarkdown(description || score.rationale)}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}


function renderLikertScores(scores, containerId) {
    const container = document.getElementById(containerId);
    if (!scores || scores.length === 0) {
        container.innerHTML = '<p>No scores available</p>';
        return;
    }
    
    container.innerHTML = scores.map(dim => {
        const position = ((dim.scale + 2) / 4) * 100; // Convert -2..+2 to 0..100%
        return `
            <div class="likert-dimension">
                <h4>${dim.name}</h4>
                <div class="likert-labels">
                    <span>${dim.low_label}</span>
                    <span>${dim.high_label}</span>
                </div>
                <div class="likert-slider-container">
                    <div class="likert-slider" style="left: ${position}%"></div>
                </div>
                <div class="likert-rationale">${dim.rationale}</div>
            </div>
        `;
    }).join('');
}

// Sessions
async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE}/sessions`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (response.ok) {
            renderSessions(data.sessions);
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

function renderSessions(sessions) {
    const container = document.getElementById('sessionsList');
    if (!sessions || sessions.length === 0) {
        container.innerHTML = '<p>No past sessions found.</p>';
        return;
    }
    
    container.innerHTML = sessions.map(session => {
        const date = new Date(session.timestamp).toLocaleString();
        return `
            <div class="session-item" onclick="loadSession(${session.id})">
                <h3>${session.problem_type}</h3>
                <p>${date}</p>
            </div>
        `;
    }).join('');
}

async function loadSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (response.ok) {
            const session = data.session;
            document.getElementById('sessionsList').classList.add('hidden');
            document.getElementById('sessionDetail').classList.remove('hidden');
            
            const date = new Date(session.timestamp);
            const formattedDate = date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric' 
            });
            const formattedTime = date.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit' 
            });
            const problemTypeFormatted = session.problem_type
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
            
            document.getElementById('sessionInfo').innerHTML = `
                <div class="session-metadata">
                    <div class="metadata-item">
                        <span class="metadata-label">Problem Type</span>
                        <span class="metadata-value">${problemTypeFormatted}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">Date</span>
                        <span class="metadata-value">${formattedDate}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">Time</span>
                        <span class="metadata-value">${formattedTime}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">Session ID</span>
                        <span class="metadata-value metadata-id">${session.session_id}</span>
                    </div>
                </div>
            `;
            
            // Parse and display summary in tabs
            if (session.summary && session.scores) {
                parseAndDisplaySessionSummary(session.summary, session.scores);
            } else if (session.summary) {
                // Fallback if no scores
                document.getElementById('sessionTab-approach').innerHTML = formatMarkdown(session.summary);
            }
            
            // Display transcript in chat tab
            if (session.transcript) {
                renderSessionTranscript(session.transcript);
            }
        }
    } catch (error) {
        console.error('Error loading session:', error);
    }
}

function parseAndDisplaySessionSummary(summary, scores) {
    // Parse the summary into sections (same logic as parseAndDisplaySummary)
    const sections = {
        approach: '',
        dimensions: '',
        nextsteps: ''
    };
    
    // Split by headers (with fallback for old format)
    const approachMatch = summary.match(/### (?:Summary of your approach|Overall approach)\s*\n([\s\S]*?)(?=###|$)/i);
    if (approachMatch) sections.approach = approachMatch[1].trim();
    
    const dimensionsMatch = summary.match(/### (?:Deep dive: how you showed up on the four dimensions|How you showed up on the four dimensions)\s*\n([\s\S]*?)(?=###|$)/i);
    if (dimensionsMatch) sections.dimensions = dimensionsMatch[1].trim();
    
    const strengthsMatch = summary.match(/### Strengths to keep building on\s*\n([\s\S]*?)(?=###|$)/i);
    if (strengthsMatch) {
        sections.approach += '\n\n### Strengths to keep building on\n' + strengthsMatch[1].trim();
    }
    
    const growthMatch = summary.match(/### Opportunities to grow your problem-solving\s*\n([\s\S]*?)(?=###|$)/i);
    if (growthMatch) {
        sections.approach += '\n\n### Opportunities to grow your problem-solving\n' + growthMatch[1].trim();
    }
    
    const nextstepsMatch = summary.match(/### Suggested next practice steps\s*\n([\s\S]*?)(?=###|$)/i);
    if (nextstepsMatch) {
        sections.nextsteps = '### Suggested next practice steps\n' + nextstepsMatch[1].trim();
    }
    
    // Display approach (now includes strengths and growth)
    document.getElementById('sessionTab-approach').innerHTML = formatMarkdown(sections.approach);
    
    // Display dimensions with Likert scores
    renderDimensionsTab(sections.dimensions, scores, 'sessionTab-dimensions');
    
    // Display next steps
    document.getElementById('sessionTab-nextsteps').innerHTML = formatMarkdown(sections.nextsteps);
    
    // Render LaTeX in all tabs
    setTimeout(() => {
        if (typeof renderMathInElement !== 'undefined') {
            ['approach', 'dimensions', 'nextsteps'].forEach(tab => {
                const tabEl = document.getElementById(`sessionTab-${tab}`);
                if (tabEl) {
                    renderMathInElement(tabEl, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false},
                            {left: '\\[', right: '\\]', display: true},
                            {left: '\\(', right: '\\)', display: false}
                        ],
                        throwOnError: false
                    });
                }
            });
        }
    }, 100);
}

function renderSessionTranscript(transcript) {
    const container = document.getElementById('sessionMessages');
    container.innerHTML = transcript.map(msg => {
        const role = msg.speaker === 'human' ? 'user' : 'assistant';
        return `
            <div class="message ${role}">
                <div class="message-content">${formatMarkdown(msg.content)}</div>
            </div>
        `;
    }).join('');
    
    // Render LaTeX
    setTimeout(() => {
        if (typeof renderMathInElement !== 'undefined') {
            renderMathInElement(container, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\[', right: '\\]', display: true},
                    {left: '\\(', right: '\\)', display: false}
                ],
                throwOnError: false
            });
        }
    }, 100);
}


// Admin
async function loadAdminSessions() {
    try {
        const response = await fetch(`${API_BASE}/admin/sessions`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (response.ok) {
            renderAdminSessions(data.sessions);
        }
    } catch (error) {
        console.error('Error loading admin sessions:', error);
    }
}

function renderAdminSessions(sessions) {
    const container = document.getElementById('adminSessionsList');
    if (!sessions || sessions.length === 0) {
        container.innerHTML = '<p>No sessions found.</p>';
        return;
    }
    
    container.innerHTML = sessions.map(session => {
        const date = new Date(session.timestamp).toLocaleString();
        return `
            <div class="session-item" onclick="loadAdminSession(${session.id})">
                <h3>${session.username} - ${session.problem_type}</h3>
                <p>${date}</p>
            </div>
        `;
    }).join('');
}

async function loadAdminSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/admin/sessions/${sessionId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (response.ok) {
            const session = data.session;
            document.getElementById('adminSessionsList').classList.add('hidden');
            document.getElementById('adminSessionDetail').classList.remove('hidden');
            
            const date = new Date(session.timestamp);
            const formattedDate = date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric' 
            });
            const formattedTime = date.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit' 
            });
            const problemTypeFormatted = session.problem_type
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
            
            document.getElementById('adminSessionInfo').innerHTML = `
                <div class="session-metadata">
                    <div class="metadata-item">
                        <span class="metadata-label">User</span>
                        <span class="metadata-value">${session.username}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">Problem Type</span>
                        <span class="metadata-value">${problemTypeFormatted}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">Date</span>
                        <span class="metadata-value">${formattedDate}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">Time</span>
                        <span class="metadata-value">${formattedTime}</span>
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">Session ID</span>
                        <span class="metadata-value metadata-id">${session.session_id}</span>
                    </div>
                </div>
            `;
            
            // Parse and display summary in tabs (same as regular sessions)
            if (session.summary && session.scores) {
                parseAndDisplayAdminSessionSummary(session.summary, session.scores);
            } else if (session.summary) {
                document.getElementById('adminSessionTab-approach').innerHTML = formatMarkdown(session.summary);
            }
            
            // Display transcript in chat tab
            if (session.transcript) {
                renderAdminSessionTranscript(session.transcript);
            }
        }
    } catch (error) {
        console.error('Error loading admin session:', error);
    }
}

function parseAndDisplayAdminSessionSummary(summary, scores) {
    // Same parsing logic as session summary
    const sections = {
        approach: '',
        dimensions: '',
        nextsteps: ''
    };
    
    const approachMatch = summary.match(/### (?:Summary of your approach|Overall approach)\s*\n([\s\S]*?)(?=###|$)/i);
    if (approachMatch) sections.approach = approachMatch[1].trim();
    
    const dimensionsMatch = summary.match(/### (?:Deep dive: how you showed up on the four dimensions|How you showed up on the four dimensions)\s*\n([\s\S]*?)(?=###|$)/i);
    if (dimensionsMatch) sections.dimensions = dimensionsMatch[1].trim();
    
    const strengthsMatch = summary.match(/### Strengths to keep building on\s*\n([\s\S]*?)(?=###|$)/i);
    if (strengthsMatch) {
        sections.approach += '\n\n### Strengths to keep building on\n' + strengthsMatch[1].trim();
    }
    
    const growthMatch = summary.match(/### Opportunities to grow your problem-solving\s*\n([\s\S]*?)(?=###|$)/i);
    if (growthMatch) {
        sections.approach += '\n\n### Opportunities to grow your problem-solving\n' + growthMatch[1].trim();
    }
    
    const nextstepsMatch = summary.match(/### Suggested next practice steps\s*\n([\s\S]*?)(?=###|$)/i);
    if (nextstepsMatch) {
        sections.nextsteps = '### Suggested next practice steps\n' + nextstepsMatch[1].trim();
    }
    
    document.getElementById('adminSessionTab-approach').innerHTML = formatMarkdown(sections.approach);
    renderDimensionsTab(sections.dimensions, scores, 'adminSessionTab-dimensions');
    document.getElementById('adminSessionTab-nextsteps').innerHTML = formatMarkdown(sections.nextsteps);
    
    setTimeout(() => {
        if (typeof renderMathInElement !== 'undefined') {
            ['approach', 'dimensions', 'nextsteps'].forEach(tab => {
                const tabEl = document.getElementById(`adminSessionTab-${tab}`);
                if (tabEl) {
                    renderMathInElement(tabEl, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false},
                            {left: '\\[', right: '\\]', display: true},
                            {left: '\\(', right: '\\)', display: false}
                        ],
                        throwOnError: false
                    });
                }
            });
        }
    }, 100);
}

function renderAdminSessionTranscript(transcript) {
    const container = document.getElementById('adminSessionMessages');
    container.innerHTML = transcript.map(msg => {
        const role = msg.speaker === 'human' ? 'user' : 'assistant';
        return `
            <div class="message ${role}">
                <div class="message-content">${formatMarkdown(msg.content)}</div>
            </div>
        `;
    }).join('');
    
    setTimeout(() => {
        if (typeof renderMathInElement !== 'undefined') {
            renderMathInElement(container, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\[', right: '\\]', display: true},
                    {left: '\\(', right: '\\)', display: false}
                ],
                throwOnError: false
            });
        }
    }, 100);
}

// Make functions available globally for onclick handlers
window.loadSession = loadSession;
window.loadAdminSession = loadAdminSession;

