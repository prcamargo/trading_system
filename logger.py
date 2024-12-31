import logging
from datetime import datetime

# Define logger
logging.basicConfig(
    filename = 'logs/trading_bot.log',
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s'
)


def createLogOrder(order):
    side = order['side']
    type = order['type']
    quantity = order['quantity']
    asset = order['symbol']
    price_per_unit = order['fills'][0]['price']
    currency = order['fills'][0]['commissionAsset']
    total_value = order['cummulativeQuoteQty']
    timestamp = order['transactTime']

    # convertendo timestamp para data/hora legivel
    datatime_transact = datetime.utcfromtimestamp(timestamp / 1000).strftime('(%H:%M:%S) %Y-%m-%d')

    log_message = (
        '\n------------------------\n'
        "ORDEM EXECUTADA: \n"
        f"Side: {side}\n"
        f"Ativo: {asset}\n"
        f"Quantidade: {quantity}\n"
        f"Valor no momento: {price_per_unit}\n"
        f"Moeda: {currency}\n"
        f"Valor em {currency}: {total_value}\n"
        f"Type: {type}\n"
        f"Data/Hora: {datatime_transact}\n"
        "\n"
        "Complete_order:\n"
        f"{order}"
        '\n------------------------\n'
    )

    print_message = (
        '\n------------------------\n'
        "ORDEM EXECUTADA: \n"
        f"Side: {side}\n"
        f"Ativo: {asset}\n"
        f"Quantidade: {quantity}\n"
        f"Valor no momento: {price_per_unit}\n"
        f"Moeda: {currency}\n"
        f"Valor em {currency}: {total_value}\n"
        f"Type: {type}\n"
        f"Data/Hora: {datatime_transact}\n"
        #"\n"
        #"Complete_order:\n"
        #f"{order}
        '\n------------------------\n'
    )

    print(print_message)

    logging.info(log_message)