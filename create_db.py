import sqlite3
import os

# Ubicacion de la BD
FOLDER = os.getcwd()

conn = sqlite3.connect(
    os.path.join(FOLDER, "case_db.db")
)
cursor = conn.cursor()

cursor.execute('''
DROP TABLE IF EXISTS casos
''')

# Para no estar a cada rato con errores de que ya existe la tabla esa
cursor.execute('''
CREATE TABLE IF NOT EXISTS casos (
    case_id INTEGER,
    date TEXT,
    user_name TEXT,
    user_id INTEGER,
    user_email TEXT,
    case_info TEXT
)
''')

conn.close()