import asyncio
from binance.client import AsyncClient
import time
from telegram import Bot
from aiogram import Bot as AiogramBot
from telegram.constants import ParseMode


api_key = ''
api_secret = ''


telegram_token = ''
telegram_chat_id = ''

telegram_bot = AiogramBot(token=telegram_token)

async def send_telegram_message(message):
    try:
        await telegram_bot.send_message(chat_id=telegram_chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

async def islem_acma(client, symbol, side, quantity):
    try:
        order = await client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity,
            timestamp=int(time.time() * 1000),
            newOrderRespType="RESULT"
        )
        print(f"{symbol}: {side} işlem açıldı - ID: {order['orderId']}")
    except Exception as e:
        hata = f"{symbol}: {side} işlem açma hatası - {e}"
        print(hata)
        send_telegram_message(hata)

async def islem_kapatma(client, symbol, side, price, quantity):
    try:
        order = await client.futures_create_order(
            symbol=symbol,
            side=side,
            type="LIMIT",
            price=price,
            quantity=quantity,
            timeInForce="GTC"
        )
        print(f"{symbol}: {side} Emir verildi - ID: {order['orderId']}")
        return order['orderId']  # İşlem ID'sini döndür
    except Exception as e:
        hata = f"{symbol}: {side} işlem açma hatası - {e}"
        print(hata)
        send_telegram_message(hata)

        return None

async def get_open_positions(client):
    try:
        open_positions = await client.futures_position_information()
        if not any(abs(float(position['positionAmt'])) > 0 for position in open_positions):
            açık_pozisyon_yok_message = "Herhangi bir açık pozisyon bulunmuyor."           
            print(açık_pozisyon_yok_message)           
            await send_telegram_message(açık_pozisyon_yok_message)    
            return []
        print("Açık pozisyonlar:")
        for position in open_positions:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            mark_price = float(position['markPrice'])
            isolated_wallet = float(position['isolatedWallet'])
            if abs(position_amt) > 0:
                unrealized_profit = (mark_price - entry_price) * position_amt
                unrealized_profit_with_wallet = unrealized_profit + isolated_wallet
                unrealized_profit_with_wallet = round(unrealized_profit_with_wallet, 2)
                açık_pozisyon_message = f"Coin : {symbol} \n💰 Anlık Profit : {unrealized_profit_with_wallet}"
                await send_telegram_message(açık_pozisyon_message)
    except Exception as e:
        hata = f"Hata: {e}"
        print(hata)
        send_telegram_message(hata)

async def get_account_info(client):
    try:
        account_info = await client.futures_account()
        total_balance = float(account_info['totalWalletBalance'])
        available_balance = float(account_info['availableBalance'])
        total_balance = round(total_balance,2)
        available_balance = round(available_balance,2)
        toplam_bakiye_message = f"💰 Toplam Bakiye : {total_balance}$ \n💰 Kullanılabilir Bakiye : {available_balance}$"    
        print(toplam_bakiye_message)    
        await send_telegram_message(toplam_bakiye_message)
    except Exception as e:
        hata = f"Hata: {e}"
        print(hata)
        send_telegram_message(hata)

async def process_symbol(client, symbol):
    klines = await client.futures_klines(symbol=symbol, interval='5m', limit=2)
    current_price = float(klines[1][4])
    previous_price = float(klines[0][4])
    price_change_percent = ((current_price - previous_price) / previous_price) * 100

    # Kaldıraç bilgisini al
    account_info = await client.futures_account()
    for position in account_info['positions']:
        leverage = int(position['leverage'])

    # Short işlem açma

    if price_change_percent > 5 :


        quantity = 100 / current_price
        quantity = round(quantity, 0)
        usdt = ( quantity * current_price ) / 20
        await islem_acma(client, symbol, "SELL", quantity)
        sembol_message = f"💰 {symbol} \nGiriş Fiyat : {current_price}$ \nDeğişim : 🔴%{abs(price_change_percent):.2f} \nÇarpan : {leverage}x \n{usdt}$ işlem açıldı."
        print(sembol_message)
        await send_telegram_message(sembol_message)      
        # Profit ile kapatma

        price = current_price * 0.5
        price = round(price, 4)
        print(price)
        await islem_kapatma(client, symbol, "BUY", price , quantity)
        
    # Long işlem açma

    elif price_change_percent < -5 :
     
        
        quantity = 100 / current_price
        quantity = round(quantity, 0)
        usdt = ( quantity * current_price ) / 20
        await islem_acma(client, symbol, "BUY", quantity)
        sembol_message =f"💰 {symbol} \nGiriş Fiyat : {current_price}$ \nDeğişim : 🟢%{abs(price_change_percent):.2f} \nÇarpan : {leverage}x \n{usdt}$ işlem açıldı. "
        print(sembol_message)
        await send_telegram_message(sembol_message)   
        # Profit ile kapatma

        price = current_price * 1.5
        price = round(price, 4)
        print(price)
        await islem_kapatma(client, symbol, "SELL", price , quantity)

async def main():
    client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
    exchange_info = await client.futures_exchange_info()
    symbols = [symbol_info['symbol'] for symbol_info in exchange_info['symbols']]

    while True:      
        tasks = []
        for symbol in symbols:
            tasks.append(process_symbol(client, symbol))
        await asyncio.gather(*tasks)
        await get_account_info(client)
        await get_open_positions(client)
        await asyncio.sleep(90)
        
    await client.close_connection()
    


asyncio.run(main())
