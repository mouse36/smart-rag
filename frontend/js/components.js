/**
 * Component loader for SunnyMentor
 * Handles loading shared components across multiple pages
 */

/**
 * Global Language Manager
 * Handles site-wide language persistence using localStorage
 */
class LanguageManager {
    constructor() {
        this.storageKey = 'sunnymentor_language';
        this.defaultLanguage = 'EN';
        this.currentLanguage = this.loadLanguage();
    }

    loadLanguage() {
        try {
            return localStorage.getItem(this.storageKey) || this.defaultLanguage;
        } catch (error) {
            console.warn('localStorage not available, using default language');
            return this.defaultLanguage;
        }
    }

    saveLanguage(language) {
        try {
            localStorage.setItem(this.storageKey, language);
            this.currentLanguage = language;
        } catch (error) {
            console.warn('Could not save language preference to localStorage');
        }
    }

    getCurrentLanguage() {
        return this.currentLanguage;
    }

    toggleLanguage() {
        const newLanguage = this.currentLanguage === 'EN' ? '中文' : 'EN';
        this.saveLanguage(newLanguage);
        return newLanguage;
    }

    updateLanguageDisplay() {
        const languageCodes = document.querySelectorAll('.language-code');
        languageCodes.forEach(code => {
            code.textContent = this.currentLanguage;
        });
    }

    updateLanguageContent() {
        // Update text content elements
        const elements = document.querySelectorAll('[data-en]');
        elements.forEach(el => {
            const englishText = el.getAttribute('data-en');
            const chineseText = el.getAttribute('data-zh');
            
            // Special handling for hero title with spans
            if (el.querySelector('.hero-title-line1, .hero-title-line2')) {
                const text = this.currentLanguage === 'EN' ? englishText : chineseText;
                if (text === 'Your 24/7 Virtual Coach for Selective Mutism Support') {
                    el.innerHTML = '<span class="hero-title-line1">Your 24/7 Virtual Coach</span><span class="hero-title-line2">for Selective Mutism Support</span>';
                } else if (text) {
                    el.innerHTML = '<span class="hero-title-line1">' + text + '</span>';
                }
            } else {
                if (this.currentLanguage === 'EN') {
                    el.textContent = englishText;
                } else if (this.currentLanguage === '中文') {
                    el.textContent = chineseText || englishText;
                }
            }
        });

        // Update placeholders
        const placeholderElements = document.querySelectorAll('[data-placeholder-en]');
        placeholderElements.forEach(el => {
            const englishPlaceholder = el.getAttribute('data-placeholder-en');
            const chinesePlaceholder = el.getAttribute('data-placeholder-zh');
            if (this.currentLanguage === 'EN') {
                el.placeholder = englishPlaceholder;
            } else if (this.currentLanguage === '中文') {
                el.placeholder = chinesePlaceholder || englishPlaceholder;
            }
        });

        // Update title attributes
        const titleElements = document.querySelectorAll('[data-title-en]');
        titleElements.forEach(el => {
            const englishTitle = el.getAttribute('data-title-en');
            const chineseTitle = el.getAttribute('data-title-zh');
            if (this.currentLanguage === 'EN') {
                el.title = englishTitle;
            } else if (this.currentLanguage === '中文') {
                el.title = chineseTitle || englishTitle;
            }
        });
    }

    initializeLanguage() {
        this.updateLanguageDisplay();
        this.updateLanguageContent();
    }
}

// Create global language manager instance
window.languageManager = new LanguageManager();

