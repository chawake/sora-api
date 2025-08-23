// 全局变量
let adminKey = '';
let keysData = [];
let currentPage = 1;
const keysPerPage = 10;
let statsData = null;
let dashboardRequestsChart = null;
let requestsChart = null;
let keysUsageChart = null;
let systemSettings = {
    proxyHost: '',
    proxyPort: '',
    proxyUser: '',
    proxyPass: ''
};
// token过期时间
let tokenExpiry = null;
// JWT配置
const JWT_EXPIRATION = 3600; // 令牌有效期1小时（秒）
// 导入预览数据
let importPreviewData = [];

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    // 检查是否已登录
    checkAuth();
    
    // 绑定登录表单提交事件
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleLogin();
    });
    
    // 绑定退出登录事件
    document.getElementById('logout-btn').addEventListener('click', (e) => {
        e.preventDefault();
        handleLogout();
    });
    
    // 侧边栏切换
    document.getElementById('sidebarCollapse').addEventListener('click', () => {
        const sidebar = document.getElementById('sidebar');
        const content = document.getElementById('content');
        
        sidebar.classList.toggle('active');
        content.classList.toggle('active');
    });
    
    // 页面切换
    document.querySelectorAll('[data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetPage = link.getAttribute('data-page');
            
            // 验证token是否有效
            if (!isTokenValid()) {
                handleLogout();
                showToast('Session expired. Please log in again', 'warning');
                return;
            }
            
            // 更新导航链接激活状态
            document.querySelectorAll('#sidebar li').forEach(li => li.classList.remove('active'));
            link.closest('li').classList.add('active');
            
            // 更新页面标题
            document.getElementById('current-page-title').textContent = link.textContent.trim();
            
            // 隐藏所有页面，只显示目标页面
            document.querySelectorAll('.content-page').forEach(page => {
                page.classList.remove('active');
                page.style.display = 'none';
            });
            document.getElementById(`${targetPage}-page`).classList.add('active');
            document.getElementById(`${targetPage}-page`).style.display = 'block';
            
            // 加载相应页面的数据
            switch (targetPage) {
                case 'dashboard':
                    loadDashboard();
                    break;
                case 'keys':
                    loadKeys();
                    break;
                case 'stats':
                    loadStats();
                    break;
                case 'settings':
                    loadSettings();
                    break;
            }
        });
    });
    
    // 仪表盘页面的"查看全部"按钮
    document.querySelectorAll('#dashboard-page [data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetPage = link.getAttribute('data-page');
            // 触发相应导航的点击事件
            document.querySelector(`#sidebar a[data-page="${targetPage}"]`).click();
        });
    });
    
    // 添加密钥按钮事件
    document.getElementById('add-key-btn').addEventListener('click', () => {
        // 重置表单
        document.getElementById('key-form').reset();
        document.getElementById('key-id').value = '';
        document.getElementById('keyModalLabel').textContent = 'Add New Key';
        
        // 显示模态框
        const keyModal = new bootstrap.Modal(document.getElementById('keyModal'));
        keyModal.show();
    });
    
    // 保存密钥按钮事件
    document.getElementById('save-key-btn').addEventListener('click', saveKey);
    
    // 测试密钥按钮事件
    document.getElementById('test-key-btn').addEventListener('click', testKey);
    
    // 全选/取消全选
    document.getElementById('select-all').addEventListener('change', (e) => {
        const checkboxes = document.querySelectorAll('#keys-table-body input[type="checkbox"]');
        checkboxes.forEach(checkbox => checkbox.checked = e.target.checked);
    });
    
    // 批量操作事件
    document.querySelectorAll('.batch-action').forEach(action => {
        action.addEventListener('click', (e) => {
            e.preventDefault();
            const actionType = action.getAttribute('data-action');
            const selectedIds = getSelectedKeyIds();
            
            if (selectedIds.length === 0) {
                showToast('Please select at least one key', 'warning');
                return;
            }
            
            // 显示确认对话框
            let message = '';
            if (actionType === 'enable') {
                message = `Are you sure you want to enable the selected ${selectedIds.length} keys?`;
            } else if (actionType === 'disable') {
                message = `Are you sure you want to disable the selected ${selectedIds.length} keys?`;
            } else if (actionType === 'delete') {
                message = `Are you sure you want to delete the selected ${selectedIds.length} keys? This action cannot be undone!`;
            }
            
            showConfirmDialog(message, () => {
                batchOperation(actionType, selectedIds);
            });
        });
    });
    
    // 搜索框事件
    document.getElementById('search-keys').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        if (searchTerm) {
            const filteredKeys = keysData.filter(key => 
                key.name.toLowerCase().includes(searchTerm) || 
                key.key.toLowerCase().includes(searchTerm)
            );
            renderKeysTable(filteredKeys);
        } else {
            renderKeysTable(keysData);
        }
    });
    
    // 管理员密钥显示/隐藏
    document.getElementById('show-admin-key').addEventListener('click', () => {
        const adminKeyInput = document.getElementById('admin-key');
        if (adminKeyInput.type === 'password') {
            adminKeyInput.type = 'text';
            document.getElementById('show-admin-key').innerHTML = '<i class="bi bi-eye-slash"></i>';
        } else {
            adminKeyInput.type = 'password';
            document.getElementById('show-admin-key').innerHTML = '<i class="bi bi-eye"></i>';
        }
    });
    
    // 复制管理员密钥
    document.getElementById('copy-admin-key').addEventListener('click', () => {
        const adminKeyInput = document.getElementById('admin-key');
        adminKeyInput.type = 'text';
        adminKeyInput.select();
        document.execCommand('copy');
        adminKeyInput.type = 'password';
        showToast('Admin key copied to clipboard', 'success');
    });
    
    // 设置表单提交
    document.getElementById('settings-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveSettings();
    });
    
    // 批量导入密钥按钮事件
    document.getElementById('import-keys-btn').addEventListener('click', () => {
        // 重置导入表单和预览
        document.getElementById('keys-text').value = '';
        document.getElementById('keys-file').value = '';
        document.getElementById('auto-enable-keys').checked = true;
        document.getElementById('import-preview').style.display = 'none';
        document.getElementById('confirm-import-btn').disabled = true;
        importPreviewData = [];
        
        // 显示导入模态框
        const importModal = new bootstrap.Modal(document.getElementById('importKeysModal'));
        importModal.show();
    });
    
    // 预览导入按钮事件
    document.getElementById('preview-import-btn').addEventListener('click', previewImport);
    
    // 确认导入按钮事件
    document.getElementById('confirm-import-btn').addEventListener('click', confirmImport);
    
    // 文件选择事件
    document.getElementById('keys-file').addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            const reader = new FileReader();
            
            reader.onload = function(event) {
                document.getElementById('keys-text').value = event.target.result;
            };
            
            reader.readAsText(file);
        }
    });
});

