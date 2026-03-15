// API Base URL
const API_URL = '';
let token = localStorage.getItem('token');
let currentUser = null;

// ============================================
// Init
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadProjects();
    loadMyLinks();
});

// ============================================
// Auth Functions
// ============================================
async function checkAuth() {
    const storedToken = localStorage.getItem('token');
    console.log('Stored token:', storedToken ? 'exists (' + storedToken.substring(0, 20) + '...)' : 'none');
    
    if (!storedToken) {
        updateAuthUI(false);
        return;
    }
    
    token = storedToken;

    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            currentUser = await response.json();
            console.log('Current user:', currentUser.username);
            updateAuthUI(true);
        } else {
            logout();
        }
    } catch (error) {
        console.error('Auth check error:', error);
        logout();
    }
}

function updateAuthUI(isAuthenticated) {
    const authButtons = document.getElementById('authButtons');
    const userMenu = document.getElementById('userMenu');
    const projectGroup = document.getElementById('projectGroup');

    if (isAuthenticated) {
        authButtons.style.display = 'none';
        userMenu.style.display = 'flex';
        projectGroup.style.display = 'block';
        document.getElementById('username').textContent = currentUser.username;
    } else {
        authButtons.style.display = 'flex';
        userMenu.style.display = 'none';
        projectGroup.style.display = 'none';
    }
}

async function login(username, password) {
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            const data = await response.json();
            token = data.access_token;
            localStorage.setItem('token', token);
            await checkAuth();
            closeModal('loginModal');
            showToast('Вход выполнен успешно!', 'success');
            loadProjects();
            loadMyLinks();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Ошибка входа', 'error');
        }
    } catch (error) {
        showToast('Ошибка подключения к серверу', 'error');
    }
}

async function register(username, email, password) {
    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });

        if (response.ok) {
            showToast('Регистрация успешна! Теперь войдите.', 'success');
            closeModal('registerModal');
            showLoginModal();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Ошибка регистрации', 'error');
        }
    } catch (error) {
        showToast('Ошибка подключения к серверу', 'error');
    }
}

function logout() {
    token = null;
    currentUser = null;
    localStorage.removeItem('token');
    updateAuthUI(false);
    document.getElementById('linksList').innerHTML = '';
    document.getElementById('projectsList').innerHTML = '';
    showToast('Вы вышли из системы', 'info');
}

// ============================================
// Shorten Link
// ============================================
document.getElementById('shortenForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const originalUrl = document.getElementById('originalUrl').value;
    const customAlias = document.getElementById('customAlias').value;
    const expiresAt = document.getElementById('expiresAt').value;
    const projectId = document.getElementById('projectSelect').value;

    const data = { original_url: originalUrl };
    if (customAlias) data.custom_alias = customAlias;
    if (expiresAt) data.expires_at = expiresAt;
    if (projectId) data.project_id = parseInt(projectId);

    console.log('Token:', token ? 'exists' : 'none');
    
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        console.log('Headers:', headers);

        const response = await fetch(`${API_URL}/links/shorten`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const result = await response.json();
            showResult(result);
            loadMyLinks();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Ошибка создания ссылки', 'error');
        }
    } catch (error) {
        showToast('Ошибка подключения к серверу', 'error');
    }
});

function showResult(link) {
    const resultCard = document.getElementById('resultCard');
    const shortUrlInput = document.getElementById('shortUrlInput');
    const resultOriginalUrl = document.getElementById('resultOriginalUrl');

    const fullShortUrl = `${window.location.origin}/${link.short_code}`;
    shortUrlInput.value = fullShortUrl;
    resultOriginalUrl.textContent = link.original_url;
    resultCard.style.display = 'block';
    resultCard.scrollIntoView({ behavior: 'smooth' });

    // Сохраняем текущий short_code для статистики
    resultCard.dataset.shortCode = link.short_code;
}

function closeResult() {
    document.getElementById('resultCard').style.display = 'none';
}

function copyShortUrl() {
    const input = document.getElementById('shortUrlInput');
    input.select();
    document.execCommand('copy');
    showToast('Ссылка скопирована!', 'success');
}

function openShortLink() {
    const shortCode = document.getElementById('resultCard').dataset.shortCode;
    window.open(`/${shortCode}`, '_blank');
}

function showStats() {
    const shortCode = document.getElementById('resultCard').dataset.shortCode;
    document.getElementById('statsShortCode').value = shortCode;
    loadStats();
    document.getElementById('stats').scrollIntoView({ behavior: 'smooth' });
}

// ============================================
// My Links
// ============================================
async function loadMyLinks() {
    if (!token) {
        document.getElementById('emptyLinks').style.display = 'block';
        document.getElementById('linksList').innerHTML = '';
        document.getElementById('linksList').appendChild(document.getElementById('emptyLinks'));
        return;
    }

    try {
        const response = await fetch(`${API_URL}/links/my`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const links = await response.json();
            renderLinks(links);
        }
    } catch (error) {
        console.error('Load links error:', error);
    }
}

