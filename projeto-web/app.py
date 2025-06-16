from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import json
import os
from datetime import datetime
import logging
import sqlite3
from werkzeug.utils import secure_filename
from unir_pdfs import unir_pdfs

app = Flask(__name__)
app.secret_key = 'florestal_secret_key_2024'  # Mude para uma chave mais segura em produção

# Configuração de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def load_users():
    """Carrega usuários do arquivo JSON"""
    try:
        with open('users.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data['users']
    except FileNotFoundError:
        logging.warning("Arquivo users.json não encontrado! Criando arquivo...")
        # Cria o arquivo com um usuário padrão
        default_users = {"users": [
            {"username": "admin", "password": "123456"}
        ]}
        with open('users.json', 'w', encoding='utf-8') as file:
            json.dump(default_users, file, indent=2, ensure_ascii=False)
        return default_users['users']
    except json.JSONDecodeError:
        logging.error("Erro no formato do arquivo users.json!")
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

def load_entradas():
    """Carrega entradas de carga do arquivo JSON"""
    try:
        with open('entradas_carga.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data.get('entradas', [])  # Retorna lista vazia se não existir a chave
    except FileNotFoundError:
        logging.warning("Arquivo entradas_carga.json não encontrado! Criando arquivo...")
        with open('entradas_carga.json', 'w', encoding='utf-8') as file:
            json.dump({"entradas": []}, file, indent=2)
        return []
    except json.JSONDecodeError:
        logging.error("Erro no formato do arquivo entradas_carga.json!")
        return []

def save_entradas(entradas):
    """Salva entradas de carga no arquivo JSON"""
    try:
        data = {'entradas': entradas}
        with open('entradas_carga.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        logging.info("Entradas de carga salvas com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar entradas: {e}")
        return False

def validate_user(username, password):
    """Valida credenciais do usuário"""
    logging.debug(f"Validando usuário: {username}")
    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            logging.info(f"Usuário {username} validado com sucesso.")
            return True
    logging.warning(f"Falha na validação do usuário: {username}")
    return False

def user_exists(username):
    """Verifica se usuário já existe"""
    users = load_users()
    for user in users:
        if user['username'] == username:
            return True
    return False

# Criação da tabela de processos vinculados a lotes e arquivos PDF
PROCESSOS_DIR = os.path.join(os.path.dirname(__file__), 'processos_pdfs')
if not os.path.exists(PROCESSOS_DIR):
    os.makedirs(PROCESSOS_DIR)

DB_PATH = os.path.join(os.path.dirname(__file__), 'estoque.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entradas_carga (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fornecedor TEXT NOT NULL,
            data_entrada TEXT NOT NULL,
            motorista TEXT NOT NULL,
            placa TEXT NOT NULL,
            quantidade_tambores INTEGER NOT NULL,
            especie_resina TEXT NOT NULL,
            lote TEXT NOT NULL,
            ticket_pesagem TEXT NOT NULL UNIQUE,
            peso_liquido REAL NOT NULL,
            data_registro TEXT NOT NULL,
            usuario_registro TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def init_db_processos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processos_lote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote TEXT NOT NULL,
            arquivo_pdf TEXT NOT NULL,
            data_upload TEXT NOT NULL,
            usuario TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def inserir_entrada_carga(entrada):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO entradas_carga (
                fornecedor, data_entrada, motorista, placa, quantidade_tambores, especie_resina, lote, ticket_pesagem, peso_liquido, data_registro, usuario_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entrada['fornecedor'],
            entrada['data_entrada'],
            entrada['motorista'],
            entrada['placa'],
            entrada['quantidade_tambores'],
            entrada['especie_resina'],
            entrada['lote'],
            entrada['ticket_pesagem'],
            entrada['peso_liquido'],
            entrada['data_registro'],
            entrada['usuario_registro']
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def ticket_existe(ticket_pesagem):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM entradas_carga WHERE ticket_pesagem = ?', (ticket_pesagem,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe

def listar_entradas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entradas_carga ORDER BY lote ASC')
    colunas = [desc[0] for desc in cursor.description]
    entradas = [dict(zip(colunas, row)) for row in cursor.fetchall()]
    conn.close()
    return entradas

UPLOAD_PDFS_DIR = os.path.join(os.path.dirname(__file__), 'processos_pdfs')
TIPOS_PDF = ['capa', 'ticket', 'nota', 'contra', 'comprovante', 'extra']

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
        logging.debug(f"Tentativa de login com usuário: {username}")
        
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
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))

    # Buscar lotes distintos já cadastrados
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT lote FROM entradas_carga ORDER BY lote ASC')
    lotes = [row[0] for row in cursor.fetchall()]
    conn.close()

    TIPOS = ['capa', 'ticket', 'nota', 'contra', 'comprovante', 'extra']
    if request.method == 'POST':
        lote = request.form.get('lote')
        usuario = session.get('username', 'desconhecido')
        arquivos_temp = []
        for tipo in TIPOS:
            file = request.files.get(f'pdf_{tipo}')
            if file and file.filename:
                nome_temp = secure_filename(f"{lote}_{tipo}_temp.pdf")
                caminho_temp = os.path.join(PROCESSOS_DIR, nome_temp)
                file.save(caminho_temp)
                arquivos_temp.append(caminho_temp)
        if arquivos_temp:
            nome_final = secure_filename(f"{lote}_final.pdf")
            caminho_final = os.path.join(PROCESSOS_DIR, nome_final)
            unir_pdfs(arquivos_temp, caminho_final)
            # Limpa arquivos temporários
            for arq in arquivos_temp:
                if os.path.exists(arq):
                    os.remove(arq)
            # Registrar no banco
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO processos_lote (lote, arquivo_pdf, data_upload, usuario) VALUES (?, ?, ?, ?)''',
                           (lote, nome_final, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), usuario))
            conn.commit()
            conn.close()
            flash(f'✅ PDF final gerado e vinculado ao lote {lote} com sucesso!', 'success')
        else:
            flash('❌ Nenhum arquivo PDF enviado!', 'error')
        return redirect(url_for('registrar_processo'))

    return render_template('registrar_processo.html', lotes=lotes)

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
@app.route('/entrada-carga', methods=['GET', 'POST'])
def entrada_carga():
    """Página para registrar entrada de carga usando banco de dados"""
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        fornecedor = request.form['fornecedor'].strip()
        data_entrada = request.form['data_entrada']
        motorista = request.form['motorista'].strip()
        placa = request.form['placa'].strip().upper()
        quantidade_tambores = request.form['quantidade_tambores']
        especie_resina = request.form['especie_resina']
        lote = request.form['lote'].strip()
        ticket_pesagem = request.form['ticket_pesagem'].strip()
        peso_liquido = request.form['peso_liquido']

        if not all([fornecedor, data_entrada, motorista, placa, quantidade_tambores, especie_resina, lote, ticket_pesagem, peso_liquido]):
            flash('❌ Todos os campos são obrigatórios!', 'error')
            return render_template('entrada_carga.html')

        try:
            quantidade_tambores = int(quantidade_tambores)
            peso_liquido = float(peso_liquido)
        except ValueError:
            flash('❌ Quantidade de tambores deve ser um número inteiro e peso líquido um número válido!', 'error')
            return render_template('entrada_carga.html')

        if ticket_existe(ticket_pesagem):
            flash('❌ Número do ticket de pesagem já existe!', 'error')
            return render_template('entrada_carga.html')

        nova_entrada = {
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

        if inserir_entrada_carga(nova_entrada):
            flash('✅ Entrada de carga registrada com sucesso!', 'success')
            return redirect(url_for('menu'))
        else:
            flash('❌ Erro ao salvar entrada de carga! Ticket duplicado.', 'error')

    return render_template('entrada_carga.html')


@app.route('/relatorio-entradas')
def relatorio_entradas():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    entradas = listar_entradas()
    return render_template('relatorio_entradas.html', entradas=entradas)

@app.route('/encontrar-processo')
def encontrar_processo():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    return "<h1>🚧 Página em construção - Encontrar Processo</h1><a href='/menu'>Voltar ao Menu</a>"

@app.route('/visualizar-pdfs/<lote>')
def visualizar_pdfs_lote(lote):
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT arquivo_pdf, data_upload, usuario FROM processos_lote WHERE lote = ?', (lote,))
    pdfs = cursor.fetchall()
    conn.close()
    return render_template('visualizar_pdfs_lote.html', lote=lote, pdfs=pdfs)

@app.route('/upload-pdfs/<lote>', methods=['GET', 'POST'])
def upload_pdfs(lote):
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        usuario = session.get('username', 'desconhecido')
        for tipo in TIPOS_PDF:
            file = request.files.get(f'pdf_{tipo}')
            if file and file.filename:
                filename = f"{lote}_{tipo}.pdf"
                file.save(os.path.join(UPLOAD_PDFS_DIR, filename))
                # Opcional: registrar no banco se quiser rastrear uploads
        flash('✅ PDFs enviados com sucesso!', 'success')
        return redirect(url_for('ver_pdfs', lote=lote))
    return render_template('upload.html')

@app.route('/ver-pdfs/<lote>')
def ver_pdfs(lote):
    links = []
    for tipo in TIPOS_PDF:
        filename = f"{lote}_{tipo}.pdf"
        path = os.path.join(UPLOAD_PDFS_DIR, filename)
        if os.path.exists(path):
            links.append((tipo.capitalize(), url_for('abrir_pdf', lote=lote, tipo=tipo)))
    return render_template('ver_pdfs.html', links=links)

@app.route('/abrir-pdf/<lote>/<tipo>')
def abrir_pdf(lote, tipo):
    filename = f"{lote}_{tipo}.pdf"
    return send_from_directory(UPLOAD_PDFS_DIR, filename)

@app.route('/baixar-pdf-lote/<lote>')
def baixar_pdf_lote(lote):
    nome_final = f"{lote}_final.pdf"
    caminho = os.path.join(PROCESSOS_DIR, nome_final)
    if os.path.exists(caminho):
        return send_from_directory(PROCESSOS_DIR, nome_final)
    flash('PDF final não encontrado para este lote.', 'error')
    return redirect(url_for('relatorio_entradas'))

if __name__ == '__main__':
    import os
    if not os.path.exists(DB_PATH):
        print("Banco de dados não encontrado. Criando banco e tabelas...")
        init_db()
        init_db_processos()
        print("Banco criado com sucesso.")
    else:
        print("Banco de dados encontrado.")
        # Garante que a tabela de processos existe mesmo se o banco já existir
        init_db_processos()

    app.run(debug=True)