async function loadComponent(elementId, componentPath) {
    try {
        console.log('Loading component:', componentPath, 'into element:', elementId);
        const response = await fetch(componentPath);
        console.log('Response status:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`Failed to load component: ${response.status} ${response.statusText}`);
        }
        
        const html = await response.text();
        console.log('Component HTML loaded, length:', html.length, 'Content:', html);
        
        let element = document.getElementById(elementId);
        if (!element) {
            // If not found by ID, try to find by class
            element = document.querySelector('.' + elementId);
        }
        
        if (element) {
            console.log('Found element:', elementId, 'Current innerHTML:', element.innerHTML);
            element.innerHTML = html;
            console.log('Component loaded successfully into:', elementId, 'New innerHTML:', element.innerHTML);
            
            // Execute any scripts in the loaded component
            const scripts = element.querySelectorAll('script');
            scripts.forEach(script => {
                if (script.textContent) {
                    console.log('Executing script from component');
                    eval(script.textContent);
                }
            });
            
        } else {
            console.error('Element not found:', elementId);
            console.log('Available elements with similar IDs:');
            document.querySelectorAll('[id*="language"]').forEach(el => {
                console.log('  -', el.id, el.tagName);
            });
            console.log('Available elements with similar classes:');
            document.querySelectorAll('[class*="bottom-bar"]').forEach(el => {
                console.log('  -', el.className, el.tagName);
            });
        }
    } catch (error) {
        console.error('Component loading error:', error);
        // Fallback: create a simple error banner if loading fails
        const element = document.getElementById(elementId);
        if (element && elementId.includes('error-banner')) {
            element.innerHTML = `
                <div class="error-banner" style="background: #e53e3e; color: white; padding: 12px; display: flex; align-items: center; justify-content: space-between;">
                    <div>Error: Component failed to load</div>
                    <button onclick="this.parentElement.style.display='none'" style="background: none; border: none; color: white; cursor: pointer;">×</button>
                </div>
            `;
        }
    }
}

/**
 * Initialize navbar with appropriate content based on page type
 */
function initializeNavbar(pageType = 'landing') {
    const navAuthContent = document.getElementById('nav-auth-content');
    if (!navAuthContent) return;

    let authHTML = '';
    
    switch (pageType) {
        case 'login':
            authHTML = `
                <button class="btn btn-secondary" onclick="goToSignup()">Don't have an account? Sign up</button>
                <div class="language-switcher" onclick="toggleLanguage()" title="Switch Language">
                    <img src="graphics/language-switcher.svg" alt="Language Switcher" class="globe-icon" />
                    <span class="language-code">EN</span>
                </div>
            `;
            break;
            
        case 'signup':
            authHTML = `
                <button class="btn btn-secondary" onclick="goToLogin()">Already have an account? Log in</button>
                <div class="language-switcher" onclick="toggleLanguage()" title="Switch Language">
                    <img src="graphics/language-switcher.svg" alt="Language Switcher" class="globe-icon" />
                    <span class="language-code">EN</span>
                </div>
            `;
            break;
            
        case 'chat':
            authHTML = `
                <button class="btn btn-secondary" onclick="showSettings()">Settings</button>
                <button class="btn btn-secondary" onclick="showLanding()">Logout</button>
                <div class="language-switcher" onclick="toggleLanguage()" title="Switch Language">
                    <img src="graphics/language-switcher.svg" alt="Language Switcher" class="globe-icon" />
                    <span class="language-code">EN</span>
                </div>
            `;
            break;

        case 'donate':
            authHTML = `
                <button class="btn btn-secondary" onclick="showLanding()">Back to Home</button>
                <div class="language-switcher" onclick="toggleLanguage()" title="Switch Language">
                    <img src="graphics/language-switcher.svg" alt="Language Switcher" class="globe-icon" />
                    <span class="language-code">EN</span>
                </div>
            `;
            break;
            
        default: // landing page
            authHTML = `
                <button class="label" data-en="About" data-zh="关于">About</button>
                <button class="label" data-en="FAQ" data-zh="常见问题">FAQ</button>
                <button class="label" data-en="Contact" data-zh="联系我们">Contact</button>
                <button class="btn btn-white" onclick="goToLogin()" data-en="Log In" data-zh="登录">Log In</button>
                <button class="btn btn-primary" onclick="goToSignup()" data-en="Get Full Access" data-zh="获取完整功能">Get Full Access</button>
                <div class="language-switcher" onclick="toggleLanguage()" title="Switch Language">
                    <img src="graphics/language-switcher.svg" alt="Language Switcher" class="globe-icon" />
                    <span class="language-code">EN</span>
                </div>
            `;
            break;
    }
    
    navAuthContent.innerHTML = authHTML;
}

