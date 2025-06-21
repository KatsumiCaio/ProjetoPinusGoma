from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import json
import os
from datetime import datetime
import logging
import sqlite3
from werkzeug.utils import secure_filename
from unir_pdfs import unir_pdfs
from flask import send_file
import pandas as pd

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
PROCESSOS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'processos_pdfs')
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
                fornecedor, data_entrada, motorista, placa, quantidade_tambores, pedido_compra, categoria, especie_resina, lote, ticket_pesagem, peso_liquido, data_registro, usuario_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entrada['fornecedor'],
            entrada['data_entrada'],
            entrada['motorista'],
            entrada['placa'],
            entrada['quantidade_tambores'],
            entrada['pedido_compra'],
            entrada['categoria'],
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
TIPOS_PDF = ['processo', 'extra']

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

# Ajuste para permitir envio de múltiplos arquivos, um por vez
@app.route('/registrar-processo', defaults={'lote': None}, methods=['GET', 'POST'])
@app.route('/registrar-processo/<lote>', methods=['GET', 'POST'])
def registrar_processo(lote):
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT lote FROM entradas_carga ORDER BY lote ASC')
    lotes = [row[0] for row in cursor.fetchall()]
    conn.close()

    if request.method == 'POST':
        lote = request.form.get('lote')
        usuario = session.get('username', 'desconhecido')
        arquivos = {}

        for tipo in TIPOS_PDF:
            file = request.files.get(f'pdf_{tipo}')
            if file and file.filename:
                nome_temp = secure_filename(f"{lote}_{tipo}_temp.pdf")
                caminho_temp = os.path.join(PROCESSOS_DIR, nome_temp)
                file.save(caminho_temp)

                nome_final = secure_filename(f"{lote}_{tipo}.pdf")
                caminho_final = os.path.join(PROCESSOS_DIR, nome_final)
                if os.path.exists(caminho_final):
                    os.remove(caminho_final)
                os.rename(caminho_temp, caminho_final)
                arquivos[tipo] = nome_final

        caminho_processo = os.path.join(PROCESSOS_DIR, f"{lote}_processo.pdf")
        caminho_extra = os.path.join(PROCESSOS_DIR, f"{lote}_extra.pdf")
        caminho_final = os.path.join(PROCESSOS_DIR, f"{lote}_final.pdf")

        if 'processo' in arquivos and 'extra' not in arquivos:
            os.rename(os.path.join(PROCESSOS_DIR, arquivos['processo']), caminho_processo)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''REPLACE INTO processos_lote (lote, arquivo_pdf, data_upload, usuario) VALUES (?, ?, ?, ?)''',
                           (lote, f"{lote}_processo.pdf", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), usuario))
            conn.commit()
            conn.close()

        elif 'extra' in arquivos and 'processo' not in arquivos:
            if os.path.exists(caminho_processo):
                unir_pdfs([caminho_processo, os.path.join(PROCESSOS_DIR, arquivos['extra'])], caminho_final)
                os.remove(caminho_processo)
                os.remove(os.path.join(PROCESSOS_DIR, arquivos['extra']))
                os.rename(caminho_final, caminho_processo)
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''REPLACE INTO processos_lote (lote, arquivo_pdf, data_upload, usuario) VALUES (?, ?, ?, ?)''',
                               (lote, f"{lote}_processo.pdf", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), usuario))
                conn.commit()
                conn.close()

        elif 'processo' in arquivos and 'extra' in arquivos:
            unir_pdfs([os.path.join(PROCESSOS_DIR, arquivos['processo']), os.path.join(PROCESSOS_DIR, arquivos['extra'])], caminho_final)
            os.remove(os.path.join(PROCESSOS_DIR, arquivos['processo']))
            os.remove(os.path.join(PROCESSOS_DIR, arquivos['extra']))
            os.rename(caminho_final, caminho_processo)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''REPLACE INTO processos_lote (lote, arquivo_pdf, data_upload, usuario) VALUES (?, ?, ?, ?)''',
                           (lote, f"{lote}_processo.pdf", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), usuario))
            conn.commit()
            conn.close()

        flash(f'✅ PDFs processados para o lote {lote} com sucesso!', 'success')
        return redirect(url_for('registrar_processo', lote=lote))

    return render_template('registrar_processo.html', lotes=lotes, lote_selecionado=lote)

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
@app.route('/entrada-carga/<int:id>', methods=['GET', 'POST'])
def entrada_carga(id=None):
    """Página para registrar ou editar entrada de carga usando banco de dados"""
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    entrada = None
    if id:
        cursor.execute('SELECT * FROM entradas_carga WHERE id=?', (id,))
        row = cursor.fetchone()
        colunas = [desc[0] for desc in cursor.description]
        entrada = dict(zip(colunas, row)) if row else None
    if request.method == 'POST':
        fornecedor = request.form['fornecedor'].strip()
        data_entrada = request.form['data_entrada']
        motorista = request.form['motorista'].strip()
        placa = request.form['placa'].strip().upper()
        quantidade_tambores = request.form['quantidade_tambores']
        pedido_compra = request.form.get('pedido_compra', '').strip()
        categoria = request.form.get('categoria', '').strip()
        especie_resina = request.form['especie_resina']
        lote = request.form['lote'].strip()
        ticket_pesagem = request.form['ticket_pesagem'].strip()
        peso_liquido = request.form['peso_liquido']
        # Verifica se o lote já existe (exceto se for edição do mesmo id)
        cursor.execute('SELECT id FROM entradas_carga WHERE lote=?', (lote,))
        lote_existente = cursor.fetchone()
        if lote_existente and (not id or lote_existente[0] != id):
            flash('❌ Esse lote já existe!', 'error')
            if entrada:
                conn.close()
                return render_template('entrada_carga.html', entrada=entrada, editar=True)
            else:
                conn.close()
                return render_template('entrada_carga.html', editar=False)
        if id and entrada:
            # Atualiza
            cursor.execute('''UPDATE entradas_carga SET fornecedor=?, data_entrada=?, motorista=?, placa=?, quantidade_tambores=?, pedido_compra=?, categoria=?, especie_resina=?, ticket_pesagem=?, peso_liquido=? WHERE id=?''',
                (fornecedor, data_entrada, motorista, placa, quantidade_tambores, pedido_compra, categoria, especie_resina, ticket_pesagem, peso_liquido, id))
            conn.commit()
            conn.close()
            flash('✅ Entrada de carga atualizada com sucesso!', 'success')
            return redirect(url_for('relatorio_entradas'))
        else:
            # Novo registro
            nova_entrada = {
                'fornecedor': fornecedor,
                'data_entrada': data_entrada,
                'motorista': motorista,
                'placa': placa,
                'quantidade_tambores': quantidade_tambores,
                'pedido_compra': pedido_compra,
                'categoria': categoria,
                'especie_resina': especie_resina,
                'lote': lote,
                'ticket_pesagem': ticket_pesagem,
                'peso_liquido': peso_liquido,
                'data_registro': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'usuario_registro': session['username']
            }
            if inserir_entrada_carga(nova_entrada):
                conn.close()
                flash('✅ Entrada de carga registrada com sucesso!', 'success')
                return redirect(url_for('menu'))
            else:
                conn.close()
                flash('❌ Erro ao salvar entrada de carga! Ticket duplicado.', 'error')
                return render_template('entrada_carga.html', editar=False)
    conn.close()
    return render_template('entrada_carga.html', entrada=entrada, editar=bool(id))

# Correção para evitar botões duplicados
@app.route('/relatorio-entradas')
def relatorio_entradas():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    entradas = listar_entradas()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT lote, arquivo_pdf FROM processos_lote')
    pdfs_lotes = cursor.fetchall()
    conn.close()
    lotes_pdfs = {}
    for lote, pdf in pdfs_lotes:
        lotes_pdfs[lote] = pdf  # Garante que o último PDF vinculado ao lote seja exibido
    return render_template('relatorio_entradas.html', entradas=entradas, lotes_pdfs=lotes_pdfs)

# Função para redirecionar com lógica de PDF
@app.route('/verificar-pdf/<lote>')
def verificar_pdf(lote):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT arquivo_pdf FROM processos_lote WHERE lote = ?', (lote,))
    pdf = cursor.fetchone()
    conn.close()
    if pdf:
        return redirect(url_for('abrir_pdf_nome', nome_arquivo=pdf[0]))
    else:
        return redirect(url_for('registrar_processo'))

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

@app.route('/editar-entrada/<int:id>', methods=['GET', 'POST'])
def editar_entrada(id):
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        # Recebe os dados do formulário
        fornecedor = request.form['fornecedor'].strip()
        data_entrada = request.form['data_entrada']
        motorista = request.form['motorista'].strip()
        placa = request.form['placa'].strip().upper()
        quantidade_tambores = request.form['quantidade_tambores']
        pedido_compra = request.form.get('pedido_compra', '').strip()
        categoria = request.form.get('categoria', '').strip()
        especie_resina = request.form['especie_resina']
        lote = request.form['lote'].strip()
        ticket_pesagem = request.form['ticket_pesagem'].strip()
        peso_liquido = request.form['peso_liquido']
        # Atualiza no banco
        cursor.execute('''UPDATE entradas_carga SET fornecedor=?, data_entrada=?, motorista=?, placa=?, quantidade_tambores=?, pedido_compra=?, categoria=?, especie_resina=?, lote=?, ticket_pesagem=?, peso_liquido=? WHERE id=?''',
            (fornecedor, data_entrada, motorista, placa, quantidade_tambores, pedido_compra, categoria, especie_resina, lote, ticket_pesagem, peso_liquido, id))
        conn.commit()
        conn.close()
        flash('✅ Entrada de carga atualizada com sucesso!', 'success')
        return redirect(url_for('relatorio_entradas'))
    # GET: busca dados atuais
    cursor.execute('SELECT * FROM entradas_carga WHERE id=?', (id,))
    row = cursor.fetchone()
    colunas = [desc[0] for desc in cursor.description]
    entrada = dict(zip(colunas, row)) if row else None
    conn.close()
    if not entrada:
        flash('❌ Entrada não encontrada!', 'error')
        return redirect(url_for('relatorio_entradas'))
    return render_template('editar_entrada.html', entrada=entrada)

@app.route('/editar-pdf/<int:id>', methods=['GET', 'POST'])
def editar_pdf(id):
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entradas_carga WHERE id=?', (id,))
    row = cursor.fetchone()
    colunas = [desc[0] for desc in cursor.description]
    entrada = dict(zip(colunas, row)) if row else None
    if not entrada:
        conn.close()
        flash('❌ Entrada não encontrada!', 'error')
        return redirect(url_for('relatorio_entradas'))
    if request.method == 'POST':
        if 'pdf' in request.files and request.files['pdf'].filename:
            pdf = request.files['pdf']
            filename = secure_filename(f"{entrada['lote']}_{entrada['ticket_pesagem']}.pdf")
            pdf_path = os.path.join(PROCESSOS_DIR, filename)
            # Excluir PDF anterior
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            pdf.save(pdf_path)
            flash('✅ PDF atualizado com sucesso!', 'success')
        else:
            flash('❌ Nenhum arquivo PDF selecionado!', 'error')
        conn.close()
        return redirect(url_for('relatorio_entradas'))
    conn.close()
    return render_template('editar_pdf.html', entrada=entrada)

@app.route('/abrir-pdf/<nome_arquivo>')
def abrir_pdf_nome(nome_arquivo):
    caminho = os.path.join(PROCESSOS_DIR, nome_arquivo)
    if os.path.exists(caminho):
        return send_from_directory(PROCESSOS_DIR, nome_arquivo, as_attachment=False)
    flash('PDF não encontrado.', 'error')
    return redirect(url_for('relatorio_entradas'))

@app.route('/excluir_entrada/<int:id>', methods=['POST'])
def excluir_entrada(id):
    if 'logged_in' not in session or not session['logged_in']:
        flash('🔒 Você precisa fazer login primeiro!', 'error')
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Busca o lote para remover o PDF
    cursor.execute('SELECT lote FROM entradas_carga WHERE id=?', (id,))
    row = cursor.fetchone()
    lote = row[0] if row else None
    # Remove a entrada do banco
    cursor.execute('DELETE FROM entradas_carga WHERE id=?', (id,))
    conn.commit()
    # Remove o PDF associado, se existir
    if lote:
        pdf_path = os.path.join(os.path.dirname(__file__), 'static', 'processos_pdfs', f'{lote}_processo.pdf')
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    # Remove o registro do PDF do banco, se existir
    cursor.execute('DELETE FROM processos_lote WHERE lote=?', (lote,))
    conn.commit()
    conn.close()
    flash('✅ Entrada e PDF excluídos com sucesso!', 'success')
    return redirect(url_for('relatorio_entradas'))

@app.route('/exportar-excel')
def exportar_excel():
    entradas = listar_entradas()
    if not entradas:
        flash('Nenhuma entrada para exportar!', 'error')
        return redirect(url_for('relatorio_entradas'))
    # Monta DataFrame
    df = pd.DataFrame(entradas)
    # Renomeia colunas para nomes amigáveis
    df = df.rename(columns={
        'lote': 'Lote',
        'data_entrada': 'Data Entrada',
        'placa': 'Placa',
        'motorista': 'Motorista',
        'ticket_pesagem': 'Ticket Pesagem',
        'pedido_compra': 'Pedido de Compra',
        'fornecedor': 'Fornecedor',
        'quantidade_tambores': 'Qtd. Tambores',
        'peso_liquido': 'Peso Líquido (kg)',
        'especie_resina': 'Espécie Resina',
        'categoria': 'Categoria'
    })
    # Ordena por data
    if 'Data Entrada' in df:
        df = df.sort_values('Data Entrada')
    # Gera arquivo Excel em memória
    from io import BytesIO
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(
        output,
        download_name='relatorio_entradas.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/gerar-relatorio', methods=['GET'])
def gerar_relatorio():
    data_inicial = request.args.get('data_inicial')
    data_final = request.args.get('data_final')
    fornecedor = request.args.get('fornecedor')
    categoria = request.args.get('categoria')
    tipo_resina = request.args.get('tipo_resina')
    entradas = listar_entradas()
    # Filtra por data
    if data_inicial:
        entradas = [e for e in entradas if e['data_entrada'] >= data_inicial]
    if data_final:
        entradas = [e for e in entradas if e['data_entrada'] <= data_final]
    # Filtra por fornecedor
    if fornecedor:
        entradas = [e for e in entradas if e['fornecedor'] == fornecedor]
    # Filtra por categoria
    if categoria:
        entradas = [e for e in entradas if e.get('categoria','') == categoria]
    # Filtra por tipo de resina
    if tipo_resina:
        entradas = [e for e in entradas if e.get('especie_resina','') == tipo_resina]
    # Por enquanto, só exibe na tela (pode ser ajustado para gerar PDF/Excel)
    return render_template('relatorio_entradas.html', entradas=entradas, lotes_pdfs={})

@app.route('/exportar-excel-personalizado', methods=['GET'])
def exportar_excel_personalizado():
    data_inicial = request.args.get('data_inicial')
    data_final = request.args.get('data_final')
    fornecedor = request.args.get('fornecedor')
    categoria = request.args.get('categoria')
    tipo_resina = request.args.get('tipo_resina')
    entradas = listar_entradas()
    if data_inicial:
        entradas = [e for e in entradas if e['data_entrada'] >= data_inicial]
    if data_final:
        entradas = [e for e in entradas if e['data_entrada'] <= data_final]
    if fornecedor:
        entradas = [e for e in entradas if e['fornecedor'] == fornecedor]
    if categoria:
        entradas = [e for e in entradas if e.get('categoria','') == categoria]
    if tipo_resina:
        entradas = [e for e in entradas if e.get('especie_resina','') == tipo_resina]
    import pandas as pd
    from io import BytesIO
    df = pd.DataFrame(entradas)
    df = df.rename(columns={
        'lote': 'Lote',
        'data_entrada': 'Data Entrada',
        'placa': 'Placa',
        'motorista': 'Motorista',
        'ticket_pesagem': 'Ticket Pesagem',
        'pedido_compra': 'Pedido de Compra',
        'fornecedor': 'Fornecedor',
        'quantidade_tambores': 'Qtd. Tambores',
        'peso_liquido': 'Peso Líquido (kg)',
        'especie_resina': 'Espécie Resina',
        'categoria': 'Categoria'
    })
    if 'Data Entrada' in df:
        df = df.sort_values('Data Entrada')
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(
        output,
        download_name='relatorio_personalizado.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

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
