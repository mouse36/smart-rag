/**
 * Railway Setup Utility
 * Helps configure and test Railway backend connection
 */

class RailwaySetup {
    constructor() {
        this.config = window.appConfig;
    }
    
    /**
     * Update Railway URL in configuration
     * @param {string} railwayUrl - The Railway app URL (e.g., https://your-app.railway.app)
     */
    updateRailwayUrl(railwayUrl) {
        if (!railwayUrl) {
            console.error('Railway URL is required');
            return false;
        }
        
        // Ensure URL has protocol
        if (!railwayUrl.startsWith('http://') && !railwayUrl.startsWith('https://')) {
            railwayUrl = 'https://' + railwayUrl;
        }
        
        // Remove trailing slash
        railwayUrl = railwayUrl.replace(/\/$/, '');
        
        // Update configuration
        this.config.updateApiBaseUrl(railwayUrl);
        
        // Save to localStorage for persistence
        localStorage.setItem('railway_url', railwayUrl);
        
        console.log('Railway URL updated to:', railwayUrl);
        return true;
    }
    
    /**
     * Get stored Railway URL
     * @returns {string|null} Stored Railway URL or null
     */
    getStoredRailwayUrl() {
        return localStorage.getItem('railway_url');
    }
    
    /**
     * Test connection to Railway backend
     * @param {string} railwayUrl - Optional Railway URL to test
     * @returns {Promise<Object>} Test results
     */
    async testConnection(railwayUrl = null) {
        const url = railwayUrl || this.config.getApiUrl('health');
        
        try {
            console.log('Testing connection to:', url);
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                timeout: 10000
            });
            
            if (response.ok) {
                const data = await response.json();
                return {
                    success: true,
                    status: response.status,
                    data: data,
                    url: url
                };
            } else {
                return {
                    success: false,
                    status: response.status,
                    error: `HTTP ${response.status}: ${response.statusText}`,
                    url: url
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message,
                url: url
            };
        }
    }
    
    /**
     * Test all critical endpoints
     * @returns {Promise<Object>} Test results for all endpoints
     */
    async testAllEndpoints() {
        const endpoints = [
            { name: 'Health Check', path: 'health' },
            { name: 'Authentication', path: 'auth/validate-phone' },
            { name: 'Chat', path: 'chat' }
        ];
        
        const results = {};
        
        for (const endpoint of endpoints) {
            const url = this.config.getApiUrl(endpoint.path);
            console.log(`Testing ${endpoint.name}:`, url);
            
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json'
                    },
                    timeout: 10000
                });
                
                results[endpoint.name] = {
                    success: response.ok,
                    status: response.status,
                    url: url
                };
            } catch (error) {
                results[endpoint.name] = {
                    success: false,
                    error: error.message,
                    url: url
                };
            }
        }
        
        return results;
    }
    
    /**
     * Display connection test results in the UI
     * @param {Object} results - Test results
     */
    displayTestResults(results) {
        // Create or find results container
        let container = document.getElementById('railway-test-results');
        if (!container) {
            container = document.createElement('div');
            container.id = 'railway-test-results';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                font-family: Arial, sans-serif;
            `;
            document.body.appendChild(container);
        }
        
        let html = '<h3>Railway Connection Test</h3>';
        
        if (results.success !== undefined) {
            // Single endpoint test
            if (results.success) {
                html += `<div style="color: green;">✅ Connection successful</div>`;
                html += `<div>Status: ${results.status}</div>`;
                if (results.data) {
                    html += `<div>Response: ${JSON.stringify(results.data, null, 2)}</div>`;
                }
            } else {
                html += `<div style="color: red;">❌ Connection failed</div>`;
                html += `<div>Error: ${results.error}</div>`;
            }
            html += `<div>URL: ${results.url}</div>`;
        } else {
            // Multiple endpoints test
            for (const [name, result] of Object.entries(results)) {
                if (result.success) {
                    html += `<div style="color: green;">✅ ${name}: OK (${result.status})</div>`;
                } else {
                    html += `<div style="color: red;">❌ ${name}: Failed - ${result.error || result.status}</div>`;
                }
            }
        }
        
        html += '<br><button onclick="this.parentElement.remove()">Close</button>';
        container.innerHTML = html;
    }
    
    /**
     * Initialize Railway setup
     */
    init() {
        // Check if we have a stored Railway URL
        const storedUrl = this.getStoredRailwayUrl();
        if (storedUrl && this.config.isProduction) {
            this.updateRailwayUrl(storedUrl);
        }
        
        // Add setup functions to window for easy access
        window.railwaySetup = {
            updateUrl: (url) => this.updateRailwayUrl(url),
            testConnection: (url) => this.testConnection(url),
            testAllEndpoints: () => this.testAllEndpoints(),
            displayResults: (results) => this.displayTestResults(results)
        };
        
        console.log('Railway setup initialized');
        console.log('Available commands:');
        console.log('- railwaySetup.updateUrl("your-railway-url")');
        console.log('- railwaySetup.testConnection()');
        console.log('- railwaySetup.testAllEndpoints()');
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (window.appConfig) {
            new RailwaySetup().init();
        }
    });
} else {
    if (window.appConfig) {
        new RailwaySetup().init();
    }
}
