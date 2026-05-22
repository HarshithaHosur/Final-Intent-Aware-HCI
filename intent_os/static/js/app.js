document.addEventListener('DOMContentLoaded', () => {
    
    // Determine which page we are on
    const isGesturePage = document.getElementById('gesture-list') !== null;
    const isVoicePage = document.getElementById('voice-list') !== null;

    let currentData = null;
    let selectedId = null;

    // --- CSRF Token Helper ---
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    // --- GESTURE PAGE LOGIC ---
    if (isGesturePage) {
        const fetchGestures = () => {
            fetch('/gestures/')
                .then(res => res.json())
                .then(data => {
                    if(data.status === 'success') {
                        currentData = data.gestures;
                        renderGestureList();
                        if(selectedId) {
                            renderGestureDetails(selectedId);
                        }
                    }
                });
        };

        const renderGestureList = () => {
            const listContainer = document.getElementById('gesture-list');
            listContainer.innerHTML = '';
            
            currentData.forEach(gesture => {
                const div = document.createElement('div');
                div.className = `list-item ${selectedId === gesture.id ? 'selected' : ''}`;
                div.onclick = () => {
                    selectedId = gesture.id;
                    renderGestureList();
                    renderGestureDetails(gesture.id);
                };
                
                div.innerHTML = `
                    <div class="item-info">
                        <h4 class="gesture-title"></h4>
                        <p>${gesture.type}</p>
                    </div>
                    <div class="status-badge">READY</div>
                `;
                listContainer.appendChild(div);
                
                div.querySelector('.gesture-title').innerHTML = getIcon(gesture.icon) + ' ' + gesture.name;
            });
        };

        const renderGestureDetails = (id) => {
            const gesture = currentData.find(g => g.id === id);
            if(!gesture) return;

            document.getElementById('gesture-details').style.display = 'flex';
            document.getElementById('gesture-icon').innerHTML = getIcon(gesture.icon);
            document.getElementById('gesture-description').innerText = gesture.description;
            document.getElementById('gesture-action-select').value = gesture.action;
            document.getElementById('gesture-type').innerText = gesture.type;
        };

        const getIcon = (iconStr) => {
            const icons = {
                'swipe_right': '<span class="swipe-animation right">🖐</span>',
                'swipe_left': '<span class="swipe-animation left">🖐</span>',
                'pinch': '🤏',
                'fist': '✊',
                'palm': '🖐',
                'peace': '✌️',
                'thumbs_up': '👍',
                'thumbs_down': '👎',
                'index_cursor': '👆'
            };
            return icons[iconStr] || '✨';
        };

        document.getElementById('save-gesture-btn').addEventListener('click', () => {
            const newAction = document.getElementById('gesture-action-select').value;
            fetch('/gestures/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ id: selectedId, action: newAction })
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'success') {
                    alert('Gesture mapping saved successfully!');
                    fetchGestures();
                }
            });
        });

        fetchGestures();
        setInterval(fetchGestures, 5000); // Polling every 5s
    }


    // --- VOICE PAGE LOGIC ---
    if (isVoicePage) {
        let currentWakeWord = 'System';

        const fetchVoiceData = () => {
            fetch('/voice-commands/')
                .then(res => res.json())
                .then(data => {
                    if(data.status === 'success') {
                        currentData = data.commands;
                        renderVoiceList();
                        if(selectedId) {
                            renderVoiceDetails(selectedId);
                        }
                    }
                });

            fetch('/voice/wake-word/')
                .then(res => res.json())
                .then(data => {
                    if(data.status === 'success') {
                        currentWakeWord = data.wake_word;
                        if(document.activeElement !== document.getElementById('wake-word-input')) {
                            document.getElementById('wake-word-input').value = currentWakeWord;
                        }
                    }
                });
        };

        const renderVoiceList = () => {
            const listContainer = document.getElementById('voice-list');
            listContainer.innerHTML = '';
            
            currentData.forEach(cmd => {
                const div = document.createElement('div');
                div.className = `list-item ${selectedId === cmd.id ? 'selected' : ''}`;
                div.onclick = () => {
                    selectedId = cmd.id;
                    renderVoiceList();
                    renderVoiceDetails(cmd.id);
                };
                
                div.innerHTML = `
                    <div class="item-info">
                        <h4>🎤 "${cmd.command}"</h4>
                        <p>${cmd.action}</p>
                    </div>
                    <div class="status-badge">ONLINE</div>
                `;
                listContainer.appendChild(div);
            });
        };

        const renderVoiceDetails = (id) => {
            const cmd = currentData.find(c => c.id === id);
            if(!cmd) return;

            document.getElementById('dynamic-voice-details').style.display = 'flex';
            document.getElementById('voice-how-to').innerText = `Say: ${currentWakeWord} ${cmd.command}`;
            
            const tipsUl = document.getElementById('voice-tips');
            tipsUl.innerHTML = '';
            cmd.tips.forEach(tip => {
                const li = document.createElement('li');
                li.innerText = tip;
                tipsUl.appendChild(li);
            });

            const select = document.getElementById('voice-action-select');
            let found = false;
            for(let i=0; i<select.options.length; i++) {
                if(select.options[i].value === cmd.action) found = true;
            }
            if(!found) {
                const opt = document.createElement('option');
                opt.value = cmd.action;
                opt.text = cmd.action;
                select.add(opt);
            }
            select.value = cmd.action;
        };

        document.getElementById('save-voice-btn').addEventListener('click', () => {
            const newAction = document.getElementById('voice-action-select').value;
            fetch('/voice-commands/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ id: selectedId, action: newAction })
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'success') {
                    alert('Command mapping saved successfully!');
                    fetchVoiceData();
                }
            });
        });

        document.getElementById('save-wake-word-btn').addEventListener('click', () => {
            const newWW = document.getElementById('wake-word-input').value;
            fetch('/voice/wake-word/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ wake_word: newWW })
            })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'success') {
                    alert('Wake word updated!');
                    fetchVoiceData();
                }
            });
        });

        fetchVoiceData();
        setInterval(fetchVoiceData, 5000); // Polling every 5s
    }

    // ── DASHBOARD REAL-TIME FEED & HISTORY (1s polling) ──
    const liveFeedEl = document.getElementById('live-activity-feed');
    const recentCommandsEl = document.getElementById('recent-commands-list');
    const lastCommandEl = document.getElementById('last-command-value');

    if (liveFeedEl || recentCommandsEl || lastCommandEl) {
        function formatTimeAgo(isoString) {
            const date = new Date(isoString);
            const now = new Date();
            const diffMs = now - date;
            const diffSecs = Math.max(0, Math.floor(diffMs / 1000));
            if (diffSecs < 5) return 'JUST NOW';
            if (diffSecs < 60) return `${diffSecs} SEC AGO`;
            const diffMins = Math.floor(diffSecs / 60);
            return `${diffMins} MIN${diffMins > 1 ? 'S' : ''} AGO`;
        }

        function updateDashboardLogs() {
            // 1. Fetch system logs for the Live Activity Feed
            fetch('/api/system-logs/')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success' && liveFeedEl) {
                        if (data.logs.length === 0) {
                            liveFeedEl.innerHTML = '<div style="color: var(--text-secondary); font-size: 12px; padding: 10px 0;">No logs available. Start gesture/voice engine.</div>';
                            return;
                        }

                        let html = '';
                        // Limit to top 5 for visual clarity
                        data.logs.slice(0, 5).forEach(log => {
                            let dotColor = 'grey';
                            if (log.event_type === 'gesture') dotColor = 'cyan';
                            if (log.event_type === 'voice') dotColor = 'purple';
                            if (log.event_type === 'error') dotColor = 'red';

                            const timeAgo = formatTimeAgo(log.timestamp);
                            const actionUpper = log.action.toUpperCase();
                            const cmdUpper = log.command.toUpperCase();

                            html += `
                                <div class="activity-item">
                                    <div class="activity-dot ${dotColor}"></div>
                                    <div class="activity-details">
                                        <div class="act-title" style="color: var(--text-primary)">
                                            ${log.event_type.toUpperCase()}: ${log.command}
                                        </div>
                                        <div class="act-time">${timeAgo} • "${actionUpper}"</div>
                                    </div>
                                </div>
                            `;
                        });
                        liveFeedEl.innerHTML = html;
                    }
                })
                .catch(err => console.error('Error fetching system logs:', err));

            // 2. Fetch recent commands for the Recent Commands panel
            fetch('/api/recent-commands/')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Update "Last Command" top card if we have any voice/gesture commands
                        if (data.commands.length > 0 && lastCommandEl) {
                            const lastCmd = data.commands[0];
                            lastCommandEl.textContent = `"${lastCmd.command}"`;
                            if (lastCmd.status === 'executing') {
                                lastCommandEl.style.color = 'var(--accent-purple)';
                            } else if (lastCmd.status === 'completed') {
                                lastCommandEl.style.color = 'var(--accent-cyan)';
                            } else {
                                lastCommandEl.style.color = 'var(--accent-red)';
                            }
                        }

                        if (recentCommandsEl) {
                            if (data.commands.length === 0) {
                                recentCommandsEl.innerHTML = '<div style="color: var(--text-secondary); font-size: 12px; padding: 10px 0;">No recent commands found.</div>';
                                return;
                            }

                            let html = '';
                            data.commands.forEach(cmd => {
                                let statusIcon = '✅';
                                let statusColor = 'var(--accent-cyan)';
                                if (cmd.status === 'executing') {
                                    statusIcon = '⚡ Executing...';
                                    statusColor = 'var(--accent-purple)';
                                } else if (cmd.status === 'error') {
                                    statusIcon = '❌ Failed';
                                    statusColor = 'var(--accent-red)';
                                } else {
                                    statusIcon = '✅ Completed';
                                }

                                const timeAgo = formatTimeAgo(cmd.timestamp);

                                html += `
                                    <div class="activity-item">
                                        <div class="activity-dot ${cmd.event_type === 'voice' ? 'purple' : 'cyan'}"></div>
                                        <div class="activity-details" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                                            <div style="flex: 1;">
                                                <div class="act-title" style="color: var(--text-primary)">
                                                    ${cmd.event_type === 'voice' ? '🎤' : '✋'} ${cmd.command}
                                                </div>
                                                <div class="act-time">${timeAgo}</div>
                                            </div>
                                            <span style="font-size: 11px; font-weight: bold; color: ${statusColor}; background: rgba(255,255,255,0.05); padding: 3px 6px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.08)">
                                                ${statusIcon}
                                            </span>
                                        </div>
                                    </div>
                                `;
                            });
                            recentCommandsEl.innerHTML = html;
                        }
                    }
                })
                .catch(err => console.error('Error fetching recent commands:', err));
        }

        // Initialize and poll every 1 second for instant real-time experience!
        updateDashboardLogs();
        setInterval(updateDashboardLogs, 1000);
    }
});
