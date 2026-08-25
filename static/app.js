document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const attachBtn = document.getElementById('attach-btn');
    const fileBadge = document.getElementById('file-badge');
    const fileNameDisplay = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file-btn');
    
    const userPromptInput = document.getElementById('user-prompt');
    const sendBtn = document.getElementById('import-btn');
    
    const chatContainer = document.getElementById('chat-container');
    const welcomeScreen = document.getElementById('welcome-screen');

    let currentFile = null;
    let chartInstanceIds = [];
    let chatState = {
        wallet: { history: [], hasChatted: false, draft: '' },
        analyst: { history: [], hasChatted: false, draft: '' }
    };

    const modeWalletBtn = document.getElementById('mode-wallet');
    const modeAnalystBtn = document.getElementById('mode-analyst');
    let currentMode = 'wallet'; // 'wallet' or 'analyst'

    const welcomeTitle = document.getElementById('welcome-title');
    const welcomeDesc = document.getElementById('welcome-desc');
    const welcomeLogo = document.getElementById('welcome-logo');
    const newChatBtn = document.getElementById('new-chat-btn');

    function updateBubblesVisibility() {
        const bubbles = chatContainer.querySelectorAll('.chat-bubble');
        bubbles.forEach(b => {
            if (b.classList.contains(`mode-${currentMode}`)) {
                b.style.display = 'flex';
            } else {
                b.style.display = 'none';
            }
        });
        if (chatState[currentMode].hasChatted) {
            if (!welcomeScreen.classList.contains('hidden')) {
                welcomeScreen.classList.add('hidden');
            }
        } else {
            welcomeScreen.classList.remove('hidden');
        }
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            chatState[currentMode].history = [];
            chatState[currentMode].hasChatted = false;
            chatState[currentMode].draft = '';
            userPromptInput.value = '';
            const bubbles = chatContainer.querySelectorAll(`.mode-${currentMode}`);
            bubbles.forEach(b => b.remove());
            welcomeScreen.classList.remove('hidden');
        });
    }

    // Auto-resize textarea
    userPromptInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') {
            this.style.height = 'auto';
        }
    });

    if (modeWalletBtn && modeAnalystBtn) {
        modeWalletBtn.addEventListener('click', () => {
            if (currentMode !== 'wallet') {
                chatState[currentMode].draft = userPromptInput.value;
                currentMode = 'wallet';
                userPromptInput.value = chatState[currentMode].draft;
            }
            document.body.classList.remove('analyst-mode');
            modeWalletBtn.classList.add('active');
            modeAnalystBtn.classList.remove('active');
            userPromptInput.placeholder = "Ask a financial question, track a stock, or upload data...";
            fileInput.accept = ".csv,.txt,.pdf,image/png,image/jpeg,image/jpg";
            
            if (welcomeTitle) welcomeTitle.textContent = "Budget Buddy V2";
            if (welcomeDesc) welcomeDesc.textContent = "Your intelligent financial advisor. Upload expense data, ask about the stock market, or get currency rates.";
            if (welcomeLogo) welcomeLogo.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
            updateBubblesVisibility();
        });

        modeAnalystBtn.addEventListener('click', () => {
            if (currentMode !== 'analyst') {
                chatState[currentMode].draft = userPromptInput.value;
                currentMode = 'analyst';
                userPromptInput.value = chatState[currentMode].draft;
            }
            document.body.classList.add('analyst-mode');
            modeAnalystBtn.classList.add('active');
            modeWalletBtn.classList.remove('active');
            userPromptInput.placeholder = "Upload SEC 10-K PDF and ask analytical questions...";
            fileInput.accept = ".pdf";
            
            if (welcomeTitle) welcomeTitle.textContent = "Market Analyst Pro";
            if (welcomeDesc) welcomeDesc.textContent = "Enterprise-grade RAG pipeline. Upload your corporate SEC 10-K filings and extract deep analytical insights instantly.";
            if (welcomeLogo) welcomeLogo.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>`;
            updateBubblesVisibility();
        });
    }

    attachBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            currentFile = e.target.files[0];
            fileNameDisplay.textContent = currentFile.name;
            fileBadge.classList.remove('hidden');
        }
    });

    removeFileBtn.addEventListener('click', () => {
        currentFile = null;
        fileInput.value = '';
        fileBadge.classList.add('hidden');
    });

    userPromptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleAnalysis();
        }
    });

    sendBtn.addEventListener('click', handleAnalysis);

    function createUserBubble(text, file) {
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble user';
        
        const avatar = document.createElement('div');
        avatar.className = 'bubble-avatar';
        avatar.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>`;
        
        const content = document.createElement('div');
        content.className = 'bubble-content';
        
        if (file) {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'bubble-file';
            fileDiv.innerHTML = `
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
                ${file.name}
            `;
            content.appendChild(fileDiv);
        }
        
        if (text) {
            const textDiv = document.createElement('div');
            textDiv.textContent = text;
            content.appendChild(textDiv);
        }

        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'bubble-actions';
        
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.title = 'Copy text';
        copyBtn.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>`;
        copyBtn.onclick = () => {
            if (text) navigator.clipboard.writeText(text);
        };
        
        const editBtn = document.createElement('button');
        editBtn.className = 'action-btn';
        editBtn.title = 'Edit prompt';
        editBtn.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>`;
        editBtn.onclick = () => {
            if (text) {
                userPromptInput.value = text;
                userPromptInput.focus();
            }
        };
        
        actionsDiv.appendChild(copyBtn);
        actionsDiv.appendChild(editBtn);

        bubble.appendChild(avatar);
        bubble.appendChild(content);
        bubble.appendChild(actionsDiv);
        return bubble;
    }

    function createAIBubble() {
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble ai';
        
        const avatar = document.createElement('div');
        avatar.className = 'bubble-avatar';
        avatar.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
        
        const content = document.createElement('div');
        content.className = 'bubble-content';
        
        const header = document.createElement('div');
        header.className = 'ai-bubble-header';
        header.innerHTML = `
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>${currentMode === 'analyst' ? 'Market Analyst Pro' : 'Bud.Buddy Model'}</span>
        `;
        
        const textContent = document.createElement('div');
        textContent.className = 'ai-text-content';
        textContent.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'bubble-actions';
        
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.title = 'Copy text';
        copyBtn.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>`;
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(textContent.innerText);
        };
        
        const editBtn = null; // Removing edit button for AI bubble
        
        actionsDiv.appendChild(copyBtn);

        content.appendChild(header);
        content.appendChild(textContent);
        bubble.appendChild(avatar);
        bubble.appendChild(content);
        bubble.appendChild(actionsDiv);
        return { bubble, content, textContent };
    }

    function processJSONChartsFromText(text, containerDiv) {
        const jsonRegex = /```json\s*([\s\S]*?)\s*```/g;
        let cleanedText = text;
        let match;
        let chartRendered = false;
        
        // Loop through all json blocks
        while ((match = jsonRegex.exec(text)) !== null) {
            try {
                const chartData = JSON.parse(match[1]);
                if (chartData.bar || chartData.pie || chartData.line || chartData.histogram) {
                    renderChartsInBubble(chartData, containerDiv);
                    cleanedText = cleanedText.replace(match[0], '');
                    chartRendered = true;
                }
            } catch (e) {
                console.error("Failed to parse JSON chart payload:", e);
            }
        }
        return { text: cleanedText, rendered: chartRendered };
    }

    function renderChartsInBubble(chartData, containerDiv) {
        const chartsDiv = document.createElement('div');
        chartsDiv.className = 'bubble-charts';
        
        const types = ['bar', 'pie', 'line', 'histogram'];
        types.forEach(type => {
            if (chartData[type]) {
                let labels = chartData[type].labels || [];
                let values = chartData[type].values;
                let label = chartData[type].label || 'Dataset';
                
                // Fallbacks for LLM hallucinations
                if (!values && chartData[type].datasets && chartData[type].datasets.length > 0) {
                    values = chartData[type].datasets[0].data || chartData[type].datasets[0].values;
                    label = chartData[type].datasets[0].label || label;
                }
                if (!values && chartData[type].data) {
                    values = chartData[type].data;
                }
                
                if (!values || !Array.isArray(values) || values.length === 0) {
                    console.warn(`Chart rendering skipped for ${type}: missing or empty values`, chartData[type]);
                    return;
                }
                const card = document.createElement('div');
                card.className = 'bubble-chart-card';
                const canvas = document.createElement('canvas');
                
                // unique ID so Chart.js can attach to it
                const canvasId = 'chart-' + Math.random().toString(36).substring(7);
                canvas.id = canvasId;
                
                card.appendChild(canvas);
                chartsDiv.appendChild(card);
                
                // We must append to DOM before Chart.js can render
                setTimeout(() => {
                    const ctx = document.getElementById(canvasId).getContext('2d');
                    
                    let chartType = type === 'histogram' ? 'bar' : type;
                    let bgColors = ['rgba(16, 185, 129, 0.7)', 'rgba(5, 150, 105, 0.7)', 'rgba(251, 191, 36, 0.7)', 'rgba(245, 158, 11, 0.7)', 'rgba(20, 184, 166, 0.7)'];
                    
                    if (type === 'histogram') {
                        new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: chartData[type].labels,
                                datasets: [{
                                    label: chartData[type].label,
                                    data: chartData[type].values,
                                    backgroundColor: 'rgba(16, 185, 129, 0.5)',
                                    borderColor: '#10b981',
                                    borderWidth: 1,
                                    barPercentage: 1.0,
                                    categoryPercentage: 1.0
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false, layout: { padding: 20 }, scales: { x: { display: false } }, plugins: { legend: { labels: { color: '#f8fafc' } } } }
                        });
                    } else if (type === 'line') {
                        new Chart(ctx, {
                            type: 'line',
                            data: {
                                labels: chartData[type].labels,
                                datasets: [{
                                    label: chartData[type].label,
                                    data: chartData[type].values,
                                    borderColor: '#fbbf24',
                                    backgroundColor: 'rgba(251, 191, 36, 0.1)',
                                    tension: 0.3,
                                    fill: true
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false, layout: { padding: 20 }, plugins: { legend: { labels: { color: '#f8fafc' } } }, scales: { y: { ticks: { color: '#94a3b8' } }, x: { ticks: { color: '#94a3b8' } } } }
                        });
                    } else {
                        new Chart(ctx, {
                            type: chartType,
                            data: {
                                labels: chartData[type].labels,
                                datasets: [{
                                    label: chartData[type].label,
                                    data: chartData[type].values,
                                    backgroundColor: bgColors,
                                    borderColor: '#0f172a',
                                    borderWidth: 2
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false, layout: { padding: 20 }, plugins: { legend: { labels: { color: '#f8fafc' } } } }
                        });
                    }
                }, 100);
            }
        });
        
        containerDiv.insertBefore(chartsDiv, containerDiv.firstChild);
    }

    async function handleAnalysis() {
        const userPrompt = userPromptInput.value.trim();
        if (!currentFile && !userPrompt) return;

        // Hide welcome screen
        if (!welcomeScreen.classList.contains('hidden')) {
            welcomeScreen.classList.add('hidden');
        }

        chatState[currentMode].hasChatted = true;

        // Add user bubble
        const userBubble = createUserBubble(userPrompt, currentFile);
        userBubble.classList.add(`mode-${currentMode}`);
        chatContainer.appendChild(userBubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Clear input, keep file unless user manually clears it
        userPromptInput.value = '';

        // Add AI bubble
        const aiBubbleObj = createAIBubble();
        aiBubbleObj.bubble.classList.add(`mode-${currentMode}`);
        chatContainer.appendChild(aiBubbleObj.bubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Disable inputs during fetch
        sendBtn.disabled = true;
        userPromptInput.disabled = true;

        if (currentMode === 'analyst') {
            let uploadSuccess = false;
            let currentAiBubble = aiBubbleObj;
            
            if (currentFile) {
                // Upload PDF to /upload_10k/
                try {
                    const uploadData = new FormData();
                    uploadData.append('file', currentFile);
                    
                    currentAiBubble.textContent.innerHTML = `<div class="typing-indicator" style="margin-bottom: 8px;"><span></span><span></span><span></span></div><div style="font-size: 0.85rem; color: var(--text-secondary); font-style: italic;">Ingesting document...</div>`;
                    
                    const res = await fetch('/upload_10k/', {
                        method: 'POST',
                        body: uploadData
                    });
                    if (!res.ok) {
                        const data = await res.json();
                        throw new Error(data.detail || 'Upload failed');
                    }
                    const uploadResult = await res.json();
                    
                    if (!userPrompt) {
                        currentAiBubble.textContent.innerHTML = `<span style="color: var(--primary);">Document ingested successfully. Please ask a question to begin analysis.</span>`;
                    } else {
                        currentAiBubble.textContent.innerHTML = `<div class="typing-indicator" style="margin-bottom: 8px;"><span></span><span></span><span></span></div><div style="font-size: 0.85rem; color: var(--text-secondary); font-style: italic;">Analyzing document and query...</div>`;
                    }
                    
                    currentFile = null;
                    fileBadge.classList.add('hidden');
                    fileInput.value = '';
                    uploadSuccess = true;
                } catch (e) {
                    currentAiBubble.textContent.innerHTML = `<span style="color: #ef4444;">${e.message}</span>`;
                    sendBtn.disabled = false;
                    userPromptInput.disabled = false;
                    userPromptInput.focus();
                    return;
                }
            }
            
            if (userPrompt) {
                // We no longer create a new bubble. The response will stream directly 
                // into currentAiBubble, replacing the loading indicator.
                
                // Query 10-K
                try {
                    const queryData = new FormData();
                    queryData.append('user_prompt', userPrompt);
                    
                    if (chatState[currentMode].history.length > 0) {
                        queryData.append('chat_history', JSON.stringify(chatState[currentMode].history));
                    }
                    
                    // Add current user prompt to history before fetch, similar to wallet mode
                    chatState[currentMode].history.push({ role: 'user', content: userPrompt });

                    const res = await fetch('/query_10k/', {
                        method: 'POST',
                        body: queryData
                    });
                    
                    if (!res.ok) {
                        const data = await res.json();
                        throw new Error(data.detail || 'Query failed');
                    }
                    
                    let markdownText = '';
                    let firstTextReceived = false;
                    const reader = res.body.getReader();
                    const decoder = new TextDecoder("utf-8");
                    let buffer = '';

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) {
                            const result = processJSONChartsFromText(markdownText, currentAiBubble.content);
                            if (result.rendered) {
                                markdownText = result.text;
                                if (typeof marked !== 'undefined') {
                                    currentAiBubble.textContent.innerHTML = marked.parse(markdownText);
                                } else {
                                    currentAiBubble.textContent.innerText = markdownText;
                                }
                            }
                            break;
                        }
                        
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop(); 

                        for (const line of lines) {
                            if (line.trim()) {
                                try {
                                    const parsed = JSON.parse(line);
                                    if (parsed.type === 'text') {
                                        if (!firstTextReceived) {
                                            currentAiBubble.textContent.innerHTML = '';
                                            firstTextReceived = true;
                                        }
                                        markdownText += parsed.chunk;
                                        if (typeof marked !== 'undefined') {
                                            currentAiBubble.textContent.innerHTML = marked.parse(markdownText);
                                        } else {
                                            currentAiBubble.textContent.innerText = markdownText;
                                        }
                                        chatContainer.scrollTop = chatContainer.scrollHeight;
                                    } else if (parsed.type === 'status') {
                                        if (!firstTextReceived) {
                                            currentAiBubble.textContent.innerHTML = `<div class="typing-indicator" style="margin-bottom: 8px;"><span></span><span></span><span></span></div><div style="font-size: 0.85rem; color: var(--text-secondary); font-style: italic;">${parsed.message}</div>`;
                                            chatContainer.scrollTop = chatContainer.scrollHeight;
                                        }
                                    } else if (parsed.type === 'charts') {
                                        renderChartsInBubble(parsed.data, currentAiBubble.content);
                                    }
                                } catch (err) {
                                    console.error('Error parsing stream line:', err);
                                }
                            }
                        }
                    }
                    if (!firstTextReceived) {
                        currentAiBubble.textContent.innerHTML = '<span style="color: var(--text-secondary); font-style: italic;">No response from RAG pipeline.</span>';
                    } else if (markdownText) {
                        chatState[currentMode].history.push({ role: 'model', content: markdownText });
                    }
                } catch (e) {
                    currentAiBubble.textContent.innerHTML = `<span style="color: #ef4444;">${e.message}</span>`;
                }
            }
            
            sendBtn.disabled = false;
            userPromptInput.disabled = false;
            userPromptInput.focus();
            return;
        }

        const formData = new FormData();
        if (currentFile) formData.append('file', currentFile);
        if (userPrompt) formData.append('user_prompt', userPrompt);
        
        if (chatState[currentMode].history.length > 0) {
            formData.append('chat_history', JSON.stringify(chatState[currentMode].history));
        }

        const currentMessage = { role: 'user', content: userPrompt || (currentFile ? `[Attached File: ${currentFile.name}]` : '') };
        chatState[currentMode].history.push(currentMessage);

        try {
            const response = await fetch('/analyze-expenses/', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'An error occurred.');
            }

            let markdownText = '';
            let firstTextReceived = false;

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    const result = processJSONChartsFromText(markdownText, aiBubbleObj.content);
                    if (result.rendered) {
                        markdownText = result.text;
                        if (typeof marked !== 'undefined') {
                            aiBubbleObj.textContent.innerHTML = marked.parse(markdownText);
                        } else {
                            aiBubbleObj.textContent.innerText = markdownText;
                        }
                    }
                    break;
                }
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); 

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const parsed = JSON.parse(line);
                            if (parsed.type === 'text') {
                                if (!firstTextReceived) {
                                    aiBubbleObj.textContent.innerHTML = '';
                                    firstTextReceived = true;
                                }
                                markdownText += parsed.chunk;
                                if (typeof marked !== 'undefined') {
                                    aiBubbleObj.textContent.innerHTML = marked.parse(markdownText);
                                } else {
                                    aiBubbleObj.textContent.innerText = markdownText;
                                }
                                chatContainer.scrollTop = chatContainer.scrollHeight;
                            } else if (parsed.type === 'status') {
                                if (!firstTextReceived) {
                                    aiBubbleObj.textContent.innerHTML = `<div class="typing-indicator" style="margin-bottom: 8px;"><span></span><span></span><span></span></div><div style="font-size: 0.85rem; color: var(--text-secondary); font-style: italic;">${parsed.message}</div>`;
                                    chatContainer.scrollTop = chatContainer.scrollHeight;
                                }
                            }
                        } catch (err) {
                            console.error('Error parsing stream line:', err);
                        }
                    }
                }
            }
            if (!firstTextReceived) {
                aiBubbleObj.textContent.innerHTML = '<span style="color: var(--text-secondary); font-style: italic;">Research complete. No further summary was provided.</span>';
            } else if (markdownText) {
                chatState[currentMode].history.push({ role: 'model', content: markdownText });
            }
        } catch (error) {
            aiBubbleObj.textContent.innerHTML = `<span style="color: #ef4444;">${error.message}</span>`;
        } finally {
            sendBtn.disabled = false;
            userPromptInput.disabled = false;
            userPromptInput.focus();
        }
    }
});
