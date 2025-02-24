import ccxt
import time
from telegram import Bot
import asyncio
from aiogram import Bot as AiogramBot
from telegram.constants import ParseMode
from binance.client import Client
import binance

# Binance API anahtarlarınızı buraya ekleyin
api_key = ''
api_secret = ''

client = Client(api_key=api_key, api_secret=api_secret, testnet=False)

# Telegram bot token'ınızı buraya ekleyin
telegram_token = ''
telegram_chat_id = ''

# Binance bağlantısı oluştur
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
})
exchange.load_markets()



telegram_bot = AiogramBot(token=telegram_token)
account_info = client.futures_account()
exchange_info = client.get_exchange_info()

dollar_amount = 5



async def send_telegram_message(message):
    try:
        await telegram_bot.send_message(chat_id=telegram_chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
        print("Telegrama mesajı gönderdim..")
    except Exception as e:
        print(f"Telegrama mesajı gönderemiyorum: {e}")
        
        
def calculate_quantity(symbol, dollar_amount):
    try:
        market_price = get_market_price(symbol)
        if market_price is not None:
            quantity = dollar_amount / market_price
            return quantity
        else:
            print(f"Market fiyatı alınamadı for symbol: {symbol}")
            return None
    except binance.exceptions.BinanceAPIException as e:
        print(f"Geçersiz sembol ({symbol}): {e}")
        return None
        
        
def get_market_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])
               
        
def create_market_order(symbol, side, quantity, leverage):

    try:
        response = exchange.fapiPrivatePostOrder({
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',  # Piyasa emri
            'quantity': quantity,
            'leverage': leverage,
        })
        print(response)
    except ccxt.NetworkError as e:
        print(f"NetworkError: {e}")
    except ccxt.ExchangeError as e:
        print(f"ExchangeError: {e}")
    

async def fetch_futures_symbols_1m_candles(symbol):
    try:

        
        candles = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=2)
        if len(candles) >= 2:
            price_change = ((candles[1][4] - candles[0][4]) / candles[0][4]) * 100.0
            if price_change > 0.1 or price_change < -0.1:
                message = f"Symbol: {symbol}, Last 1 Minute Price Change: {price_change:.2f}%"

                if price_change > 0.1:
                    # %1 ve üzeri yükseliş durumu
                    message += "\nShort Pozisyonu açtım"
                        # Burada SHORT pozisyon açma işlemini gerçekleştirin

                    side = 'SELL' 
                    quantity = calculate_quantity(symbol, dollar_amount)
                    leverage = 20  # Kaldıraç

                    create_market_order(symbol, side, quantity, leverage)
                        
                    
                        # İşlem açıldığında bildir

                        
                elif price_change < -0.1:
                    # %1 ve üzeri düşüş durumu
                    message += "\nLong Pozisyonu açtım"
                    # Burada LONG pozisyon açma işlemini gerçekleştirin
                    side = 'BUY' 
                    quantity = calculate_quantity(symbol, dollar_amount)
                    leverage = 20  # Kaldıraç

                    create_market_order(symbol, side, quantity, leverage)

                    # İşlem açıldığında bildir


                print(message)
        else:
            print(f"Symbol: {symbol}, Not enough data for calculation")
    except ccxt.NetworkError as e:
        print(f"NetworkError: {e}")
    except ccxt.ExchangeError as e:
        print(f"ExchangeError: {e}")

async def main():
    try:
        markets = exchange.fapiPublicGetExchangeInfo()
        symbols = [market['symbol'] for market in markets['symbols'] if market['quoteAsset'] == 'USDT']

        start_time = time.time()

        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time >= 5:
                for symbol in symbols:
                    await fetch_futures_symbols_1m_candles(symbol)

                start_time = time.time()

            await asyncio.sleep(1)
    except ccxt.NetworkError as e:
        print(f"NetworkError: {e}")
    except ccxt.ExchangeError as e:
        print(f"ExchangeError: {e}")

if __name__ == '__main__':
    asyncio.run(main())
