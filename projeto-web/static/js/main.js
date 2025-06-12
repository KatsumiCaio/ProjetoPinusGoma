// JavaScript para Sistema Florestal - Login e Menu

document.addEventListener('DOMContentLoaded', function() {
    console.log('🌲 Sistema Florestal carregado!');
    
    // Auto-hide alerts após 5 segundos
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);
    });

    // Validação do formulário de login
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value.trim();
            
            if (!username || !password) {
                e.preventDefault();
                showAlert('🚨 Por favor, preencha todos os campos!', 'error');
            }
        });
    }

    // Validação do formulário de entrada de carga
    const entradaCargaForm = document.querySelector('form');
    if (entradaCargaForm) {
        entradaCargaForm.addEventListener('submit', function(e) {
            const requiredFields = ['fornecedor', 'data_entrada', 'motorista', 'placa', 'quantidade_tambores', 'especie_resina', 'lote', 'ticket_pesagem', 'peso_liquido'];
            let isValid = true;

            requiredFields.forEach(fieldId => {
                const field = document.getElementById(fieldId);
                if (!field || !field.value.trim()) {
                    isValid = false;
                    field.style.border = '2px solid red';
                } else {
                    field.style.border = '';
                }
            });

            if (!isValid) {
                e.preventDefault();
                showAlert('⚠️ Por favor, preencha todos os campos obrigatórios!', 'error');
            }
        });
    }

    // Animação dos cards do menu
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
            item.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateY(0)';
        }, index * 150);
    });

    // Efeito de hover nos cards do menu
    menuItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
});

// Função para mostrar alertas dinamicamente
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container') || document.querySelector('.menu-container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
}

// Função para confirmar logout
function confirmLogout() {
    return confirm('🌲 Tem certeza que deseja sair do sistema?');
}

// Função para voltar à página anterior
function goBack() {
    window.history.back();
}

// Função para adicionar efeitos visuais
function addVisualEffects() {
    // Adiciona classe de animação aos elementos
    const elementsToAnimate = document.querySelectorAll('.container, .menu-container');
    elementsToAnimate.forEach(element => {
        element.classList.add('fade-in-up');
    });
}

// Chama efeitos visuais quando a página carrega
document.addEventListener('DOMContentLoaded', addVisualEffects);
