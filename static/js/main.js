// Main JavaScript for lottery web application

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const form = document.getElementById('lottery-form');
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const mode1Params = document.getElementById('mode-1-params');
    const mode3Params = document.getElementById('mode-3-params');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const errorSection = document.getElementById('error-section');
    const downloadBtn = document.getElementById('download-btn');
    const resetBtn = document.getElementById('reset-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const retryBtn = document.getElementById('retry-btn');
    const backBtn = document.getElementById('back-btn');
    const loadingText = document.getElementById('loading-text');
    const errorMessage = document.getElementById('error-message');

    // Current result ID and request controller
    let currentResultId = null;
    let currentController = null;
    let lastFormData = null;

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
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        submitLottery();
    });

    async function submitLottery() {
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

        // Store form data for retry
        lastFormData = data;

        console.log('Submitting lottery request:', data);

        // Validate URL
        if (!isValidUrl(data.url)) {
            showError('請輸入有效的 Threads 或 Instagram 網址');
            return;
        }

        // Show loading
        showLoading('正在驗證網址...');

        try {
            // Create new controller for this request
            currentController = new AbortController();
            const timeoutId = setTimeout(() => {
                if (currentController) {
                    currentController.abort();
                }
            }, 60000); // 60 seconds timeout

            updateLoadingText('正在爬取留言資料...');

            const response = await fetch('/lottery', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data),
                signal: currentController.signal
            });

            clearTimeout(timeoutId);

            console.log('Response status:', response.status);

            const result = await response.json();
            console.log('Response data:', result);

            if (response.ok && result.success) {
                // Display results
                displayResults(result);
                currentResultId = result.result_id;
            } else {
                throw new Error(result.error || '抽獎失敗');
            }
        } catch (error) {
            console.error('Lottery error:', error);
            
            let errorMsg = '抽獎過程中發生錯誤';
            if (error.name === 'AbortError') {
                errorMsg = '請求已取消或超時';
            } else if (error.message) {
                errorMsg = error.message;
            }
            
            showError(errorMsg);
        } finally {
            currentController = null;
        }
    }

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

    // Cancel button handler
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            if (currentController) {
                currentController.abort();
                console.log('Request cancelled by user');
            }
            resetForm();
        });
    }

    // Retry button handler
    if (retryBtn) {
        retryBtn.addEventListener('click', function() {
            if (lastFormData) {
                console.log('Retrying with last form data');
                hideError();
                submitLotteryWithData(lastFormData);
            } else {
                resetForm();
            }
        });
    }

    // Back button handler
    if (backBtn) {
        backBtn.addEventListener('click', resetForm);
    }

    async function submitLotteryWithData(data) {
        console.log('Submitting lottery request (retry):', data);

        // Show loading
        showLoading('正在重新嘗試...');

        try {
            // Create new controller for this request
            currentController = new AbortController();
            const timeoutId = setTimeout(() => {
                if (currentController) {
                    currentController.abort();
                }
            }, 60000); // 60 seconds timeout

            updateLoadingText('正在爬取留言資料...');

            const response = await fetch('/lottery', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data),
                signal: currentController.signal
            });

            clearTimeout(timeoutId);

            const result = await response.json();

            if (response.ok && result.success) {
                displayResults(result);
                currentResultId = result.result_id;
            } else {
                throw new Error(result.error || '抽獎失敗');
            }
        } catch (error) {
            console.error('Retry lottery error:', error);
            
            let errorMsg = '重試失敗';
            if (error.name === 'AbortError') {
                errorMsg = '請求已取消或超時';
            } else if (error.message) {
                errorMsg = error.message;
            }
            
            showError(errorMsg);
        } finally {
            currentController = null;
        }
    }

    // Helper functions
    function isValidUrl(url) {
        try {
            const urlObj = new URL(url);
            const hostname = urlObj.hostname.toLowerCase();
            return hostname.includes('threads.com') || 
                   hostname.includes('threads.net') ||
                   hostname.includes('instagram.com');
        } catch {
            return false;
        }
    }

    function displayResults(result) {
        console.log('Displaying results:', result);
        
        // Hide loading first
        hideLoading();
        
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
        console.log('Results displayed successfully');
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

    function showLoading(text = '正在處理，請稍候...') {
        form.style.display = 'none';
        loading.style.display = 'block';
        results.style.display = 'none';
        errorSection.style.display = 'none';
        if (loadingText) {
            loadingText.textContent = text;
        }
        console.log('Loading state: shown with text:', text);
    }

    function updateLoadingText(text) {
        if (loadingText) {
            loadingText.textContent = text;
            console.log('Loading text updated:', text);
        }
    }

    function showError(message) {
        hideLoading();
        results.style.display = 'none';
        errorSection.style.display = 'block';
        if (errorMessage) {
            errorMessage.textContent = message;
        }
        console.log('Error shown:', message);
    }

    function hideError() {
        errorSection.style.display = 'none';
        console.log('Error hidden');
    }

    function hideLoading() {
        loading.style.display = 'none';
        form.style.display = 'block';
        console.log('Loading state: hidden');
    }

    function resetForm() {
        hideLoading();
        hideError();
        results.style.display = 'none';
        form.style.display = 'block';
        form.reset();
        currentResultId = null;
        lastFormData = null;
        
        // Reset to mode 1
        mode1Params.style.display = 'block';
        mode3Params.style.display = 'none';
        console.log('Form reset completed');
    }
});