// 检查是否已登录
function checkAuth() {
    const savedAdminKey = localStorage.getItem('adminKey');
    const savedTokenExpiry = localStorage.getItem('tokenExpiry');
    
    if (savedAdminKey && savedTokenExpiry) {
        adminKey = savedAdminKey;
        tokenExpiry = parseInt(savedTokenExpiry);
        
        // 检查token是否已过期
        if (isTokenValid()) {
            showAdminPanel();
            // 初始化其他数据
            displayAdminKey();
            loadDashboard(); // 初始加载仪表盘页面
            
            // 如果token即将过期（小于5分钟），则刷新
            const fiveMinutesInMs = 5 * 60 * 1000;
            if (tokenExpiry - new Date().getTime() < fiveMinutesInMs) {
                refreshToken();
            }
        } else {
            // token已过期，清除存储并显示登录面板
            handleLogout();
            showToast('Session expired. Please log in again', 'warning');
        }
    } else {
        showLoginPanel();
    }
}

// 处理登录
async function handleLogin() {
    const inputKey = document.getElementById('admin-key-input').value.trim();
    if (!inputKey) {
        showLoginError('Please enter the admin key');
        return;
    }
    
    try {
        // 显示加载状态
        document.querySelector('#login-form button').disabled = true;
        document.querySelector('#login-form button').innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Logging in...';
        
        // 使用fetch API进行登录请求
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ admin_key: inputKey })
        });
        
        // 恢复按钮状态
        document.querySelector('#login-form button').disabled = false;
        document.querySelector('#login-form button').innerHTML = 'Log In';
        
        if (response.ok) {
            const data = await response.json();
            adminKey = data.token;
            tokenExpiry = new Date().getTime() + (data.expires_in * 1000);
            
            // 保存至本地存储
            localStorage.setItem('adminKey', adminKey);
            localStorage.setItem('tokenExpiry', tokenExpiry.toString());
            
            // 隐藏错误信息
            document.getElementById('login-error').style.display = 'none';
            
            // 显示管理面板
            showAdminPanel();
            displayAdminKey();
            loadDashboard();
        } else {
            // 登录失败
            try {
                const error = await response.json();
                showLoginError(error.detail || 'Login failed. Please check the admin key');
            } catch {
                showLoginError('Login failed. Please check the admin key');
            }
        }
    } catch (error) {
        // 处理网络错误等异常
        document.querySelector('#login-form button').disabled = false;
        document.querySelector('#login-form button').innerHTML = 'Log In';
        console.error('Failed to validate admin key:', error);
        showLoginError('Validation failed. Please try again later');
    }
}

// 显示登录错误
function showLoginError(message) {
    const errorElement = document.getElementById('login-error');
    errorElement.textContent = message;
    errorElement.style.display = 'block';
    
    // 3秒后自动隐藏
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 3000);
}

// 处理登出
function handleLogout() {
    localStorage.removeItem('adminKey');
    localStorage.removeItem('tokenExpiry');
    adminKey = '';
    tokenExpiry = null;
    showLoginPanel();
    document.getElementById('admin-key-input').value = '';
}

// 检查token是否有效
function isTokenValid() {
    if (!tokenExpiry) return false;
    // 检查token是否过期（留10秒缓冲）
    return new Date().getTime() < tokenExpiry - 10000;
}

// 刷新token
async function refreshToken() {
    try {
        const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminKey}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            adminKey = data.token;
            tokenExpiry = new Date().getTime() + (data.expires_in * 1000);
            localStorage.setItem('adminKey', adminKey);
            localStorage.setItem('tokenExpiry', tokenExpiry.toString());
            return true;
        } else {
            return false;
        }
    } catch (error) {
        console.error('Failed to refresh token:', error);
        return false;
    }
}

// 显示登录面板
function showLoginPanel() {
    document.getElementById('login-container').style.display = 'flex';
    document.getElementById('admin-panel').style.display = 'none';
    // 清除可能存在的错误信息
    document.getElementById('login-error').style.display = 'none';
}

// 显示管理面板
function showAdminPanel() {
    document.getElementById('login-container').style.display = 'none';
    document.getElementById('admin-panel').style.display = 'flex';
    
    // 确保侧边栏正常显示
    document.getElementById('sidebar').classList.remove('active');
    document.getElementById('content').classList.remove('active');
    
    // 初始化显示仪表盘页面，隐藏其他页面
    document.querySelectorAll('.content-page').forEach(page => {
        page.classList.remove('active');
        page.style.display = 'none';
    });
    document.getElementById('dashboard-page').classList.add('active');
    document.getElementById('dashboard-page').style.display = 'block';
    
    // 更新导航栏状态
    document.querySelectorAll('#sidebar li').forEach(li => li.classList.remove('active'));
    document.querySelector('#sidebar li:first-child').classList.add('active');
    
    // 更新页面标题
    document.getElementById('current-page-title').textContent = 'Dashboard';
}

