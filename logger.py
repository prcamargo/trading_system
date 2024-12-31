import logging
from datetime import datetime
import sqlite3

# Configuração básica do logging
logger = logging.getLogger("BotTrader")
logger.setLevel(logging.DEBUG)  # Define o nível de logging

# Formato de log
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Handler para salvar logs em arquivo
file_handler = logging.FileHandler("trading_bot.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Handler para exibir logs no console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Adicionando handlers ao logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Função para criar o banco de dados e a tabela
def create_db():
    conn = sqlite3.connect('trading_bot.db')  # Cria/abre o banco de dados
    cursor = conn.cursor()

    # Cria a tabela de ordens, se não existir
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        side TEXT NOT NULL,
        symbol TEXT NOT NULL,
        quantity REAL NOT NULL,
        price_per_unit REAL NOT NULL,
        total_value REAL NOT NULL,
        transaction_time TEXT NOT NULL,
        order_type TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

create_db()


class log():

    def info(message):
        logger.info(message)

    def warning(message):
        logger.warning(message)

    def error(message):
        logger.error(message)


    @staticmethod
    def createLogOrder(order):
        side = order['side']
        order_type = order['type']
        quantity = order['quantity']
        symbol = order['symbol']
        price_per_unit = order['fills'][0]['price']
        currency = order['fills'][0]['commissionAsset']
        total_value = order['cummulativeQuoteQty']
        timestamp = order['transactTime']

        # convertendo timestamp para data/hora legivel
        transaction_time = datetime.utcfromtimestamp(timestamp / 1000).strftime('(%H:%M:%S) %Y-%m-%d')

        #Conectar ao banco de dados
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()

        # Inserir a ordem na tabela
        cursor.execute('''
        INSERT INTO orders (side, symbol, quantity, price_per_unit, total_value, transaction_time, order_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (side, symbol, quantity, price_per_unit, total_value, transaction_time, order_type))

        conn.commit()
        conn.close()

        log_message = (
            '\n------------------------\n'
            "ORDEM EXECUTADA: \n"
            f"Side: {side}\n"
            f"Ativo: {symbol}\n"
            f"Quantidade: {quantity}\n"
            f"Valor no momento: {price_per_unit}\n"
            f"Moeda: {currency}\n"
            f"Valor em {currency}: {total_value}\n"
            f"Type: {order_type}\n"
            f"Data/Hora: {transaction_time}\n"
            "\n"
            "Complete_order:\n"
            f"{order}"
            '\n------------------------\n'
        )

        logger.info(log_message)