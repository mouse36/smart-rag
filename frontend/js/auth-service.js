/**
 * Authentication Service for SunnyMentor
 * Handles JWT token-based authentication securely
 */

class AuthService {
    constructor() {
        this.tokenKey = 'sunnymentor_jwt_token';
        this.userKey = 'sunnymentor_user_data';
        // Use global config for API base URL
        this.apiBaseUrl = window.appConfig ? window.appConfig.getApiUrl('') : 'http://127.0.0.1:5000';
    }

    /**
     * Store JWT token securely
     * @param {string} token - JWT token
     * @param {Object} userData - User information
     */
    setToken(token, userData) {
        // Store token in sessionStorage (cleared when browser closes)
        sessionStorage.setItem(this.tokenKey, token);
        
        // Store user data (without sensitive info)
        const safeUserData = {
            email: userData.email,
            username: userData.username,
            profile_picture: userData.profile_picture
        };
        sessionStorage.setItem(this.userKey, JSON.stringify(safeUserData));
    }

    /**
     * Get stored JWT token
     * @returns {string|null} JWT token or null if not found
     */
    getToken() {
        return sessionStorage.getItem(this.tokenKey);
    }

    /**
     * Get stored user data
     * @returns {Object|null} User data or null if not found
     */
    getUserData() {
        const userData = sessionStorage.getItem(this.userKey);
        return userData ? JSON.parse(userData) : null;
    }

    /**
     * Check if user is authenticated
     * @returns {boolean} True if authenticated, false otherwise
     */
    isAuthenticated() {
        const token = this.getToken();
        return token !== null;
    }

    /**
     * Clear authentication data
     */
    clearAuth() {
        sessionStorage.removeItem(this.tokenKey);
        sessionStorage.removeItem(this.userKey);
    }

    /**
     * Validate token with server
     * @returns {Promise<boolean>} True if token is valid, false otherwise
     */
    async validateToken() {
        const token = this.getToken();
        if (!token) {
            return false;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/validate-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: token })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update user data with fresh data from server
                    this.setToken(token, data.user);
                    return true;
                }
            }
            
            // Token is invalid, clear it
            this.clearAuth();
            return false;
        } catch (error) {
            console.error('Token validation error:', error);
            // On network error, assume token is still valid for now
            // This prevents logout on temporary network issues
            return true;
        }
    }

    /**
     * Login with email and password
     * @param {string} email - User email
     * @param {string} password - User password
     * @returns {Promise<Object>} Login result
     */
    async login(email, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (data.success && data.token) {
                // Store token and user data
                this.setToken(data.token, data);
                return {
                    success: true,
                    user: data
                };
            } else {
                return {
                    success: false,
                    error: data.error,
                    message: data.message
                };
            }
        } catch (error) {
            console.error('Login error:', error);
            return {
                success: false,
                error: 'network_error',
                message: 'Network error occurred during login'
            };
        }
    }

    /**
     * Logout user
     * @returns {Promise<Object>} Logout result
     */
    async logout() {
        const token = this.getToken();
        if (!token) {
            this.clearAuth();
            return { success: true };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            // Always clear local auth data regardless of server response
            this.clearAuth();

            if (response.ok) {
                return { success: true };
            } else {
                return {
                    success: false,
                    error: 'logout_error',
                    message: 'Failed to logout on server'
                };
            }
        } catch (error) {
            console.error('Logout error:', error);
            // Clear local auth data even if server request fails
            this.clearAuth();
            return {
                success: false,
                error: 'network_error',
                message: 'Network error during logout'
            };
        }
    }

    /**
     * Get authorization header for API requests
     * @returns {Object} Headers object with Authorization
     */
    getAuthHeaders() {
        const token = this.getToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }

    /**
     * Make authenticated API request
     * @param {string} url - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} API response
     */
    async authenticatedRequest(url, options = {}) {
        const token = this.getToken();
        if (!token) {
            throw new Error('No authentication token available');
        }

        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...options.headers
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            // If token is invalid, clear auth and redirect to login
            if (response.status === 401) {
                this.clearAuth();
                window.location.href = '/login.html';
                throw new Error('Authentication required');
            }

            return response;
        } catch (error) {
            if (error.message === 'Authentication required') {
                throw error;
            }
            throw new Error('Network error occurred');
        }
    }
}

// Create global instance
window.authService = new AuthService();
