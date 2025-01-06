import talib
import numpy as np
from logger import Logger


LOG_FILE = 'bot_trader.log'
LOG_LEVEL='INFO'


logger_instance = Logger(name="Bot Trader", log_file=LOG_FILE, level=LOG_LEVEL)
logger = logger_instance.get_logger()

# Estratégias
def validate_data(data):
    """
    Valida os dados e preenche valores ausentes para evitar problemas nos cálculos.
    """
    if data.isnull().values.any():
        logger.warning("Dados contêm valores nulos. Realizando preenchimento com backward fill.")
        data = data.bfill()  # Usa bfill diretamente para preencher os valores ausentes
    return data


def moving_average_strategy(data, short_window=7, long_window=40):
    """
    Estratégia baseada em médias móveis.
    """
    try:
        data = validate_data(data)
        data['SMA_Short'] = talib.SMA(data['close'], timeperiod=short_window)
        data['SMA_Long'] = talib.SMA(data['close'], timeperiod=long_window)
        data['Signal_MA'] = np.where(data['SMA_Short'] > data['SMA_Long'], 1, 0)
        logger.info("Sinais da estratégia de médias móveis gerados com sucesso.")
        return data
    except Exception as e:
        logger.error(f"Erro na estratégia de médias móveis: {e}")
        return data

def rsi_strategy(data, rsi_period=14, overbought=70, oversold=30):
    """
    Estratégia baseada no Índice de Força Relativa (RSI).
    """
    try:
        data = validate_data(data)
        data['RSI'] = talib.RSI(data['close'], timeperiod=rsi_period)
        data['Signal_RSI'] = np.where(data['RSI'] < oversold, 1, 
                                      np.where(data['RSI'] > overbought, -1, 0))
        logger.info("Sinais da estratégia de RSI gerados com sucesso.")
        return data
    except Exception as e:
        logger.error(f"Erro na estratégia de RSI: {e}")
        return data

def breakout_strategy(data, window=10):
    """
    Estratégia baseada em breakout de máximas e mínimas.
    """
    try:
        data = validate_data(data)
        data['High_Max'] = data['high'].rolling(window=window).max()
        data['Low_Min'] = data['low'].rolling(window=window).min()
        data['Signal_Breakout'] = np.where(data['close'] > data['High_Max'], 1, 
                                           np.where(data['close'] < data['Low_Min'], -1, 0))
        logger.info("Sinais da estratégia de breakout gerados com sucesso.")
        return data
    except Exception as e:
        logger.error(f"Erro na estratégia de breakout: {e}")
        return data

def combine_signals(data):
    """
    Combina sinais de múltiplas estratégias em uma única coluna.
    """
    try:
        data['Combined_Signal'] = data[['Signal_MA', 'Signal_RSI', 'Signal_Breakout']].sum(axis=1)
        logger.info("Sinais combinados com sucesso.")
        return data
    except Exception as e:
        logger.error(f"Erro ao combinar sinais: {e}")
        return data

# Exemplo de uso
def apply_strategies(data):
    """
    Aplica todas as estratégias e combina os sinais.
    """
    try:
        data = moving_average_strategy(data)
        data = rsi_strategy(data)
        data = breakout_strategy(data)
        data = combine_signals(data)
        logger.info("Estratégias aplicadas com sucesso.")
        return data
    except Exception as e:
        logger.error(f"Erro ao aplicar estratégias: {e}")
        return data
