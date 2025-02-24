import ccxt
import time
from telegram import Bot
import asyncio
from aiogram import Bot as AiogramBot
from telegram.constants import ParseMode

# Binance API anahtarlarınızı buraya ekleyin
api_key = ''
api_secret = ''

# Telegram bot token'ınızı buraya ekleyin
telegram_token = ''
telegram_chat_id = ''

# Binance bağlantısı oluştur
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
})

telegram_bot = AiogramBot(token=telegram_token)

async def send_telegram_message(message):
    try:
        await telegram_bot.send_message(chat_id=telegram_chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
        print("Telegram message sent successfully.")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

async def fetch_futures_symbols_1m_candles(symbol):
    try:
        candles = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=2)
        if len(candles) >= 2:
            price_change = ((candles[1][4] - candles[0][4]) / candles[0][4]) * 100.0
            if price_change > 1 or price_change < -1 :
                message = f"Coin Adı : {symbol}, Değişim Oranı : {price_change:.2f}%"
                print(message)
                await send_telegram_message(message)
        else:
            print(f"Coin Adı : {symbol}, Hesaplanamadı")
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
            if elapsed_time >= 1:
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