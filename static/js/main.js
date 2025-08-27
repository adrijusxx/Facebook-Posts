// Main JavaScript for Facebook Trucking News Automation

// Global variables
let currentPostData = null;
let refreshInterval = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Facebook Trucking News Automation loaded');
    
    // Start auto-refresh for dashboard
    if (window.location.pathname === '/') {
        startAutoRefresh();
    }
    
    // Initialize tooltips
    initializeTooltips();
});

// Utility functions
function showAlert(message, type = 'info', timeout = 5000) {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type} alert-dismissible fade show`;
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the main container
    const main = document.querySelector('main');
    main.insertBefore(alertContainer, main.firstChild);
    
    // Auto-dismiss after timeout
    if (timeout > 0) {
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(alertContainer);
            alert.close();
        }, timeout);
    }
}

function showLoading() {
    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();
}

function hideLoading() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
    if (modal) {
        modal.hide();
    }
}

function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function startAutoRefresh() {
    // Refresh dashboard data every 2 minutes
    refreshInterval = setInterval(() => {
        if (document.visibilityState === 'visible') {
            refreshDashboardData();
        }
    }, 120000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// API interaction functions
function fetchNews() {
    showLoading();
    
    fetch('/api/fetch_news', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showAlert(`Successfully fetched ${data.message}!`, 'success');
            // Refresh the page after a short delay
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showAlert('Error fetching news: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showAlert('Error fetching news: ' + error.message, 'danger');
    });
}

function postNow() {
    if (!confirm('Are you sure you want to post now?')) {
        return;
    }
    
    showLoading();
    
    fetch('/api/post_now', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showAlert(data.message, 'success');
            // Refresh the page after a short delay
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showAlert('Error posting: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showAlert('Error posting: ' + error.message, 'danger');
    });
}

function postSingle(postId) {
    if (!confirm('Are you sure you want to post this article now?')) {
        return;
    }
    
    showLoading();
    
    // This would need to be implemented in the backend
    fetch('/api/post_single', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ post_id: postId })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showAlert('Post published successfully!', 'success');
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showAlert('Error posting: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showAlert('Error posting: ' + error.message, 'danger');
    });
}

function refreshPosts() {
    const button = event.target.closest('button');
    const icon = button.querySelector('i');
    
    // Add spinning animation
    icon.className = 'fas fa-sync-alt fa-spin';
    button.disabled = true;
    
    fetch('/api/posts')
        .then(response => response.json())
        .then(posts => {
            // Update the posts table
            updatePostsTable(posts);
            
            // Remove spinning animation
            icon.className = 'fas fa-sync-alt';
            button.disabled = false;
            
            showAlert('Posts refreshed successfully!', 'success', 3000);
        })
        .catch(error => {
            console.error('Error refreshing posts:', error);
            
            // Remove spinning animation
            icon.className = 'fas fa-sync-alt';
            button.disabled = false;
            
            showAlert('Error refreshing posts: ' + error.message, 'danger');
        });
}

function updatePostsTable(posts) {
    const tbody = document.getElementById('postsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    posts.slice(0, 10).forEach(post => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div class="post-title" title="${post.title}">
                    ${post.title.length > 60 ? post.title.substring(0, 60) + '...' : post.title}
                </div>
            </td>
            <td>
                <span class="badge bg-${post.status === 'posted' ? 'success' : post.status === 'pending' ? 'warning' : 'danger'}">
                    ${post.status.charAt(0).toUpperCase() + post.status.slice(1)}
                </span>
            </td>
            <td>${post.source || 'Unknown'}</td>
            <td>
                <small>${new Date(post.created_at).toLocaleDateString()} ${new Date(post.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</small>
            </td>
            <td>
                ${post.posted_at ? 
                    `<small>${new Date(post.posted_at).toLocaleDateString()} ${new Date(post.posted_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</small>` : 
                    '<small class="text-muted">Not posted</small>'
                }
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary btn-sm" 
                            onclick="viewPost(${post.id})" data-bs-toggle="tooltip" title="View">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${post.status === 'pending' ? 
                        `<button type="button" class="btn btn-outline-success btn-sm" 
                                onclick="postSingle(${post.id})" data-bs-toggle="tooltip" title="Post Now">
                            <i class="fas fa-paper-plane"></i>
                        </button>` : ''
                    }
                    ${post.facebook_post_id ? 
                        `<a href="https://facebook.com/${post.facebook_post_id}" 
                           target="_blank" class="btn btn-outline-info btn-sm" data-bs-toggle="tooltip" title="View on Facebook">
                            <i class="fab fa-facebook"></i>
                        </a>` : ''
                    }
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // Reinitialize tooltips
    initializeTooltips();
}

function refreshDashboardData() {
    // Silently refresh dashboard statistics
    fetch('/api/posts')
        .then(response => response.json())
        .then(posts => {
            // Update stats if elements exist
            const today = new Date().toDateString();
            const postedToday = posts.filter(p => p.posted_at && new Date(p.posted_at).toDateString() === today).length;
            const pending = posts.filter(p => p.status === 'pending').length;
            
            const postedTodayEl = document.getElementById('postedToday');
            const pendingPostsEl = document.getElementById('pendingPosts');
            
            if (postedTodayEl) postedTodayEl.textContent = postedToday;
            if (pendingPostsEl) pendingPostsEl.textContent = pending;
        })
        .catch(error => {
            console.error('Error refreshing dashboard data:', error);
        });
}

// AI-related functions
function generateAIPost() {
    const topic = document.getElementById('aiTopic').value;
    const style = document.getElementById('aiStyle').value;
    
    if (!topic.trim()) {
        showAlert('Please enter a topic.', 'warning');
        return;
    }
    
    showLoading();
    
    fetch('/api/generate_custom_post', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            topic: topic,
            style: style
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            document.getElementById('aiPreview').value = data.content;
            document.getElementById('saveAIPost').disabled = false;
            showAlert('AI content generated successfully!', 'success', 3000);
        } else {
            showAlert('Error generating content: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showAlert('Error generating content: ' + error.message, 'danger');
    });
}

function saveAIPost() {
    const content = document.getElementById('aiPreview').value;
    
    if (!content.trim()) {
        showAlert('No content to save.', 'warning');
        return;
    }
    
    // This would create a new post with the AI-generated content
    // For now, we'll just copy to clipboard and show a message
    navigator.clipboard.writeText(content).then(() => {
        showAlert('Content copied to clipboard! You can paste it as a custom post.', 'info');
        
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('aiPostModal'));
        modal.hide();
    }).catch(err => {
        showAlert('Could not copy to clipboard. Please copy the content manually.', 'warning');
    });
}

// Form validation helpers
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Cleanup when page is unloaded
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});

// Handle visibility change to pause/resume auto-refresh
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'hidden') {
        stopAutoRefresh();
    } else if (window.location.pathname === '/') {
        startAutoRefresh();
    }
});

// Global error handler for fetch requests
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showAlert('An unexpected error occurred. Please try again.', 'danger');
});

// Utility function for formatting dates
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

// Utility function for truncating text
function truncateText(text, maxLength = 100) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// View post function (referenced in dashboard.html)
function viewPost(postId) {
    // This function is implemented in dashboard.html template
    // It's defined there to access the posts data
    console.log('viewPost called with ID:', postId);
}

// Export functions for use in templates
window.fetchNews = fetchNews;
window.postNow = postNow;
window.postSingle = postSingle;
window.refreshPosts = refreshPosts;
window.generateAIPost = generateAIPost;
window.saveAIPost = saveAIPost;
window.viewPost = viewPost;
window.showAlert = showAlert;
window.showLoading = showLoading;
window.hideLoading = hideLoading;