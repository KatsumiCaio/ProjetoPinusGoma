import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'estoque.db')

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
print('Tabela processos_lote criada com sucesso!')
