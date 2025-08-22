document.addEventListener('DOMContentLoaded', function() {
    // 获取当前配置
    fetchConfig();
    
    // 保存配置按钮事件
    document.getElementById('saveConfig').addEventListener('click', saveConfig);
});

// 获取当前配置 
function fetchConfig() {
    fetch('/api/config', {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + getAdminKey()
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to fetch configuration. Please check if the admin key is correct.');
        }
        return response.json();
    })
    .then(data => {
        // Proxy settings
        document.getElementById('proxy_host').value = data.PROXY_HOST || '';
        document.getElementById('proxy_port').value = data.PROXY_PORT || '';
        document.getElementById('proxy_user').value = data.PROXY_USER || '';
        
        // Proxy password field
        const proxyPassField = document.getElementById('proxy_pass');
        if (data.PROXY_PASS && data.PROXY_PASS !== '') {
            // Set proxy password placeholder to prevent user modification
            proxyPassField.setAttribute('placeholder', 'Proxy password set (leave blank to keep)');
        } else {
            proxyPassField.setAttribute('placeholder', 'Proxy Password');
        }
        
        // Image localization settings
        document.getElementById('image_localization').checked = data.IMAGE_LOCALIZATION || false;
        document.getElementById('image_save_dir').value = data.IMAGE_SAVE_DIR || 'src/static/images';
    })
    .catch(error => {
        showMessage('Error', error.message, 'danger');
    });
}

// Save configuration
function saveConfig() {
    // Get proxy settings
    const proxyHost = document.getElementById('proxy_host').value.trim();
    const proxyPort = document.getElementById('proxy_port').value.trim();
    const proxyUser = document.getElementById('proxy_user').value.trim();
    const proxyPass = document.getElementById('proxy_pass').value.trim();
    
    // Get image localization settings
    const imageLocalization = document.getElementById('image_localization').checked;
    const imageSaveDir = document.getElementById('image_save_dir').value.trim();
    
    // Create configuration object
    const config = {
        PROXY_HOST: proxyHost,
        PROXY_PORT: proxyPort,
        PROXY_USER: proxyUser,
        IMAGE_LOCALIZATION: imageLocalization,
        IMAGE_SAVE_DIR: imageSaveDir,
        save_to_env: true
    };
    
    // If proxy password exists, add it to the configuration object
    if (proxyPass) {
        config.PROXY_PASS = proxyPass;
    }
    
    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAdminKey()
        },
        body: JSON.stringify(config)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save configuration. Please check if the admin key is correct.');
        }
        return response.json();
    })
    .then(data => {
        showMessage('Success', 'Configuration saved', 'success');
        
        // After success, immediately re-fetch configuration to update display
        setTimeout(fetchConfig, 1000);
    })
    .catch(error => {
        showMessage('Error', error.message, 'danger');
    });
}

// Get admin key
function getAdminKey() {
    return localStorage.getItem('adminKey') || '';
}

// 显示消息
function showMessage(title, message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <strong>${title}:</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const messagesContainer = document.getElementById('messages');
    messagesContainer.appendChild(alertDiv);
    
    // 5秒后自动关闭
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
} 