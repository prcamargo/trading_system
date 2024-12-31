import os
import time
from datetime import datetime
import logging

import pandas as pd
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv

from logger import *

from bot_strategy import * # importa as estrategias do arquivo bot_strategy.py

load_dotenv() # carregar .env
api_key = os.getenv('BINANCE_API_KEY')
secret_key = os.getenv('BINANCE_API_SECRET')
# print(api_key)
# print(secret_key)

# -------------------------------------------
# configuração 
# STOCK_CODE = "BNB"
# OPERATION_CODE = "BNBBTC"
STOCK_CODE = "BTC"
OPERATION_CODE = "BTCUSDT"
CANDLE_PERIOD = Client.KLINE_INTERVAL_15MINUTE
TRADED_QUANTITY = 0.00002 

# -------------------------------------------

# Define logger
logging.basicConfig(
    filename = 'logs/trading_bot.log',
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s'
)

# Classe principal

class BinanceTraderBot():

    last_trade_desision: bool # ultima decisão de posição ( False = Vender | True = Comprar)

    def __init__(self, stock_code, operation_code, traded_quantity, traded_percentage, candle_period):
        self.stock_code = stock_code # codigo principal da stck negociada ( ex 'BTC')
        self.operation_code = operation_code # codigo negociado/moeda ( ex 'BTC')
        self.traded_quantity = traded_quantity # quantidade inicial que será operadra
        self.traded_percentage = traded_percentage # porcentagem total da carteira, que será negociada
        self.candle_period = candle_period # periodo levado em consideração para operação ( ex 15min)

        self.client_binance = Client(api_key, secret_key) # inicia o client binance

        self.updateAllData() # Busca e atualiza todos os dados

        print('----------------------------------------------------------')
        print('Robo Trader iniciado...')
    # atualiza todos os dados da conta
    def updateAllData(self):
        self.account_data = self.getUpdateAccountData() # dados atualizado do usuario e sua carteira
        self.last_stock_account_balance = self.getLastStockAccountBalance() # balanço atual do ativo na carteira
        self.actual_trade_position = self.getActualTradePosition() # posição atual ( false = vendido | true = comprado)
        self.stock_data = self.getStockData_ClosePrice_OpenTime() # atualiza dados usados nos modelos


    # busca infos atualizada da conta Binance
    def getUpdateAccountData(self):
        return self.client_binance.get_account() # busca infos da conta
    
    # busca o ultimo balanço da conta, na stock escolhida
    def getLastStockAccountBalance(self):

        for stock in self.account_data['balances']:
            if stock['asset'] == self.stock_code:
                in_wallet_amount = stock['free']

        return float(in_wallet_amount)
    
    # checa se a posição atual é comprado ou vendido
    # futuramente integra com banco de dados para 
    # guardar este dado com mais precisão
    def getActualTradePosition(self):
        if self.last_stock_account_balance > 0.001:
            return True # comprado
        else:
            return False # esta vendido
        
    # busca os dados do ativo no periodo
    def getStockData_ClosePrice_OpenTime(self):
        
        # busca dados na binance dos ultimos 1000 periodos
        candles = self.client_binance.get_klines(symbol = self.operation_code, interval = self.candle_period, limit = 500)

        # transformar um datafram pandas
        prices = pd.DataFrame(candles)

        # renomea as colunas baseada na documentação da binance
        prices.columns = ['open_time', 'open_price', 'high_price', 'low_price', 'close_price',
                          'volume', 'close_time', 'quote_asset_volume', 'number_of_trades',
                          'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', '-']
        
        #pega apenas os indicadores que queremos para esse modelo
        prices = prices[['close_price', 'open_time']]

        #corrige o tempo de fechamento
        prices['open_time'] = pd.to_datetime(prices['open_time'], unit= 'ms').dt.tz_localize('UTC')

        # converte para o fuso horarios UTC -3
        prices['open_time'] = prices['open_time'].dt.tz_convert('America/Sao_Paulo')

        return prices;

    # --------------------------------------------------------
    # prints

    # printa toda a carteira
    def printWallet(self):
        for stock in self.account_data['balances']:
            if float(stock['free']) > 0:
                print(stock)

    # printa o ativo definido na classe
    def printStock(self):
        for stock in self.account_data['balances']:
            if float(stock['free']) > 0 :
                print(stock)

    # -------------------------------------------------------
    # compra a ação
    def buyStock(self):
        
        if self.actual_trade_position == False: # se a posição for vendida
            order_buy = self.client_binance.create_order(
                symbol = self.operation_code,
                side = SIDE_BUY,
                type = ORDER_TYPE_MARKET,
                quantity = self.traded_quantity,
            )
            # order_buy = self.client_binance.order_market_buy(
            #     symbol = self.operation_code,
            #     quantity= self.traded_quantity
            # )
            self.actual_trade_position = True # Define posição como comprada
            createLogOrder(order_buy) # cria um log
            return order_buy
        
        else: # se ocorreu algum erro
            logging.warning('Erro ao comprar')
            print('Erro ao comprar ')
            return False
        
    # vende a ação
    def sellStock(self):
        if self.actual_trade_position == True: # se a posição for comprada
            order_sell = self.client_binance.create_order(
                symbol = self.operation_code,
                side = SIDE_SELL,
                type = ORDER_TYPE_MARKET,
                quantity = int(self.last_stock_account_balance * 1000) / 1000
            )
            # order_sell = self.client_binance.order_market_sell(
            #     symbol=self.operation_code,
            #     quantity= int(self.last_stock_account_balance * 1000) / 1000
            # )
            self.actual_trade_position = False # define posição como vendida
            createLogOrder(order_sell) # cria log
            return order_sell
        
        else: # se ocorreu algum erro
            logging.warning('Erro ao comprar')
            print('Erro ao comprar')
            return False


    def execute(self):

        # atualiza todos os dados
        self.updateAllData()

        print('----------------------------------------------------------')
        print(f'Executado ({datetime.now().strftime("%Y-%m-%d %H-%M-%S")})') # add o horario atual 
        print(f'Posição atual: {"Comprado" if MaTrader.actual_trade_position else "Vendido"}')
        print(f'Balanço atual: {MaTrader.last_stock_account_balance} ({self.stock_code})')

        # executa a estrategia de media movel 
        ma_trade_decision = getMovingAvarageTradeStrategy(self.stock_data, self.operation_code)

        #executa a estrategia RSI
        #rsi_trade_decision = getRSIStrategy(self.stock_data, period=14)

        ####### AQUI CRIAR OUTRAS ESTRATEGIAS  #######

        # neste caso, a desição final será a mesma da media movel
        self.last_trade_desision = ma_trade_decision

        # se a posição for vendida (false) e a decisão for de compra (true), compra o ativo
        # se a posição for compra (true) e a decisão for de venda (false), vende o ativo
        if self.actual_trade_position == False and self.last_trade_desision == True:
            self.printStock()
            self.buyStock()
            time.sleep(2)
            self.updateAllData()
            self.printStock()

        elif self.actual_trade_position == True and self.last_trade_desision == False:
            self.printStock()
            self.sellStock()
            time.sleep(2)
            self.updateAllData()
            self.printStock()

        print('----------------------------------------------------------')


# --------------------------------------------------------------

MaTrader = BinanceTraderBot(STOCK_CODE, OPERATION_CODE, TRADED_QUANTITY, 100, CANDLE_PERIOD)

while(1):
    MaTrader.execute()
    time.sleep(60)