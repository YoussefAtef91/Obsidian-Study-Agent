


// Auto-resize textarea
document.getElementById('messageInput').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Send message on Enter (but allow Shift+Enter for new lines)
document.getElementById('messageInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Scroll to bottom on page load if there are messages
window.addEventListener('DOMContentLoaded', function() {
    scrollToBottom();
});

function addMessageToChat(content, type) {
    const container = document.getElementById('chatMessages');
    
    // Hide welcome message if it exists
    const welcomeMessage = document.getElementById('welcomeMessage');
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${content.replace(/\n/g, '<br>')}
        </div>
    `;
    
    container.appendChild(messageDiv);
    scrollToBottom();
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message || !currentSessionId) return;
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    input.value = '';
    input.style.height = 'auto';
    
    // Show loading indicator
    document.getElementById('loadingIndicator').style.display = 'block';
    
    try {
        const response = await fetch(`/chat/${currentSessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                input: message
            })
        });
        
        const data = await response.json();
        
        // Hide loading indicator
        document.getElementById('loadingIndicator').style.display = 'none';
        
        // Add agent response to chat
        addMessageToChat(data.response, 'agent');
        
    } catch (error) {
        console.error('Error sending message:', error);
        document.getElementById('loadingIndicator').style.display = 'none';
        addMessageToChat('Sorry, I encountered an error. Please try again.', 'agent');
    }
}

async function createNewSession() {
    try {
        const response = await fetch('/sessions/new', { method: 'POST' });
        const data = await response.json();
        
        if (data.error) {
            console.error('Error creating session:', data.error);
            return;
        }
        
        // Redirect to the new session
        window.location.href = `/chat/${data.session_id}`;
    } catch (error) {
        console.error('Error creating new session:', error);
    }
}

async function deleteSession(sessionId, event) {
    event.preventDefault();
    event.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this session?')) {
        return;
    }
    
    try {
        const response = await fetch(`/sessions/${sessionId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (result.status === 'success') {
            // If we're currently viewing the deleted session, redirect to home
            if (currentSessionId === sessionId) {
                window.location.href = '/';
            } else {
                // Otherwise, just reload the page to update the sidebar
                window.location.reload();
            }
        } else {
            console.error('Error deleting session:', result.message);
            alert('Failed to delete session. Please try again.');
        }
    } catch (error) {
        console.error('Error deleting session:', error);
        alert('Failed to delete session. Please try again.');
    }
}

function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}