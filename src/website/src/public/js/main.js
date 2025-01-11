document.addEventListener('DOMContentLoaded', () => {
    const checkHealthButton = document.getElementById('checkHealth');
    const healthStatus = document.getElementById('healthStatus');
    
    async function checkServerHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            if (data.status === 'ok') {
                healthStatus.textContent = '✅ Server is healthy';
                healthStatus.style.color = '#27ae60';
            } else {
                healthStatus.textContent = '❌ Server status unknown';
                healthStatus.style.color = '#e74c3c';
            }
        } catch (error) {
            healthStatus.textContent = '❌ Server is not responding';
            healthStatus.style.color = '#e74c3c';
            console.error('Error checking server health:', error);
        }
    }
    
    checkHealthButton.addEventListener('click', checkServerHealth);
}); 