// 显示管理员密钥信息
function displayAdminKey() {
    // 设置到隐藏输入框
    document.getElementById('admin-key').value = adminKey;
    
    // 显示密钥部分信息
    const keyDisplay = adminKey.substring(0, 6) + '...' + adminKey.substring(adminKey.length - 4);
    document.getElementById('admin-key-display').textContent = 'Admin: ' + keyDisplay;
}

// API请求包装函数，处理token刷新逻辑
async function apiRequest(url, options = {}) {
    // 检查token是否即将到期（剩余5分钟以内）
    const fiveMinutesInMs = 5 * 60 * 1000;
    if (tokenExpiry && (tokenExpiry - new Date().getTime() < fiveMinutesInMs)) {
        // 刷新token
        const refreshSuccess = await refreshToken();
        if (!refreshSuccess) {
            // token刷新失败，需要重新登录
            handleLogout();
            showToast('Session expired. Please log in again', 'warning');
            return null;
        }
    }
    
    // 确保options中包含正确的headers
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Bearer ${adminKey}`;
    
    // 如果是POST/PUT请求且有body，确保设置正确的Content-Type
    if ((options.method === 'POST' || options.method === 'PUT') && options.body) {
        // 确保Content-Type正确设置
        if (!options.headers['Content-Type']) {
            options.headers['Content-Type'] = 'application/json';
        }
    }
    
    // 发送请求
    try {
        const response = await fetch(url, options);
        
        // 处理401/403错误（未授权）
        if (response.status === 401 || response.status === 403) {
            // 尝试刷新token
            if (await refreshToken()) {
                // 刷新成功，使用新token重试请求
                options.headers['Authorization'] = `Bearer ${adminKey}`;
                const retryResponse = await fetch(url, options);
                if (retryResponse.ok) {
                    return await retryResponse.json();
                }
            }
            
            // 刷新失败或重试失败，需要重新登录
            handleLogout();
            showToast('Session expired. Please log in again', 'warning');
            return null;
        }
        
        // 其他错误
        if (!response.ok) {
            // 尝试解析错误消息
            try {
                const errorData = await response.json();
                throw new Error(`Request failed: ${response.status} - ${errorData.detail || errorData.message || response.statusText}`);
            } catch (e) {
                throw new Error(`Request failed: ${response.status} ${response.statusText}`);
            }
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request error:', error);
        showToast(`Request failed: ${error.message}`, 'error');
        return null;
    }
}

// 加载密钥列表
async function loadKeys() {
    try {
        // 显示加载中
        document.getElementById('keys-table-body').innerHTML = '<tr><td colspan="9" class="text-center">Loading...</td></tr>';
        
        const data = await apiRequest('/api/keys');
        if (data) {
            keysData = data;
            renderKeysTable(keysData);
        }
    } catch (error) {
        console.error('Failed to load keys:', error);
        document.getElementById('keys-table-body').innerHTML = 
            `<tr><td colspan="9" class="text-center text-danger">Load failed: ${error.message}</td></tr>`;
    }
}

// 渲染密钥表格
function renderKeysTable(keys) {
    const tableBody = document.getElementById('keys-table-body');
    tableBody.innerHTML = '';
    
    if (keys.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="9" class="text-center">No key data</td></tr>';
        return;
    }
    
    // 分页处理
    const startIndex = (currentPage - 1) * keysPerPage;
    const endIndex = startIndex + keysPerPage;
    const keysToShow = keys.slice(startIndex, endIndex);
    
    // 渲染表格行
    keysToShow.forEach(key => {
        const row = document.createElement('tr');
        
        // 创建时间和最后使用时间格式化
        const createDate = key.created_at ? new Date(key.created_at * 1000).toLocaleString() : 'Unknown';
        const lastUsedDate = key.last_used ? new Date(key.last_used * 1000).toLocaleString() : 'Never used';
        
        // 确定密钥状态
        let statusText = '';
        let statusClass = '';
        let statusTitle = '';
        let remainingTimeText = '';
        
        if (key.temp_disabled_until) {
            // 临时禁用 - 使用格式化后的时间
            statusText = 'Temporarily Disabled';
            statusClass = 'status-temp-disabled';
            
            // 优先使用服务器返回的格式化时间
            const enableTimeText = key.temp_disabled_until_formatted || 
                                  new Date(key.temp_disabled_until * 1000).toLocaleString();
            
            statusTitle = `Will be re-enabled at ${enableTimeText}`;
            
            // 如果有剩余时间信息，添加可读性更强的显示
            if (key.temp_disabled_remaining !== undefined) {
                const remainingSecs = key.temp_disabled_remaining;
                if (remainingSecs > 0) {
                    // 转换为 小时:分钟:秒 格式
                    const hours = Math.floor(remainingSecs / 3600);
                    const minutes = Math.floor((remainingSecs % 3600) / 60);
                    const seconds = remainingSecs % 60;
                    
                    remainingTimeText = `Remaining ${hours}h ${minutes}m`;
                } else {
                    remainingTimeText = 'Resuming soon';
                }
            }
        } else if (key.is_enabled) {
            // 启用
            statusText = 'Enabled';
            statusClass = 'status-enabled';
        } else {
            // 永久禁用
            statusText = 'Disabled';
            statusClass = 'status-disabled';
        }
        
        row.innerHTML = `
            <td><input type="checkbox" name="key-checkbox" class="key-checkbox" value="${key.id}" data-id="${key.id}"></td>
            <td>${key.name || 'Unnamed'}</td>
            <td class="key-value">${key.key}</td>
            <td>
                <span class="status-badge ${statusClass}" title="${statusTitle}">
                    ${statusText}
                </span>
                ${key.temp_disabled_until ? 
                    `<div class="small text-muted">
                        Will be enabled at: ${key.temp_disabled_until_formatted || new Date(key.temp_disabled_until * 1000).toLocaleString()}
                        ${remainingTimeText ? `<br>${remainingTimeText}` : ''}
                    </div>` : ''}
            </td>
            <td>${key.weight || 1}</td>
            <td>${key.max_rpm || 60}/min</td>
            <td>${createDate}</td>
            <td>${lastUsedDate}</td>
            <td>
                <button class="btn btn-sm btn-primary action-btn edit-key" data-id="${key.id}" title="Edit">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-danger action-btn delete-key" data-id="${key.id}" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
                <button class="btn btn-sm btn-secondary action-btn copy-key" data-key="${key.key}" title="Copy Key">
                    <i class="bi bi-clipboard"></i>
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // 绑定操作按钮事件
    bindTableEvents();
    
    // 更新分页
    renderPagination(keys.length);
}

