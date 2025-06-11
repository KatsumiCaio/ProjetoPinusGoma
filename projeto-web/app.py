from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os

app = Flask(__name__)
app.secret_key = 'florestal_secret_key_2024'  # Mude para uma chave mais segura em produção

def load_users():
    """Carrega usuários do arquivo JSON"""
    try:
        with open('users.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data['users']
    except FileNotFoundError:
        print("Arquivo users.json não encontrado!")
        return []

def validate_user(username, password):
    """Valida credenciais do usuário"""
    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            return True
    return False

@app.route('/')
def index():
    """Rota principal - redireciona para login ou menu"""
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('menu'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if validate_user(username, password):
            session['logged_in'] = True
            session['username'] = username
            flash('🌲 Login realizado com sucesso!', 'success')
            return redirect(url_for('menu'))
        else:
            flash('❌ Usuário ou senha inválidos!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout do usuário"""
    session.clear()
    flash('👋 Logout realizado com sucesso!', 'info')
    return redirect(url_for('login'))

@app.route('/menu')
def menu():
    """Página do menu principal"""
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    
    return render_template('menu.html', username=session.get('username'))

# Rotas temporárias para as páginas (apenas para não dar erro 404)
@app.route('/entrada-carga')
def entrada_carga():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    return "<h1>🚧 Página em construção - Entrada de Carga</h1><a href='/menu'>Voltar ao Menu</a>"

@app.route('/relatorio-entradas')
def relatorio_entradas():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    return "<h1>🚧 Página em construção - Relatório de Entradas</h1><a href='/menu'>Voltar ao Menu</a>"

@app.route('/encontrar-processo')
def encontrar_processo():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    return "<h1>🚧 Página em construção - Encontrar Processo</h1><a href='/menu'>Voltar ao Menu</a>"

if __name__ == '__main__':
    print("🌲 Iniciando Sistema Florestal...")
    print("📋 Usuários disponíveis:")
    users = load_users()
    for user in users:
        print(f"   👤 {user['username']} / 🔒 {user['password']}")
    print("🌐 Acesse: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
