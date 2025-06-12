from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
from datetime import datetime

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

def save_users(users):
    """Salva usuários no arquivo JSON"""
    try:
        data = {'users': users}
        with open('users.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar usuários: {e}")
        return False

def load_processos():
    """Carrega processos do arquivo JSON"""
    try:
        with open('processos.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data['processos']
    except FileNotFoundError:
        print("Arquivo processos.json não encontrado!")
        return []

def save_processos(processos):
    """Salva processos no arquivo JSON"""
    try:
        data = {'processos': processos}
        with open('processos.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar processos: {e}")
        return False

def validate_user(username, password):
    """Valida credenciais do usuário"""
    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            return True
    return False

def user_exists(username):
    """Verifica se usuário já existe"""
    users = load_users()
    for user in users:
        if user['username'] == username:
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

@app.route('/registrar-processo', methods=['GET', 'POST'])
def registrar_processo():
    """Página para registrar novos processos"""
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Coleta dados do formulário
        numero_processo = request.form['numero_processo']
        tipo_processo = request.form['tipo_processo']
        descricao = request.form['descricao']
        localizacao = request.form['localizacao']
        area_hectares = request.form['area_hectares']
        
        # Validação básica
        if not all([numero_processo, tipo_processo, descricao, localizacao, area_hectares]):
            flash('❌ Todos os campos são obrigatórios!', 'error')
            return render_template('registrar_processo.html')
        
        # Carrega processos existentes
        processos = load_processos()
        
        # Verifica se o número do processo já existe
        for processo in processos:
            if processo['numero_processo'] == numero_processo:
                flash('❌ Número de processo já existe!', 'error')
                return render_template('registrar_processo.html')
        
        # Cria novo processo
        novo_processo = {
            'id': len(processos) + 1,
            'numero_processo': numero_processo,
            'tipo_processo': tipo_processo,
            'descricao': descricao,
            'localizacao': localizacao,
            'area_hectares': float(area_hectares),
            'data_registro': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'usuario_registro': session['username'],
            'status': 'Em Análise'
        }
        
        # Adiciona à lista e salva
        processos.append(novo_processo)
        if save_processos(processos):
            flash('✅ Processo registrado com sucesso!', 'success')
            return redirect(url_for('menu'))
        else:
            flash('❌ Erro ao salvar processo!', 'error')
    
    return render_template('registrar_processo.html')

@app.route('/cadastrar-usuario', methods=['GET', 'POST'])
def cadastrar_usuario():
    """Página para cadastrar novos usuários"""
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Coleta dados do formulário
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        nome_completo = request.form['nome_completo'].strip()
        email = request.form['email'].strip()
        
        # Validação básica
        if not all([username, password, confirm_password, nome_completo, email]):
            flash('❌ Todos os campos são obrigatórios!', 'error')
            return render_template('cadastrar_usuario.html')
        
        # Verifica se as senhas coincidem
        if password != confirm_password:
            flash('❌ As senhas não coincidem!', 'error')
            return render_template('cadastrar_usuario.html')
        
        # Verifica se o usuário já existe
        if user_exists(username):
            flash('❌ Nome de usuário já existe!', 'error')
            return render_template('cadastrar_usuario.html')
        
        # Carrega usuários existentes
        users = load_users()
        
        # Cria novo usuário
        novo_usuario = {
            'username': username,
            'password': password,
            'nome_completo': nome_completo,
            'email': email,
            'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'cadastrado_por': session['username']
        }
        
        # Adiciona à lista e salva
        users.append(novo_usuario)
        if save_users(users):
            flash('✅ Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('menu'))
        else:
            flash('❌ Erro ao salvar usuário!', 'error')
    
    return render_template('cadastrar_usuario.html')

# Rotas temporárias para as páginas (apenas para não dar erro 404)
@app.route('/entrada-carga')
# Adicione estas funções após as outras funções de load/save

def load_entradas():
    """Carrega entradas de carga do arquivo JSON"""
    try:
        with open('entradas_carga.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data.get('entradas', [])  # Retorna lista vazia se não existir a chave
    except FileNotFoundError:
        print("Arquivo entradas_carga.json não encontrado! Criando arquivo...")
        # Cria o arquivo se não existir
        with open('entradas_carga.json', 'w', encoding='utf-8') as file:
            json.dump({"entradas": []}, file, indent=2)
        return []
    except json.JSONDecodeError:
        print("Erro no formato do arquivo entradas_carga.json!")
        return []


def save_entradas(entradas):
    """Salva entradas de carga no arquivo JSON"""
    try:
        data = {'entradas': entradas}
        with open('entradas_carga.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar entradas: {e}")
        return False

# Substitua a rota temporária por esta:

@app.route('/entrada-carga', methods=['GET', 'POST'])
def entrada_carga():
    """Página para registrar entrada de carga"""
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Coleta dados do formulário
        fornecedor = request.form['fornecedor'].strip()
        data_entrada = request.form['data_entrada']
        motorista = request.form['motorista'].strip()
        placa = request.form['placa'].strip().upper()
        quantidade_tambores = request.form['quantidade_tambores']
        especie_resina = request.form['especie_resina']
        lote = request.form['lote'].strip()
        ticket_pesagem = request.form['ticket_pesagem'].strip()
        peso_liquido = request.form['peso_liquido']
        
        # Validação básica
        if not all([fornecedor, data_entrada, motorista, placa, quantidade_tambores, 
                   especie_resina, lote, ticket_pesagem, peso_liquido]):
            flash('❌ Todos os campos são obrigatórios!', 'error')
            return render_template('entrada_carga.html')
        
        try:
            quantidade_tambores = int(quantidade_tambores)
            peso_liquido = float(peso_liquido)
        except ValueError:
            flash('❌ Quantidade de tambores deve ser um número inteiro e peso líquido um número válido!', 'error')
            return render_template('entrada_carga.html')
        
        # Carrega entradas existentes
        entradas = load_entradas()
        
        # Verifica se o ticket de pesagem já existe
        for entrada in entradas:
            if entrada['ticket_pesagem'] == ticket_pesagem:
                flash('❌ Número do ticket de pesagem já existe!', 'error')
                return render_template('entrada_carga.html')
        
        # Cria nova entrada
        nova_entrada = {
            'id': len(entradas) + 1,
            'fornecedor': fornecedor,
            'data_entrada': data_entrada,
            'motorista': motorista,
            'placa': placa,
            'quantidade_tambores': quantidade_tambores,
            'especie_resina': especie_resina,
            'lote': lote,
            'ticket_pesagem': ticket_pesagem,
            'peso_liquido': peso_liquido,
            'data_registro': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'usuario_registro': session['username']
        }
        
        # Adiciona à lista e salva
        entradas.append(nova_entrada)
        if save_entradas(entradas):
            flash('✅ Entrada de carga registrada com sucesso!', 'success')
            return redirect(url_for('menu'))
        else:
            flash('❌ Erro ao salvar entrada de carga!', 'error')
    
    return render_template('entrada_carga.html')


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

