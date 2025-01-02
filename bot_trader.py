import threading
import logging
import os
import numpy as np
import pandas as pd
import talib
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_LIMIT, TIME_IN_FORCE_GTC
from datetime import datetime
from dotenv import load_dotenv
import time
import json
from dash import Dash, dcc, html
from dash.dependencies import Input, Output

# Configurações
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
USE_TESTNET = True

client = Client(API_KEY, API_SECRET)  # Use testnet conforme necessário

SYMBOL = "BTCUSDT"
BASE_ASSET = "BTC"
QUOTE_ASSET = "USDT"
INTERVAL = '1h'
LOOKBACK = '200'
QUANTITY = 0.0001
STOP_LOSS_PERCENT = 0.98
TAKE_PROFIT_PERCENT = 1.02
MIN_QUOTE_BALANCE = 10

STATUS_FILE = 'bot_status.json'
HISTORY_FILE = 'trade_history.csv'
LOG_FILE = 'bot_trader.log'
LOG_LEVEL = 'INFO'

# Configuração de logs
logger = logging.getLogger('BotTrader')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Variáveis globais
current_trade = {"side": None, "entry_price": None}

# Funções de persistência
def load_status():
    global current_trade
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r') as file:
            current_trade.update(json.load(file))

def save_status():
    with open(STATUS_FILE, 'w') as file:
        json.dump(current_trade, file)

# Verificar saldo
def check_balance():
    try:
        quote_balance = float(client.get_asset_balance(asset=QUOTE_ASSET)['free'])
        base_balance = float(client.get_asset_balance(asset=BASE_ASSET)['free'])

        if quote_balance < MIN_QUOTE_BALANCE and base_balance < QUANTITY:
            logger.warning(f"Saldo insuficiente: {QUOTE_ASSET}: {quote_balance}, {BASE_ASSET}: {base_balance}")
            return False
        else:
            logger.info(f"Saldo disponível: {QUOTE_ASSET}: {quote_balance}, {BASE_ASSET}: {base_balance}")
            return True
    except Exception as e:
        logger.error(f"Erro ao verificar saldo: {e}")
        return False


# Estratégias
def moving_average_strategy(data, short_window=10, long_window=50):
    data['SMA_Short'] = talib.SMA(data['close'], timeperiod=short_window)
    data['SMA_Long'] = talib.SMA(data['close'], timeperiod=long_window)
    data['Signal'] = data['SMA_Short'] > data['SMA_Long']
    return data

def rsi_strategy(data, rsi_period=14, overbought=70, oversold=30):
    data['RSI'] = talib.RSI(data['close'], timeperiod=rsi_period)
    #data['Signal'] = (data['RSI'] < oversold) - (data['RSI'] > overbought)

    buy_condition = data['RSI'] < overbought
    sell_condition = data['RSI'] > overbought

    data['Signal'] = np.where(buy_condition, 1, np.where(sell_condition, -1, 0))

    return data

def breakout_strategy(data):
    data['High_Max'] = data['high'].rolling(window=10).max()
    data['Low_Min'] = data['low'].rolling(window=10).min()
    
    # Condição de breakout para compra e venda
    buy_condition = data['close'] > data['High_Max']
    sell_condition = data['close'] < data['Low_Min']

    # Atribuindo 1 para compra, -1 para venda, e 0 para manter
    data['Signal'] = np.where(buy_condition, 1, np.where(sell_condition, -1, 0))

    return data

def fetch_data(symbol, interval, lookback):
    """
    Busca os dados históricos de candles (OHLCV) da Binance.
    
    :param symbol: O par de negociação (exemplo: 'BTCUSDT').
    :param interval: O intervalo de tempo (exemplo: '1h', '15m').
    :param lookback: A quantidade de candles a buscar (exemplo: '200').
    :return: DataFrame com os dados de candles.
    """
    try:
        # Obtém os dados de candles da Binance
        klines = client.get_klines(symbol=symbol, interval=interval, limit=int(lookback))

        # Converte os dados para um DataFrame do pandas
        data = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume", 
            "close_time", "quote_asset_volume", "number_of_trades", 
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
        ])

        # Seleciona apenas as colunas relevantes e ajusta os tipos
        data = data[["timestamp", "open", "high", "low", "close", "volume"]]
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        data[["open", "high", "low", "close", "volume"]] = data[["open", "high", "low", "close", "volume"]].astype(float)

        return data
    except Exception as e:
        logger.error(f"Erro ao buscar dados históricos: {e}")
        return pd.DataFrame()

# Função para executar ordens
def execute_order_with_risk(symbol, side, quantity, price):
    global current_trade
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=quantity,
            price=round(price, 2),
        )
        current_trade["side"] = side
        current_trade["entry_price"] = price
        save_status()
        logger.info(f"Ordem executada: {order}")
    except Exception as e:
        logger.error(f"Erro ao executar ordem: {e}")

# Bot principal
def execute_bot():
    load_status()
    while True:
        logger.info("-------------------------------------------------------------")
        
        if not check_balance():
            logger.warning("Saldo insuficiente.")
            sys.exit(1)

        try:
            
            data = fetch_data(SYMBOL, INTERVAL, LOOKBACK)
            data = moving_average_strategy(data)
            data = rsi_strategy(data)
            data = breakout_strategy(data)
            last_signal = data['Signal'].iloc[-1]
            price = float(client.get_symbol_ticker(symbol=SYMBOL)['price'])

            logger.info(f"Sinal atual: {last_signal}, Preço atual: {price}")

            if last_signal > 0:
                logger.info("Sinal de Compra detectado!")
                execute_order_with_risk(SYMBOL, SIDE_BUY, QUANTITY, price)

            elif last_signal < 0:
                logger.info("Sinal de Venda detectado!")
                execute_order_with_risk(SYMBOL, SIDE_SELL, QUANTITY, price)

            time.sleep(15)
        except KeyboardInterrupt:
            logger.info("Bot encerrado manualmente.")
            break
        except Exception as e:
            logger.error(f"Erro: {e}")
            time.sleep(60)

# Dashboard com Dash
def create_dashboard():
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("Histórico de Lucros e Perdas"),
        dcc.Graph(id='profit-graph'),
        dcc.Interval(id='update-interval', interval=1000, n_intervals=0)
    ])

    @app.callback(
        Output('profit-graph', 'figure'),
        Input('update-interval', 'n_intervals')
    )
    def update_graph(n):
        if os.path.exists(HISTORY_FILE):
            df = pd.read_csv(HISTORY_FILE)
            fig = {
                'data': [{
                    'x': df['timestamp'],
                    'y': df['profit'].cumsum(),
                    'type': 'line',
                    'name': 'Lucro Acumulado'
                }],
                'layout': {
                    'title': 'Histórico de Lucros/Perdas',
                    'xaxis': {'title': 'Tempo'},
                    'yaxis': {'title': 'Lucro'}
                }
            }
            return fig
        return {'data': [], 'layout': {'title': 'Sem Dados'}}

    app.run_server(debug=False, use_reloader=False)

# Multithreading
# def main():
#     bot_thread = threading.Thread(target=execute_bot)
#     dashboard_thread = threading.Thread(target=create_dashboard)
#     bot_thread.start()
#     dashboard_thread.start()
#     bot_thread.join()
#     dashboard_thread.join()


if __name__ == "__main__":
    #main()
    execute_bot()