// 绑定表格操作事件
function bindTableEvents() {
    // 编辑按钮
    document.querySelectorAll('.edit-key').forEach(btn => {
        btn.addEventListener('click', async () => {
            const keyId = btn.getAttribute('data-id');
            await loadKeyDetails(keyId);
            
            // 显示模态框
            document.getElementById('keyModalLabel').textContent = 'Edit Key';
            const keyModal = new bootstrap.Modal(document.getElementById('keyModal'));
            keyModal.show();
        });
    });
    
    // 删除按钮
    document.querySelectorAll('.delete-key').forEach(btn => {
        btn.addEventListener('click', () => {
            const keyId = btn.getAttribute('data-id');
            const keyName = btn.closest('tr').children[1].textContent;
            
            showConfirmDialog(`Are you sure you want to delete the key "${keyName}"? This action cannot be undone!`, () => {
                deleteKey(keyId);
            });
        });
    });
    
    // 复制按钮
    document.querySelectorAll('.copy-key').forEach(btn => {
        btn.addEventListener('click', () => {
            const keyValue = btn.getAttribute('data-key');
            navigator.clipboard.writeText(keyValue)
                .then(() => showToast('Key copied to clipboard', 'success'))
                .catch(err => showToast('Copy failed: ' + err, 'error'));
        });
    });
}

// 渲染分页
function renderPagination(totalKeys) {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    if (totalKeys <= keysPerPage) {
        return;
    }
    
    const totalPages = Math.ceil(totalKeys / keysPerPage);
    const ul = document.createElement('ul');
    ul.className = 'pagination';
    
    // 上一页
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage - 1}">Previous</a>`;
    ul.appendChild(prevLi);
    
    // 页码
    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${currentPage === i ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
        ul.appendChild(li);
    }
    
    // 下一页
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage + 1}">Next</a>`;
    ul.appendChild(nextLi);
    
    pagination.appendChild(ul);
    
    // 绑定页码点击事件
    document.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            if (link.parentElement.classList.contains('disabled')) {
                return;
            }
            currentPage = parseInt(link.getAttribute('data-page'));
            renderKeysTable(keysData);
        });
    });
}

// 加载单个密钥详情
async function loadKeyDetails(keyId) {
    try {
        const keyData = await apiRequest(`/api/keys/${keyId}`);
        if (!keyData) return;
        
        // 填充表单
        document.getElementById('key-id').value = keyData.id;
        document.getElementById('key-name').value = keyData.name || '';
        document.getElementById('key-value').value = keyData.key || '';
        document.getElementById('key-weight').value = keyData.weight || 1;
        document.getElementById('key-rate-limit').value = keyData.max_rpm || 60;
        document.getElementById('key-enabled').checked = keyData.is_enabled;
        document.getElementById('key-notes').value = keyData.notes || '';
    } catch (error) {
        console.error('Failed to load key details:', error);
        showToast('Failed to load key details: ' + error.message, 'error');
    }
}

// 保存密钥
async function saveKey() {
    try {
        const keyId = document.getElementById('key-id').value;
        const keyData = {
            name: document.getElementById('key-name').value,
            key_value: document.getElementById('key-value').value,
            weight: parseInt(document.getElementById('key-weight').value),
            rate_limit: parseInt(document.getElementById('key-rate-limit').value),
            is_enabled: document.getElementById('key-enabled').checked,
            notes: document.getElementById('key-notes').value
        };
        
        if (!keyData.name || !keyData.key_value) {
            showToast('Key name and value cannot be empty', 'warning');
            return;
        }
        
        let url, method;
        
        if (keyId) {
            // 更新现有密钥
            url = `/api/keys/${keyId}`;
            method = 'PUT';
        } else {
            // 创建新密钥
            url = '/api/keys';
            method = 'POST';
        }
        
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(keyData)
        };
        
        const result = await apiRequest(url, options);
        if (!result) return;
        
        // 关闭模态框
        const keyModal = bootstrap.Modal.getInstance(document.getElementById('keyModal'));
        keyModal.hide();
        
        // 重新加载密钥列表
        await loadKeys();
        
        // 如果是仪表盘页面，也更新仪表盘数据
        if (document.getElementById('dashboard-page').classList.contains('active')) {
            await loadDashboard();
        }
        
        // 显示成功消息
        showToast(keyId ? 'Key updated successfully' : 'Key added successfully', 'success');
    } catch (error) {
        console.error('Failed to save key:', error);
        showToast('Failed to save key: ' + error.message, 'error');
    }
}