function renderLinks(links) {
    const container = document.getElementById('linksList');

    if (links.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                </svg>
                <p>У вас пока нет ссылок</p>
                <span>Создайте первую ссылку выше</span>
            </div>
        `;
        return;
    }

    container.innerHTML = links.map(link => `
        <div class="link-item">
            <div class="link-info">
                <div class="link-short">
                    <a href="/${link.short_code}" target="_blank">${window.location.origin}/${link.short_code}</a>
                </div>
                <div class="link-original">${link.original_url}</div>
                <div class="link-meta">
                    <span>📊 ${link.access_count} переходов</span>
                    <span>📅 ${formatDate(link.created_at)}</span>
                    ${link.expires_at ? `<span>⏰ Истекает: ${formatDate(link.expires_at)}</span>` : ''}
                </div>
            </div>
            <div class="link-actions">
                <button class="btn btn-outline" onclick="viewLinkStats('${link.short_code}')">
                    Статистика
                </button>
                <button class="btn btn-outline" onclick="deleteLink('${link.short_code}')">
                    Удалить
                </button>
            </div>
        </div>
    `).join('');
}

async function deleteLink(shortCode) {
    if (!confirm('Вы уверены, что хотите удалить эту ссылку?')) return;

    try {
        const response = await fetch(`${API_URL}/links/${shortCode}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            showToast('Ссылка удалена', 'success');
            loadMyLinks();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Ошибка удаления', 'error');
        }
    } catch (error) {
        showToast('Ошибка подключения к серверу', 'error');
    }
}

async function viewLinkStats(shortCode) {
    document.getElementById('statsShortCode').value = shortCode;
    await loadStats();
    document.getElementById('stats').scrollIntoView({ behavior: 'smooth' });
}

// Search functionality
document.getElementById('searchInput').addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    const linkItems = document.querySelectorAll('.link-item');

    linkItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(query) ? 'flex' : 'none';
    });
});

// ============================================
// Stats
// ============================================
async function loadStats() {
    const shortCode = document.getElementById('statsShortCode').value.trim();

    if (!shortCode) {
        showToast('Введите short код ссылки', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/links/${shortCode}/stats`);

        if (response.ok) {
            const stats = await response.json();
            renderStats(stats);
        } else {
            const error = await response.json();
            showToast(error.detail || 'Ссылка не найдена', 'error');
            document.getElementById('statsCard').style.display = 'none';
        }
    } catch (error) {
        showToast('Ошибка подключения к серверу', 'error');
        document.getElementById('statsCard').style.display = 'none';
    }
}

function renderStats(stats) {
    document.getElementById('statAccessCount').textContent = stats.access_count;
    document.getElementById('statCreatedAt').textContent = formatDate(stats.created_at);
    document.getElementById('statLastAccess').textContent = stats.last_accessed_at 
        ? formatDate(stats.last_accessed_at) 
        : '—';
    document.getElementById('statExpires').textContent = stats.expires_at 
        ? formatDate(stats.expires_at) 
        : 'Не ограничено';
    document.getElementById('statsOriginalUrl').textContent = stats.original_url;
    document.getElementById('statsOriginalUrl').href = stats.original_url;
    document.getElementById('statsCard').style.display = 'block';
}

// ============================================
// Projects
// ============================================
async function loadProjects() {
    if (!token) {
        document.getElementById('projectsList').innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                <p>Войдите для управления проектами</p>
            </div>
        `;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/projects`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const projects = await response.json();
            renderProjects(projects);
        }
    } catch (error) {
        console.error('Load projects error:', error);
    }
}

function renderProjects(projects) {
    const container = document.getElementById('projectsList');

    if (projects.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                <p>Нет проектов</p>
            </div>
        `;
        return;
    }

    container.innerHTML = projects.map(project => `
        <div class="project-card">
            <div class="project-name">${project.name}</div>
            <div class="project-description">${project.description || 'Без описания'}</div>
            <div class="project-meta">
                <span>📅 ${formatDate(project.created_at)}</span>
                <span>🔗 ${project.links ? project.links.length : 0} ссылок</span>
            </div>
            ${project.links && project.links.length > 0 ? `
                <div class="project-links">
                    <strong>Ссылки:</strong>
                    <ul>
                        ${project.links.map(link => `
                            <li>
                                <a href="/${link.short_code}" target="_blank">${link.short_code}</a>
                                <span class="link-count">(${link.access_count || 0} переходов)</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
    `).join('');

    // Обновляем select проектов
    const select = document.getElementById('projectSelect');
    select.innerHTML = '<option value="">Без проекта</option>' +
        projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
}

// ============================================
// Modal Functions
// ============================================
function showLoginModal() {
    document.getElementById('loginModal').classList.add('active');
}

function showRegisterModal() {
    document.getElementById('registerModal').classList.add('active');
}

function showProjectModal() {
    if (!token) {
        showToast('Войдите для создания проекта', 'error');
        return;
    }
    document.getElementById('projectModal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function switchModal(fromModal, toModal) {
    closeModal(fromModal);
    setTimeout(() => {
        document.getElementById(toModal).classList.add('active');
    }, 200);
}

function toggleMobileMenu() {
    document.getElementById('navMenu').classList.toggle('active');
}

// ============================================
// Form Submits
// ============================================
document.getElementById('loginForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    login(username, password);
});

document.getElementById('registerForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    register(username, email, password);
});

document.getElementById('projectForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('projectName').value;
    const description = document.getElementById('projectDescription').value;

    try {
        const response = await fetch(`${API_URL}/projects`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name, description })
        });

        if (response.ok) {
            showToast('Проект создан!', 'success');
            closeModal('projectModal');
            document.getElementById('projectForm').reset();
            loadProjects();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Ошибка создания проекта', 'error');
        }
    } catch (error) {
        showToast('Ошибка подключения к серверу', 'error');
    }
});

// ============================================
// Utility Functions
// ============================================
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Close modal on outside click
window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});
