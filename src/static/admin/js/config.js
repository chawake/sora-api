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
            throw new Error('获取配置失败，请检查管理员密钥是否正确');
        }
        return response.json();
    })
    .then(data => {
        // 代理设置
        document.getElementById('proxy_host').value = data.PROXY_HOST || '';
        document.getElementById('proxy_port').value = data.PROXY_PORT || '';
        document.getElementById('proxy_user').value = data.PROXY_USER || '';
        
        // 代理密码字段
        const proxyPassField = document.getElementById('proxy_pass');
        if (data.PROXY_PASS && data.PROXY_PASS !== '') {
            // 设置代理密码占位符，防止用户修改
            proxyPassField.setAttribute('placeholder', '已设置代理密码 (请保留空)');
        } else {
            proxyPassField.setAttribute('placeholder', '代理密码');
        }
        
        // 图像本地化设置
        document.getElementById('image_localization').checked = data.IMAGE_LOCALIZATION || false;
        document.getElementById('image_save_dir').value = data.IMAGE_SAVE_DIR || 'src/static/images';
    })
    .catch(error => {
        showMessage('错误', error.message, 'danger');
    });
}

// 保存配置
function saveConfig() {
    // 获取代理设置
    const proxyHost = document.getElementById('proxy_host').value.trim();
    const proxyPort = document.getElementById('proxy_port').value.trim();
    const proxyUser = document.getElementById('proxy_user').value.trim();
    const proxyPass = document.getElementById('proxy_pass').value.trim();
    
    // 获取图像本地化设置
    const imageLocalization = document.getElementById('image_localization').checked;
    const imageSaveDir = document.getElementById('image_save_dir').value.trim();
    
    // 创建配置对象
    const config = {
        PROXY_HOST: proxyHost,
        PROXY_PORT: proxyPort,
        PROXY_USER: proxyUser,
        IMAGE_LOCALIZATION: imageLocalization,
        IMAGE_SAVE_DIR: imageSaveDir,
        save_to_env: true
    };
    
    // 如果代理密码存在，则添加到配置对象中
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
            throw new Error('保存配置失败，请检查管理员密钥是否正确');
        }
        return response.json();
    })
    .then(data => {
        showMessage('成功', '配置已保存', 'success');
        
        // 成功后，立即重新获取配置以更新显示
        setTimeout(fetchConfig, 1000);
    })
    .catch(error => {
        showMessage('错误', error.message, 'danger');
    });
}

// 获取管理员密钥
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