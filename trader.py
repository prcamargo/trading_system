import os
import time
import logging
import pandas as pd
from binance.client import Client
from ta.trend import SMAIndicator
from dotenv import load_dotenv
import pytz

# Configurar logging
# logging.basicConfig(
#     filename="trading_bot.log",
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Configure timezone
timezone = pytz.timezone('America/Sao_Paulo')

# Configuração da API (modo Testnet)
load_dotenv() # load env
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
USE_TESTNET = False

client = Client(API_KEY, API_SECRET, tld='com')
if USE_TESTNET:
    client.API_URL = 'https://testnet.binance.vision/api'

client.ping() #ping binance

# Configurações do Bot
SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
MA_PERIOD = 20
QUANTITY = 0.00011000
STOP_LOSS_PERCENT = 0.02  # 2%
TAKE_PROFIT_PERCENT = 0.03  # 3%

# Funções auxiliares
def get_historical_data(symbol, interval, lookback):
    """Obtém dados históricos de candles."""
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=lookback)
        data = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'quote_asset_volume', 'number_of_trades', 
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        data['close'] = pd.to_numeric(data['close'])
        return data
    except Exception as e:
        logging.error(f"Erro ao obter dados históricos: {e}")
        return None

def calculate_sma(data, period):
    """Calcula a média móvel simples."""
    sma_indicator = SMAIndicator(data['close'], window=period)
    data['sma'] = sma_indicator.sma_indicator()
    return data

def place_order(symbol, side, quantity):
    """Coloca uma ordem de compra ou venda."""
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )
        logging.info(f"Ordem executada: {side} {quantity} {symbol}")
        return order
    except Exception as e:
        logging.error(f"Erro ao executar ordem: {e}")
        return None

def backtest_strategy(data):
    """Executa um backtest da estratégia em dados históricos."""
    data = calculate_sma(data, MA_PERIOD)
    position_open = False
    initial_balance = 1000
    balance = initial_balance
    quantity = 0

    for i in range(MA_PERIOD, len(data)):
        close = data['close'].iloc[i]
        sma = data['sma'].iloc[i]

        if not position_open and close > sma:
            quantity = balance / close
            position_open = True
            logging.info(f"Compra simulada: {quantity} BTC a {close}")

        elif position_open and close < sma:
            balance = quantity * close
            position_open = False
            logging.info(f"Venda simulada: {quantity} BTC a {close}, Saldo: {balance}")

    logging.info(f"Backtest concluído: Saldo final: {balance}, Lucro: {balance - initial_balance}")
    return balance - initial_balance

def get_lot_size(symbol):
    """Obtém as regras de tamanho de lote para o símbolo especificado."""
    try:
        exchange_info = client.get_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        return {
                            'minQty': float(f['minQty']),
                            'maxQty': float(f['maxQty']),
                            'stepSize': float(f['stepSize'])
                        }
    except Exception as e:
        logging.error(f"Erro ao obter informações de tamanho de lote: {e}")
        return None

# Execução principal
def main():
    position_open = False
    entry_price = 0

    while True:
        try:
            # regra para ordens
            #lot_size = get_lot_size(SYMBOL)
            #logging.info(lot_size)

            # Obter dados de candles
            data = get_historical_data(SYMBOL, INTERVAL, MA_PERIOD + 1)
            if data is None:
                time.sleep(60)
                continue

            # Calcular a média móvel
            data = calculate_sma(data, MA_PERIOD)
            last_close = data['close'].iloc[-1]
            last_sma = data['sma'].iloc[-1]

            # Lógica de trading
            if not position_open and last_close > last_sma:
                logging.info(f"Condição de compra detectada: Preço de fechamento ({last_close}) acima da SMA ({last_sma}).")
                order = place_order(SYMBOL, Client.SIDE_BUY, QUANTITY)
                if order:
                    entry_price = last_close
                    position_open = True
                    logging.info(f"Compra realizada: Entrada em {entry_price}. Quantidade: {QUANTITY}.")

            elif position_open:
                stop_loss = entry_price * (1 - STOP_LOSS_PERCENT)
                take_profit = entry_price * (1 + TAKE_PROFIT_PERCENT)

                logging.info(f"Monitorando posição: Preço atual {last_close}, Stop Loss em {stop_loss}, Take Profit em {take_profit}.")

                if last_close <= stop_loss:
                    logging.info(f"Condição de Stop Loss atingida: Preço de fechamento ({last_close}) <= Stop Loss ({stop_loss}).")
                    place_order(SYMBOL, Client.SIDE_SELL, QUANTITY)
                    position_open = False
                    profit_loss = (last_close - entry_price) * QUANTITY
                    logging.info(f"Venda realizada devido ao Stop Loss. Resultado da transação: {'Lucro' if profit_loss > 0 else 'Prejuízo'} de {profit_loss:.2f} USDT.")

                elif last_close >= take_profit:
                    logging.info(f"Condição de Take Profit atingida: Preço de fechamento ({last_close}) >= Take Profit ({take_profit}).")
                    place_order(SYMBOL, Client.SIDE_SELL, QUANTITY)
                    position_open = False
                    profit_loss = (last_close - entry_price) * QUANTITY
                    logging.info(f"Venda realizada devido ao Take Profit. Resultado da transação: {'Lucro' if profit_loss > 0 else 'Prejuízo'} de {profit_loss:.2f} USDT.")

            # Esperar pelo próximo candle
            logging.info("Aguardando próximo candle...")
            time.sleep(60)
        except Exception as e:
            logging.error(f"Erro no loop principal: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Modo backtest ou ao vivo
    MODE = "LIVE"  # Alterar para "BACKTEST" para testar ou LIVE

    if MODE == "BACKTEST":
        historical_data = get_historical_data(SYMBOL, INTERVAL, 500)
        if historical_data is not None:
            backtest_strategy(historical_data)
    else:

        main()
