import os
import time
import json
import sys
import argparse

import pandas as pd
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_LIMIT, TIME_IN_FORCE_GTC
from dotenv import load_dotenv

from strategy import *
from db import *
from logger import Logger

db = DatabaseManager() # inicia db sqlite


# Configurações
load_dotenv() #carregando variaveis da bianance
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
USE_TESTNET = True

# Variáveis globais
parser = argparse.ArgumentParser(description="Bot Trader")
parser.add_argument("-s", "--symbol", type=str, required=True, default="BTCUSDT", help="symbol para trader")
parser.add_argument("-b", "--base_asset", type=str, required=True, default="BTC", help="symbol para trader")
parser.add_argument("-q", "--quote_asset", type=str, required=True, default="USDT", help="symbol para trader")
args = parser.parse_args()

SYMBOL = args.symbol
BASE_ASSET = args.base_asset
QUOTE_ASSET = args.quote_asset
INTERVAL = '1h'
LOOKBACK = '200'
QUANTITY = 0.0001
STOP_LOSS_PERCENT = 0.98
TAKE_PROFIT_PERCENT = 1.02
MIN_QUOTE_BALANCE = 10

STATUS_FILE = 'bot_status.json'
HISTORY_FILE = 'trade_history.csv'
CURRENT_TRADE = {"side": None, "entry_price": None}
LOG_FILE = 'bot_trader.log'
LOG_LEVEL='INFO'


logger_instance = Logger(name="Bot Trader", log_file=LOG_FILE, level=LOG_LEVEL)
logger = logger_instance.get_logger()

# iniciando api binance
client = Client(API_KEY, API_SECRET)  # Use testnet conforme necessário

# Funções de persistência
def load_status():
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info('Criando arquivo bot_status.json')
        with open(STATUS_FILE, 'w') as f:
            json.dump(CURRENT_TRADE, f)

def save_status():
    with open(STATUS_FILE, 'w') as f:
        json.dump(CURRENT_TRADE, f)

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
    global CURRENT_TRADE
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=quantity,
            price=round(price, 2),
        )
        CURRENT_TRADE["side"] = side
        CURRENT_TRADE["entry_price"] = price
        #save_status()

        db.save_trade_history(side, quantity, price) # salva trade realizado 

        db.save_application_status(side, price) # atualiza o status 

        logger.info(f"Ordem executada: {order}")
    except Exception as e:
        logger.error(f"Erro ao executar ordem: {e}")

# Bot principal
def execute_bot():
    #load_status()

    last_status = db.get_last_application_status()
    print(last_status)

    while True:
        logger.info("-------------------------------------------------------------")
        
        if not check_balance():
            logger.warning("Saldo insuficiente.")
            sys.exit(1)

        try:
            
            data = fetch_data(SYMBOL, INTERVAL, LOOKBACK)
            data = apply_strategies(data)
            #print(data)
            last_signal = data['Combined_Signal'].iloc[-1]
            price = float(client.get_symbol_ticker(symbol=SYMBOL)['price'])

            logger.info(f"Sinal atual: {last_signal}, Preço atual: {price}")

            if last_signal > 0:
                logger.info("Sinal de Compra detectado!")
                execute_order_with_risk(SYMBOL, SIDE_BUY, QUANTITY, price)

            elif last_signal < 0:
                logger.info("Sinal de Venda detectado!")
                execute_order_with_risk(SYMBOL, SIDE_SELL, QUANTITY, price)

            time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Bot encerrado manualmente.")
            break
        except Exception as e:
            logger.error(f"Erro: {e}")
            time.sleep(60)

if __name__ == "__main__":
    execute_bot()
