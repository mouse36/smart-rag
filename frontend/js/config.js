/**
 * Configuration for SunnyMentor Frontend
 * Manages API endpoints and environment-specific settings
 */

class Config {
    constructor() {
        // Environment detection
        this.isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.isProduction = !this.isDevelopment;
        
        // API Configuration
        this.apiConfig = this.getApiConfig();
        
        // Feature flags
        this.features = {
            enableHealthChecks: true,
            enableBackendMonitoring: true,
            enableErrorBanners: true
        };
    }
    
    /**
     * Get API configuration based on environment
     */
    getApiConfig() {
        if (this.isDevelopment) {
            // Local development - connect to local backend
            return {
                baseUrl: 'http://127.0.0.1:5000',
                timeout: 10000,
                retryAttempts: 3
            };
        } else {
            // Production - connect to Railway backend
            // You'll need to replace this with your actual Railway URL
            return {
                baseUrl: 'https://sunnymentor-production.up.railway.app', // Your actual Railway URL
                timeout: 15000,
                retryAttempts: 3
            };
        }
    }
    
    /**
     * Get the full API URL for a specific endpoint
     * @param {string} endpoint - API endpoint (e.g., '/health', '/chat')
     * @returns {string} Full API URL
     */
    getApiUrl(endpoint) {
        // Remove leading slash if present
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
        return `${this.apiConfig.baseUrl}/${cleanEndpoint}`;
    }
    
    /**
     * Get API request options with common headers
     * @param {Object} options - Additional options
     * @returns {Object} Fetch options
     */
    getRequestOptions(options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout: this.apiConfig.timeout
        };
        
        return {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };
    }
    
    /**
     * Update API base URL (useful for dynamic configuration)
     * @param {string} newBaseUrl - New base URL
     */
    updateApiBaseUrl(newBaseUrl) {
        this.apiConfig.baseUrl = newBaseUrl;
        console.log('API base URL updated to:', newBaseUrl);
    }
    
    /**
     * Get current environment info
     * @returns {Object} Environment information
     */
    getEnvironmentInfo() {
        return {
            isDevelopment: this.isDevelopment,
            isProduction: this.isProduction,
            hostname: window.location.hostname,
            protocol: window.location.protocol,
            apiBaseUrl: this.apiConfig.baseUrl
        };
    }
}

// Create global config instance
window.appConfig = new Config();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Config;
}
