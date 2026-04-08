// Main JavaScript file for Placement Portal

const API_BASE_URL = '/api';
axios.defaults.baseURL = API_BASE_URL;

axios.interceptors.request.use(
    (config) => config,
    (error) => Promise.reject(error)
);

axios.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user_role');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

function setAuthToken(token) {
    if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        localStorage.setItem('access_token', token);
    } else {
        delete axios.defaults.headers.common['Authorization'];
        localStorage.removeItem('access_token');
    }
}

function getAuthToken() {
    return localStorage.getItem('access_token');
}

function isLoggedIn() {
    return !!getAuthToken();
}

function getUserRole() {
    return localStorage.getItem('user_role');
}
window.getUserRole = getUserRole;

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_role');
    window.location.href = '/login';
}

function checkAuth() {
    const token = getAuthToken();
    if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    if (typeof updateNav === 'function') {
        updateNav();
    }
});

window.PlacementPortal = {
    API_BASE_URL,
    setAuthToken,
    getAuthToken,
    isLoggedIn,
    getUserRole,
    logout,
    checkAuth,
    axios
};

window.isLoggedIn = window.PlacementPortal.isLoggedIn;
window.logout = window.PlacementPortal.logout;
