import sqlite3

class DatabaseManager:
    def __init__(self, db_file: str = 'bot_trader.db'):
        """
        Inicializa a conexão com o banco de dados e cria as tabelas se necessário.
        """
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Cria as tabelas no banco de dados se não existirem."""
        # Tabela para armazenar o status da aplicação
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            side TEXT,
            entry_price REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        # Tabela para armazenar o histórico de trades realizados
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            side TEXT,
            quantity REAL,
            price REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        self.conn.commit()

    def save_application_status(self, side, entry_price):
        """Salva o status atual da aplicação na tabela application_status."""
        self.cursor.execute('''
        INSERT INTO application_status (side, entry_price)
        VALUES (?, ?)''', (side, entry_price))
        self.conn.commit()

    def save_trade_history(self, side, quantity, price):
        """Salva um trade realizado na tabela trade_history."""
        self.cursor.execute('''
        INSERT INTO trade_history (side, quantity, price)
        VALUES (?, ?, ?)''', (side, quantity, price))
        self.conn.commit()

    def get_last_application_status(self):
        """Retorna o último status da aplicação."""
        self.cursor.execute('''
        SELECT * FROM application_status ORDER BY timestamp DESC LIMIT 1''')
        return self.cursor.fetchone()

    def get_trade_history(self):
        """Retorna o histórico de trades realizados."""
        self.cursor.execute('''
        SELECT * FROM trade_history ORDER BY timestamp DESC''')
        return self.cursor.fetchall()

    def close(self):
        """Fecha a conexão com o banco de dados."""
        self.conn.close()

