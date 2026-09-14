/**
 * Dark Mode 核心功能
 * 实现主题切换、持久化存储和系统主题跟随
 */

const STORAGE_KEY = 'dark-mode-enabled';
const THEME_ATTR = 'data-theme';
const ENABLE_SYSTEM = true;

/**
 * 获取首选主题
 */
function getPreferredTheme() {
    // 1. 优先使用用户保存的偏好
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) {
        return saved === 'dark' ? 'dark' : 'light';
    }

    // 2. 如果启用系统偏好跟随，检测系统设置
    if (ENABLE_SYSTEM && window.matchMedia) {
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
    }

    // 3. 默认主题
    return 'light';
}

/**
 * 应用主题
 */
function applyTheme(theme) {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    if (theme === 'dark') {
        document.documentElement.setAttribute(THEME_ATTR, 'dark');
        document.body.setAttribute(THEME_ATTR, 'dark');
    } else {
        document.documentElement.removeAttribute(THEME_ATTR);
        document.body.removeAttribute(THEME_ATTR);
    }
}

/**
 * 获取当前主题
 */
function getCurrentTheme() {
    return document.documentElement.getAttribute(THEME_ATTR) || 'light';
}

/**
 * 设置主题
 */
function setTheme(theme) {
    const validTheme = theme === 'dark' ? 'dark' : 'light';

    // 应用主题
    applyTheme(validTheme);

    // 保存到localStorage
    localStorage.setItem(STORAGE_KEY, validTheme);

    // 触发自定义事件
    const event = new CustomEvent('themeChanged', {
        detail: { theme: validTheme }
    });
    document.dispatchEvent(event);

    return validTheme;
}

/**
 * 切换主题
 */
function toggleTheme() {
    const current = getCurrentTheme();
    const next = current === 'dark' ? 'light' : 'dark';
    return setTheme(next);
}

/**
 * 初始化（防闪烁）
 * 必须在DOM渲染前执行
 */
function initTheme() {
    const theme = getPreferredTheme();
    applyTheme(theme);
}

/**
 * 设置键盘快捷键
 */
function setupKeyboardShortcut() {
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
            e.preventDefault();
            toggleTheme();
        }
    });
}

/**
 * 监听系统主题变化
 */
function setupSystemThemeListener() {
    if (!ENABLE_SYSTEM || !window.matchMedia) return;

    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const listener = function(e) {
        // 只有在用户未手动设置时才跟随系统
        if (localStorage.getItem(STORAGE_KEY) === null) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    };

    if (darkModeQuery.addEventListener) {
        darkModeQuery.addEventListener('change', listener);
    } else if (darkModeQuery.addListener) {
        darkModeQuery.addListener(listener);
    }
}

/**
 * 初始化Dark Mode
 */
export function initDarkMode() {
    // 设置全局API
    window.DarkMode = {
        getCurrentTheme,
        setTheme,
        toggle: toggleTheme
    };

    // 设置键盘快捷键
    setupKeyboardShortcut();

    // 监听系统主题变化
    setupSystemThemeListener();

    console.log('🌗 Dark Mode initialized');
}

// 立即执行防闪烁初始化（在模块加载时）
initTheme();