// 测试密钥连接
async function testKey() {
    try {
        const keyValue = document.getElementById('key-value').value;
        
        if (!keyValue) {
            showToast('Please enter a valid key value', 'warning');
            return;
        }
        
        const keyName = document.getElementById('key-name').value || 'New Key';
        
        // 显示测试中状态
        const testButton = document.getElementById('test-key-btn');
        const originalText = testButton.innerHTML;
        testButton.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Testing...';
        testButton.disabled = true;
        
        const testData = {
            name: keyName,
            key_value: keyValue
        };
        
        const result = await apiRequest('/api/keys/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(testData)
        });
        
        // 恢复按钮状态
        testButton.innerHTML = originalText;
        testButton.disabled = false;
        
        if (!result) return;
        
        if (result.status === "success") {
            showToast(`Test successful: ${result.message || 'Key is valid'}`, 'success');
        } else {
            showToast(`Test failed: ${result.message || 'Key cannot connect'}`, 'warning');
        }
    } catch (error) {
        console.error('Failed to test key:', error);
        showToast('Failed to test key: ' + error.message, 'error');
        
        // 恢复按钮状态
        const testButton = document.getElementById('test-key-btn');
        testButton.innerHTML = '<i class="bi bi-shield-check me-1"></i> Test Connection';
        testButton.disabled = false;
    }
}

// 删除密钥
async function deleteKey(keyId) {
    try {
        const result = await apiRequest(`/api/keys/${keyId}`, {
            method: 'DELETE'
        });
        
        if (!result) return;
        
        // 重新加载密钥列表
        await loadKeys();
        
        // 如果是仪表盘页面，也更新仪表盘数据
        if (document.getElementById('dashboard-page').classList.contains('active')) {
            await loadDashboard();
        }
        
        // 显示成功消息
        showToast('Key deleted successfully', 'success');
    } catch (error) {
        console.error('Failed to delete key:', error);
        showToast('Failed to delete key: ' + error.message, 'error');
    }
}

// 批量操作
async function batchOperation(action, keyIds) {
    try {
        const operationData = {
            action: action,
            key_ids: keyIds
        };
        
        const result = await apiRequest('/api/keys/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(operationData)
        });
        
        if (!result) return;
        
        // 重新加载密钥列表
        await loadKeys();
        
        // 如果是仪表盘页面，也更新仪表盘数据
        if (document.getElementById('dashboard-page').classList.contains('active')) {
            await loadDashboard();
        }
        
        // 显示成功消息
        let message = '';
        if (action === 'enable') {
            message = 'Batch enable successful';
        } else if (action === 'disable') {
            message = 'Batch disable successful';
        } else if (action === 'delete') {
            message = 'Batch delete successful';
        }
        
        showToast(message, 'success');
    } catch (error) {
        console.error('Batch operation failed:', error);
        showToast('Batch operation failed: ' + error.message, 'error');
    }
}

