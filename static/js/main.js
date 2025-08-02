// Main JavaScript for lottery web application

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const form = document.getElementById('lottery-form');
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const mode1Params = document.getElementById('mode-1-params');
    const mode3Params = document.getElementById('mode-3-params');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const downloadBtn = document.getElementById('download-btn');
    const resetBtn = document.getElementById('reset-btn');

    // Current result ID
    let currentResultId = null;

    // Mode change handler
    modeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            // Hide all mode params
            mode1Params.style.display = 'none';
            mode3Params.style.display = 'none';

            // Show relevant params
            if (this.value === '1') {
                mode1Params.style.display = 'block';
            } else if (this.value === '3') {
                mode3Params.style.display = 'block';
            }
        });
    });

    // Form submit handler
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Get form data
        const formData = new FormData(form);
        const data = {
            url: formData.get('url'),
            mode: formData.get('mode'),
            winner_count: parseInt(formData.get('winner_count'))
        };

        // Add mode-specific parameters
        if (data.mode === '1') {
            data.keyword = formData.get('keyword');
        } else if (data.mode === '3') {
            data.mention_count = parseInt(formData.get('mention_count'));
        }

        // Validate URL
        if (!isValidUrl(data.url)) {
            alert('請輸入有效的 Threads 或 Instagram 網址');
            return;
        }

        // Show loading
        form.style.display = 'none';
        loading.style.display = 'block';
        results.style.display = 'none';

        try {
            // Send request
            const response = await fetch('/lottery', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                // Display results
                displayResults(result);
                currentResultId = result.result_id;
            } else {
                throw new Error(result.error || '抽獎失敗');
            }
        } catch (error) {
            alert('錯誤：' + error.message);
            resetForm();
        } finally {
            loading.style.display = 'none';
        }
    });

    // Download button handler
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            if (currentResultId) {
                window.location.href = `/download/${currentResultId}`;
            }
        });
    }

    // Reset button handler
    if (resetBtn) {
        resetBtn.addEventListener('click', resetForm);
    }

    // Helper functions
    function isValidUrl(url) {
        try {
            const urlObj = new URL(url);
            const hostname = urlObj.hostname.toLowerCase();
            return hostname.includes('threads.net') || 
                   hostname.includes('instagram.com');
        } catch {
            return false;
        }
    }

    function displayResults(result) {
        // Update result info
        document.getElementById('result-time').textContent = formatDateTime(result.timestamp);
        document.getElementById('result-mode').textContent = getModeName(result.mode);
        document.getElementById('result-total').textContent = result.total_participants;

        // Display winners
        const winnersList = document.getElementById('winners-list');
        winnersList.innerHTML = '';

        if (result.winners && result.winners.length > 0) {
            result.winners.forEach((winner, index) => {
                const winnerCard = createWinnerCard(winner, index + 1);
                winnersList.appendChild(winnerCard);
            });
        } else {
            winnersList.innerHTML = '<p>沒有符合條件的參與者</p>';
        }

        // Show results section
        results.style.display = 'block';
    }

    function createWinnerCard(winner, rank) {
        const card = document.createElement('div');
        card.className = 'winner-card';
        
        // Default avatar if not provided
        const avatarUrl = winner.avatar_url || '/static/images/default-avatar.png';
        
        card.innerHTML = `
            <img src="${avatarUrl}" alt="${winner.username}" class="winner-avatar" onerror="this.src='/static/images/default-avatar.png'">
            <div class="winner-info">
                <h4>#${rank} @${winner.username}</h4>
                <p class="winner-comment">${winner.comment}</p>
            </div>
        `;
        
        return card;
    }

    function getModeName(mode) {
        const modeNames = {
            '1': '關鍵字篩選',
            '2': '所有留言者',
            '3': '標註指定帳號'
        };
        return modeNames[mode] || '未知模式';
    }

    function formatDateTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString('zh-TW');
    }

    function resetForm() {
        form.style.display = 'block';
        results.style.display = 'none';
        form.reset();
        currentResultId = null;
        
        // Reset to mode 1
        mode1Params.style.display = 'block';
        mode3Params.style.display = 'none';
    }
});