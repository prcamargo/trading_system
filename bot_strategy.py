import pandas as pd

###################### ESTRATEGIAS ######################
# executa a estrategia de media movel
def getMovingAvarageTradeStrategy(stock_data, operation_code,fast_window = 7, slow_window = 40):

    #calcula as medias moveis rapida e lenda
    stock_data['ma_fast'] = stock_data['close_price'].rolling(window=fast_window).mean() # media rapida
    stock_data['ma_slow'] = stock_data['close_price'].rolling(window=slow_window).mean() # media lenta

    # pega as ultimas moving average
    last_ma_fast = stock_data['ma_fast'].iloc[-1] # iloc[-1] pega o ultimo dado do array
    last_ma_slow = stock_data['ma_slow'].iloc[-1]

    #toma a decisão, baseada na posição da media movel 
    # (false = vender | true = comprar)
    if last_ma_fast > last_ma_slow:
        ma_trade_decision = True # compra
    else:
        ma_trade_decision = False

    #print('----------------------------------------------------------')
    print('Estratégia executada: Moving Average')
    print(f'{operation_code}\n | {last_ma_fast:.3f} = Última Média Rápida \n | {last_ma_slow:.3f} = Última Média Lenta')
    print(f'Decisao de posição: {"Comprar " if ma_trade_decision == True else "Vender"}')
    print('----------------------------------------------------------')

    return ma_trade_decision;

#executa estrategia RSI
def getRSIStrategy(stock_data, period=14):
    delta = stock_data['close_price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    rsi_value = rsi.iloc[-1]

    if rsi_value > 70:
        print(f'RSI: {rsi_value:.2f} -> Overbought -> Sell Signal')
        return False  # Sell
    elif rsi_value < 30:
        print(f'RSI: {rsi_value:.2f} -> Oversold -> Buy Signal')
        return True  # Buy
    else:
        print(f'RSI: {rsi_value:.2f} -> Neutral')
        return None  # No action