// 获取所有选中的密钥ID
function getSelectedKeyIds() {
    const checkboxes = document.querySelectorAll('#keys-table-body input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(checkbox => checkbox.getAttribute('data-id'));
}

// 加载统计数据
async function loadStats() {
    try {
        // 显示加载中状态
        document.getElementById('total-requests').textContent = 'Loading...';
        document.getElementById('successful-requests').textContent = 'Loading...';
        document.getElementById('failed-requests').textContent = 'Loading...';
        document.getElementById('success-rate').textContent = 'Loading...';
        
        const data = await apiRequest('/api/stats');
        if (data) {
            statsData = data;
            
            // 渲染统计卡片
            renderStats();
            
            // 渲染图表
            renderRequestsChart(statsData.daily_usage);
            renderKeysUsageChart(statsData.keys_usage);
        }
    } catch (error) {
        console.error('Failed to load statistics:', error);
        
        // 创建模拟数据
        statsData = {
            total_requests: Math.floor(Math.random() * 5000) + 1000,
            successful_requests: Math.floor(Math.random() * 4000) + 800,
            daily_usage: generateMockDailyUsage(),
            keys_usage: generateMockKeysUsage()
        };
        
        // 渲染模拟数据
        renderStats();
        renderRequestsChart(statsData.daily_usage);
        renderKeysUsageChart(statsData.keys_usage);
    }
}

// 渲染统计卡片
function renderStats() {
    if (!statsData) {
        // 如果没有统计数据，使用默认值
        statsData = {
            total_requests: 0,
            successful_requests: 0
        };
    }
    
    const totalRequests = statsData.total_requests || 0;
    const successfulRequests = statsData.successful_requests || 0;
    const failedRequests = totalRequests - successfulRequests;
    const successRate = totalRequests > 0 ? ((successfulRequests / totalRequests) * 100).toFixed(1) + '%' : '0%';
    
    // 更新统计卡片
    document.getElementById('total-requests').textContent = totalRequests;
    document.getElementById('successful-requests').textContent = successfulRequests;
    document.getElementById('failed-requests').textContent = failedRequests;
    document.getElementById('success-rate').textContent = successRate;
}

// 渲染请求趋势图
function renderRequestsChart(dailyUsage) {
    // 准备数据
    const dates = Object.keys(dailyUsage || {}).sort();
    const lastDates = dates.slice(-30); // 最近30天
    
    const chartData = {
        labels: lastDates.map(date => date.substring(5)), // 只显示月-日
        datasets: [{
            label: 'Requests',
            data: lastDates.map(date => dailyUsage[date] || 0),
            backgroundColor: 'rgba(13, 110, 253, 0.4)',
            borderColor: 'rgba(13, 110, 253, 1)',
            borderWidth: 2
        }]
    };
    
    // 销毁现有图表
    if (requestsChart) {
        requestsChart.destroy();
    }
    
    // 创建新图表
    const ctx = document.getElementById('requests-chart').getContext('2d');
    requestsChart = new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// 渲染密钥使用分布图
function renderKeysUsageChart(keysUsage) {
    // 准备数据
    const keys = Object.keys(keysUsage || {});
    const values = keys.map(key => keysUsage[key]);
    
    // 只显示前8个密钥，其余归为"其他"
    let displayKeys = keys;
    let displayValues = values;
    
    if (keys.length > 8) {
        displayKeys = keys.slice(0, 7);
        displayValues = values.slice(0, 7);
        
        // 计算"其他"的总和
        const othersSum = values.slice(7).reduce((sum, value) => sum + value, 0);
        displayKeys.push('Others');
        displayValues.push(othersSum);
    }
    
    // 生成颜色
    const backgroundColors = [
        'rgba(13, 110, 253, 0.7)',   // 主蓝色
        'rgba(220, 53, 69, 0.7)',    // 红色
        'rgba(25, 135, 84, 0.7)',    // 绿色
        'rgba(255, 193, 7, 0.7)',    // 黄色
        'rgba(111, 66, 193, 0.7)',   // 紫色
        'rgba(23, 162, 184, 0.7)',   // 青色
        'rgba(102, 16, 242, 0.7)',   // 靛蓝色
        'rgba(108, 117, 125, 0.7)'   // 灰色
    ];
    
    const chartData = {
        labels: displayKeys,
        datasets: [{
            data: displayValues,
            backgroundColor: backgroundColors,
            borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
            borderWidth: 1
        }]
    };
    
    // 销毁现有图表
    if (keysUsageChart) {
        keysUsageChart.destroy();
    }
    
    // 创建新图表
    const ctx = document.getElementById('keys-usage-chart').getContext('2d');
    keysUsageChart = new Chart(ctx, {
        type: 'pie',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// 加载系统设置
async function loadSettings() {
    try {
        const data = await apiRequest('/api/config');
        if (!data) return;
        
            // 设置现有的代理设置
            document.getElementById('proxy-host').value = data.PROXY_HOST || '';
            document.getElementById('proxy-port').value = data.PROXY_PORT || '';
            document.getElementById('proxy-user').value = data.PROXY_USER || '';
            document.getElementById('proxy-pass').value = '';
            
            // 设置基础URL
            document.getElementById('base-url').value = data.BASE_URL || '';
            
            // 设置图片本地化配置
            document.getElementById('image-localization').checked = data.IMAGE_LOCALIZATION || false;
            document.getElementById('image-save-dir').value = data.IMAGE_SAVE_DIR || 'src/static/images';
    } catch (error) {
        console.error('Failed to load settings:', error);
        showToast('Failed to get settings: ' + error.message, 'error');
    }
}

// 保存系统设置
async function saveSettings() {
    try {
        // 获取表单数据
        const config = {
            PROXY_HOST: document.getElementById('proxy-host').value,
            PROXY_PORT: document.getElementById('proxy-port').value,
            PROXY_USER: document.getElementById('proxy-user').value,
            PROXY_PASS: document.getElementById('proxy-pass').value,
            BASE_URL: document.getElementById('base-url').value,
            IMAGE_LOCALIZATION: document.getElementById('image-localization').checked,
            IMAGE_SAVE_DIR: document.getElementById('image-save-dir').value || 'src/static/images',
            save_to_env: true
        };
        
        // 调用API保存到服务器
        const result = await apiRequest('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (!result) return;
        
        showToast('Settings saved', 'success');
    } catch (error) {
        console.error('Failed to save settings:', error);
        showToast('Failed to save settings: ' + error.message, 'error');
    }
}

// 显示确认对话框
function showConfirmDialog(message, callback) {
    document.getElementById('confirm-message').textContent = message;
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    
    // 确认按钮事件
    document.getElementById('confirm-btn').onclick = () => {
        confirmModal.hide();
        if (typeof callback === 'function') {
            callback();
        }
    };
    
    confirmModal.show();
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 创建Toast元素
    const toastId = 'toast-' + Date.now();
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type}`;
    toastEl.id = toastId;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // 添加到容器
    document.getElementById('toast-container').appendChild(toastEl);
    
    // 显示Toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 3000
    });
    toast.show();
    
    // 监听隐藏事件，删除元素
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}

// 加载仪表盘数据
async function loadDashboard() {
    try {
        // 先加载密钥统计
        await loadKeyStats();
        
        // 再加载使用统计
        await loadUsageStats();
        
        // 加载最近的密钥
        await loadRecentKeys();
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        showToast('Failed to load dashboard data', 'error');
    }
}

// 加载密钥统计
async function loadKeyStats() {
    try {
        const data = await apiRequest('/api/keys');
        if (!data) return;
        
            keysData = data;
            
            // 计算统计数据
            const totalKeys = keysData.length;
            const activeKeys = keysData.filter(key => key.is_enabled).length;
            const disabledKeys = totalKeys - activeKeys;
            
            // 更新统计卡片
            document.getElementById('total-keys').textContent = totalKeys;
            document.getElementById('active-keys').textContent = activeKeys;
            document.getElementById('disabled-keys').textContent = disabledKeys;
    } catch (error) {
        console.error('Failed to load key stats:', error);
    }
}

// 加载使用统计
async function loadUsageStats() {
    try {
        const data = await apiRequest('/api/stats');
        if (!data) return;
        
        // 更新仪表盘统计数据
        const totalRequests = data.total_requests || 0;
        const successfulRequests = data.successful_requests || 0;
        const failedRequests = data.failed_requests || 0;
        
        // 更新统计卡片
        document.getElementById('total-requests').textContent = totalRequests;
        document.getElementById('successful-requests').textContent = successfulRequests;
        document.getElementById('failed-requests').textContent = failedRequests;
        
        // 计算成功率
        const successRate = totalRequests > 0 ? Math.round((successfulRequests / totalRequests) * 100) : 0;
        document.getElementById('success-rate').textContent = `${successRate}%`;
        
        // 获取今日使用量
        const today = new Date().toISOString().split('T')[0];
        const todayRequests = (data.daily_usage && data.daily_usage[today]) || 0;
        document.getElementById('today-requests').textContent = todayRequests;
        
        // 设置图表数据
        statsData = data;
        
        // 更新图表
        renderDashboardRequestsChart(data.daily_usage || {});
        
        // 渲染请求趋势图和密钥使用分布图
        renderRequestsChart(data.daily_usage || {});
        renderKeysUsageChart(data.keys_usage || {});
        
        console.log("Chart data updated:", {
            daily_usage: data.daily_usage,
            keys_usage: data.keys_usage
        });
    } catch (error) {
        console.error('Failed to load key stats:', error);
    }
}

// 加载最近的密钥
async function loadRecentKeys() {
    try {
        if (!keysData || keysData.length === 0) {
            const data = await apiRequest('/api/keys');
            if (!data) return;
                keysData = data;
            }
        
        // 按创建时间排序，获取最近的5个
        const recentKeys = [...keysData]
            .sort((a, b) => (b.created_at || 0) - (a.created_at || 0))
            .slice(0, 5);
            
        const recentKeysList = document.getElementById('recent-keys-list');
        recentKeysList.innerHTML = '';
        
        if (recentKeys.length === 0) {
            recentKeysList.innerHTML = '<div class="list-group-item text-center text-muted">No key data</div>';
            return;
        }
        
        recentKeys.forEach(key => {
            const createDate = key.created_at ? new Date(key.created_at * 1000).toLocaleDateString() : 'Unknown';
            const li = document.createElement('a');
            li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
            li.href = '#';
            li.innerHTML = `
                <div>
                    <strong>${key.name || 'Unnamed'}</strong>
                    <div class="text-muted small">${key.key.substring(0, 10)}...</div>
                </div>
                <div>
                    <span class="badge ${key.is_enabled ? 'bg-success' : 'bg-danger'} rounded-pill">
                        ${key.is_enabled ? 'Enabled' : 'Disabled'}
                    </span>
                    <small class="text-muted ms-2">${createDate}</small>
                </div>
            `;
            recentKeysList.appendChild(li);
            
            // 点击跳转到密钥管理页面
            li.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelector('#sidebar a[data-page="keys"]').click();
            });
        });
    } catch (error) {
        console.error('Failed to load recent keys:', error);
    }
}

// 渲染仪表盘请求趋势图
function renderDashboardRequestsChart(dailyUsage) {
    // 获取最近7天的日期
    const dates = [];
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(now.getDate() - i);
        dates.push(date.toISOString().split('T')[0]);
    }
    
    // 准备图表数据
    const chartData = {
        labels: dates.map(date => date.substring(5)), // 只显示月-日
        datasets: [{
            label: 'Daily requests',
            data: dates.map(date => (dailyUsage && dailyUsage[date]) || 0),
            borderColor: '#0d6efd',
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.3
        }]
    };
    
    // 销毁现有图表
    if (dashboardRequestsChart) {
        dashboardRequestsChart.destroy();
}

    // 创建新图表
    const ctx = document.getElementById('dashboard-requests-chart').getContext('2d');
    dashboardRequestsChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// 批量导入密钥预览
async function previewImport() {
    const keysText = document.getElementById('keys-text').value.trim();
    
    if (!keysText) {
        showToast('Please enter or upload key data', 'warning');
        return;
    }
    
    try {
        // 解析密钥数据
        const lines = keysText.split('\n').filter(line => line.trim());
        importPreviewData = [];
        
        console.log(`Starting to process ${lines.length} lines`);
        
        for (let i = 0; i < lines.length; i++) {
            try {
                const line = lines[i];
                // 安全获取子字符串
                const safeSubstring = (str, start, end) => {
                    if (!str) return '';
                    return str.substring(start, Math.min(end, str.length));
                };
                
                console.log(`Processing line ${i+1}: ${safeSubstring(line, 0, 10)}...`);
                
                // 检查是否是单行密钥格式（不包含逗号）
                if (!line.includes(',')) {
                    const keyValue = line.trim();
                    console.log(`  Single-line format, key value: ${safeSubstring(keyValue, 0, 5)}...`);
                    
                    // 几乎不做验证 - 只要不是空字符串或太短就接受
                    if (!keyValue || keyValue.length < 5) {
                        console.log(`  Key too short, skipping`);
                        continue; // 跳过太短的密钥
                    }
                    
                    // 为密钥自动生成名称（使用前5位）
                    const keyName = `Key_${safeSubstring(keyValue, 0, 5)}`;
                    
                    importPreviewData.push({
                        name: keyName,
                        key: keyValue,
                        weight: 1,
                        rate_limit: 60,
                        enabled: document.getElementById('auto-enable-keys').checked
                    });
                    console.log(`  Added to preview, now total ${importPreviewData.length}`);
                    continue;
                }
                
                // 处理标准格式（带逗号分隔）
                const parts = line.split(',').map(part => part.trim());
                console.log(`  Standard format, split into ${parts.length} parts`);
                
                if (parts.length < 2) {
                    console.log(`  Less than 2 parts, skipping`);
                    continue; // 跳过格式不正确的行
                }
                
                const keyName = parts[0] || `Key_Untitled_${i+1}`;
                const keyValue = parts[1] || '';
                const weight = parts.length > 2 ? parseInt(parts[2]) || 1 : 1;
                const rateLimit = parts.length > 3 ? parseInt(parts[3]) || 60 : 60;
                
                console.log(`  Name: ${keyName}, Key: ${safeSubstring(keyValue, 0, 5)}..., Weight: ${weight}, Rate: ${rateLimit}`);
                
                // 几乎不做验证 - 只要不是空字符串或太短就接受
                if (!keyValue || keyValue.length < 5) {
                    console.log(`  Key too short, skipping`);
                    continue; // 跳过太短的密钥
                }
                
                importPreviewData.push({
                    name: keyName,
                    key: keyValue,
                    weight: weight,
                    rate_limit: rateLimit,
                    enabled: document.getElementById('auto-enable-keys').checked
                });
                console.log(`  Added to preview, now total ${importPreviewData.length}`);
            } catch (lineError) {
                console.error(`Error processing line ${i+1}:`, lineError);
                // 继续处理下一行
                continue;
            }
        }
        
        console.log(`Processing complete, ${importPreviewData.length} valid keys`);
        
        // 显示预览
        if (importPreviewData.length > 0) {
            renderImportPreview();
            document.getElementById('preview-count').textContent = importPreviewData.length;
            document.getElementById('import-preview').style.display = 'block';
            document.getElementById('confirm-import-btn').disabled = false;
            console.log('Preview rendered, enabling import button');
        } else {
            showToast('No valid key data found', 'warning');
            document.getElementById('import-preview').style.display = 'none';
            document.getElementById('confirm-import-btn').disabled = true;
            console.log('No valid keys found, disabling import button');
        }
    } catch (error) {
        console.error('Failed to preview import:', error);
        showToast('Preview failed: ' + error.message, 'danger');
    }
}

// 渲染导入预览表格
function renderImportPreview() {
    const tableBody = document.getElementById('preview-table-body');
    tableBody.innerHTML = '';
    
    // 限制预览最多显示10行
    const displayData = importPreviewData.slice(0, 10);
    
    displayData.forEach(key => {
        const row = document.createElement('tr');
        
        // 名称
        const nameCell = document.createElement('td');
        nameCell.textContent = key.name;
        row.appendChild(nameCell);
        
        // 密钥(部分隐藏)
        const keyCell = document.createElement('td');
        const maskedKey = key.key.substring(0, 5) + '...' + key.key.substring(key.key.length - 4);
        keyCell.textContent = maskedKey;
        row.appendChild(keyCell);
        
        // 权重
        const weightCell = document.createElement('td');
        weightCell.textContent = key.weight;
        row.appendChild(weightCell);
        
        // 速率限制
        const rateLimitCell = document.createElement('td');
        rateLimitCell.textContent = key.rate_limit;
        row.appendChild(rateLimitCell);
        
        tableBody.appendChild(row);
    });
    
    // 如果有更多未显示的行
    if (importPreviewData.length > 10) {
        const moreRow = document.createElement('tr');
        const moreCell = document.createElement('td');
        moreCell.colSpan = 4;
        moreCell.textContent = `... ${importPreviewData.length - 10} more keys not shown in preview`;
        moreCell.className = 'text-center text-muted';
        moreRow.appendChild(moreCell);
        tableBody.appendChild(moreRow);
    }
}

// 确认导入密钥
async function confirmImport() {
    if (importPreviewData.length === 0) {
        showToast('No keys to import', 'warning');
        return;
    }
    
    try {
        // 显示加载状态
        const importBtn = document.getElementById('confirm-import-btn');
        const originalText = importBtn.textContent;
        importBtn.disabled = true;
        importBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Importing...';
        
        console.log('Preparing to send batch import request, data preview:', importPreviewData.slice(0, 2));
        
        // 简化数据处理
        const requestData = {
            action: "import",
            keys: []
        };
        
        // 手动将每个importPreviewData项转换为普通对象
        for (const item of importPreviewData) {
            requestData.keys.push({
                name: item.name || "",
                key: item.key || "",
                weight: item.weight || 1,
                rate_limit: item.rate_limit || 60,
                enabled: item.enabled !== undefined ? item.enabled : true
            });
        }
        
        console.log('Sending request to /api/keys/batch, request data:', requestData);
        
        // 发送请求
        const response = await apiRequest('/api/keys/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        console.log('Received batch import response:', response);
        
        if (response && response.success) {
            // 隐藏模态框
            bootstrap.Modal.getInstance(document.getElementById('importKeysModal')).hide();
            
            // 刷新密钥列表
            await loadKeys();
            
            // 显示成功消息
            const successCount = response.imported || importPreviewData.length;
            const skippedCount = response.skipped || 0;
            let message = `Successfully imported ${successCount} keys`;
            if (skippedCount > 0) {
                message += `, ${skippedCount} duplicate keys skipped`;
            }
            showToast(message, 'success');
            console.log('Import completed successfully');
        } else {
            const errorMsg = (response && response.message) ? response.message : 'Unknown error';
            showToast('Import failed: ' + errorMsg, 'danger');
            console.error('Import failed, server response:', response);
        }
    } catch (error) {
        console.error('An exception occurred during import:', error);
        showToast('Import failed: ' + error.message, 'danger');
    } finally {
        // 恢复按钮状态
        const importBtn = document.getElementById('confirm-import-btn');
        importBtn.disabled = false;
        importBtn.textContent = 'Import';
    }
}