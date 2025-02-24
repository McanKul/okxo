import ccxt
import time
from telegram import Bot
import asyncio
from aiogram import Bot as AiogramBot
from telegram.constants import ParseMode
from binance.client import Client



# Binance API anahtarlarınızı buraya ekleyin
api_key = ''
api_secret = ''

client = Client(api_key=api_key, api_secret=api_secret, testnet=False)


 
 
account_info = client.futures_account()
            
for position in account_info['positions']:
    symbol = position['symbol']
    leverage = int(position['leverage'])
    print(symbol,leverage)