/**
 * Handle logo click - navigate to home page
 */
function handleLogoClick() {
    // For login/signup pages, go to home
    if (window.location.pathname.includes('login.html') || window.location.pathname.includes('signup.html')) {
        window.location.href = 'index.html';
    } else {
        // For main page, scroll to top or show landing
        if (typeof showLanding === 'function') {
            showLanding();
        } else {
            window.scrollTo(0, 0);
        }
    }
}

/**
 * Navigation functions
 */
function goToLogin() {
    window.location.href = 'login.html';
}

function goToSignup() {
    window.location.href = 'signup.html';
}

function goToHome() {
    window.location.href = 'index.html';
}

/**
 * Placeholder functions for pages that don't have them
 */
function showSettings() {
    if (typeof window.showSettings === 'function') {
        window.showSettings();
    } else {
        console.log('Settings function not available on this page');
    }
}

function showLanding() {
    if (typeof window.showLanding === 'function') {
        window.showLanding();
    } else {
        window.location.href = 'index.html';
    }
}

/**
 * Global language switching function
 */
function toggleLanguage() {
    // Use the global language manager
    if (window.languageManager) {
        window.languageManager.toggleLanguage();
        window.languageManager.initializeLanguage();
        
        // Call page-specific language update if it exists
        if (typeof window.updateAllText === 'function') {
            window.updateAllText();
        }
        
        // Call chat-specific language update if it exists
        if (typeof window.updateChatLanguage === 'function') {
            window.updateChatLanguage();
        }
        
        return;
    }
    
    // Fallback for pages without the language manager (should not happen)
    console.warn('Global language manager not available');
}

/**
 * Update language content for basic language switching
 */
function updateLanguageContent(language) {
    const elements = document.querySelectorAll('[data-en]');
    elements.forEach(el => {
        const englishText = el.getAttribute('data-en');
        const chineseText = el.getAttribute('data-zh');
        if (language === 'EN') {
            el.textContent = englishText;
        } else {
            el.textContent = chineseText || englishText;
        }
    });

    // Update placeholders
    const placeholderElements = document.querySelectorAll('[data-placeholder-en]');
    placeholderElements.forEach(el => {
        const englishPlaceholder = el.getAttribute('data-placeholder-en');
        const chinesePlaceholder = el.getAttribute('data-placeholder-zh');
        if (language === 'EN') {
            el.placeholder = englishPlaceholder;
        } else {
            el.placeholder = chinesePlaceholder || englishPlaceholder;
        }
    });
}

/**
 * Load navbar component and initialize based on page
 */
async function setupNavbar(pageType = 'landing', containerId = 'navbar-container') {
    await loadComponent(containerId, 'components/navbar.html');
    // Small delay to ensure DOM is updated
    setTimeout(() => {
        initializeNavbar(pageType);
        // Initialize language after navbar is set up
        if (window.languageManager) {
            window.languageManager.initializeLanguage();
        }
    }, 100);
}

/**
 * Load error banner component
 */
async function loadErrorBanner(containerId = 'error-banner-container') {
    await loadComponent(containerId, 'components/error-banner.html');
}

/**
 * Load error text component
 */
async function loadErrorText(containerId = 'error-text-container') {
    await loadComponent(containerId, 'components/error-text.html');
}

/**
 * Setup error components for a page
 */
async function setupErrorComponents(bannerContainerId = 'error-banner-container', textContainerId = 'error-text-container') {
    await loadErrorBanner(bannerContainerId);
    await loadErrorText(textContainerId);
}

/**
 * Setup error text components for all error containers on a page
 */
async function setupErrorTextComponents() {
    const errorContainers = document.querySelectorAll('[id$="-error-container"]');
    for (const container of errorContainers) {
        await loadComponent(container.id, 'components/error-text.html');
    }
}