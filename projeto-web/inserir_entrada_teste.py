import sqlite3
from datetime import datetime

# Conectar ao banco de dados
conn = sqlite3.connect('estoque.db')
cursor = conn.cursor()

# Inserir uma entrada de teste
cursor.execute('''
INSERT INTO entradas_carga (
    fornecedor, data_entrada, motorista, placa, quantidade_tambores, especie_resina, lote, ticket_pesagem, peso_liquido, data_registro, usuario_registro
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    'Fornecedor Exemplo',
    '2025-06-16',
    'João da Silva',
    'ABC-1234',
    10,
    'Pinus',
    'Lote001',
    'TCK123',
    1500.0,
    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'admin'
))

conn.commit()
conn.close()

print('Entrada de teste inserida com sucesso!')
