import asyncio
from binance.client import AsyncClient
import time

api_key = ''
api_secret = ''

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
        print(f"{symbol}: {side} işlem açma hatası - {e}")

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
        print(f"{symbol}: {side} işlem açma hatası - {e}")
        return None

async def get_open_positions(client):
    try:
        open_positions = await client.futures_position_information()

        if not any(abs(float(position['positionAmt'])) > 0 for position in open_positions):
            print("Herhangi bir açık pozisyon bulunmuyor.")
            print("-" * 50)
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
                print(f"Coin : {symbol}")
                print(f"💰 Anlık Profit : {unrealized_profit_with_wallet}")
                print("-" * 50)


    except Exception as e:
        print(f"Hata: {e}")

async def get_account_info(client):
    try:
        account_info = await client.futures_account()

        total_balance = float(account_info['totalWalletBalance'])
        available_balance = float(account_info['availableBalance'])
        total_balance = round(total_balance,2)
        available_balance = round(available_balance,2)

        print(f"💰 Toplam Bakiye : {total_balance}$")
        print(f"💰 Kullanılabilir Bakiye : {available_balance}$")
        print("-" * 50)

        
    except Exception as e:
        print(f"Hata: {e}")

async def process_symbol(client, symbol):
    klines = await client.futures_klines(symbol=symbol, interval='1m', limit=2)
    current_price = float(klines[1][4])
    previous_price = float(klines[0][4])
    price_change_percent = ((current_price - previous_price) / previous_price) * 100

    # Kaldıraç bilgisini al
    account_info = await client.futures_account()
    for position in account_info['positions']:
        leverage = int(position['leverage'])

    # Short işlem açma
    if price_change_percent > 1 :
        print(f"💰 {symbol} ")
        print(f"Giriş Fiyat : {current_price}$ ")
        print(f"Değişim : 🔴%{abs(price_change_percent):.2f} ")
        quantity = 120 / current_price
        quantity = round(quantity, 0)
        usdt = ( quantity * current_price ) / 20
        print(f"Çarpan : {leverage}x")
        print(f"{usdt}$ işlem açıldı.")
        print("-" * 50)
        await islem_acma(client, symbol, "SELL", quantity)
        
        # Profit ile kapatma
        price = current_price * 0.995
        price = round(price, 4)
        await islem_kapatma(client, symbol, "BUY", price , quantity)
        
    # Long işlem açma
    elif price_change_percent < -1 :
        print(f"💰 {symbol} ")
        print(f"Giriş Fiyat : {current_price}$ ")
        print(f"Değişim : 🟢%{abs(price_change_percent):.2f} ")
        quantity = 120 / current_price
        quantity = round(quantity, 0)
        usdt = ( quantity * current_price ) / 20
        print(f"Çarpan : {leverage}x")
        print(f"{usdt}$ işlem açıldı.")
        print("-" * 50)    
        await islem_acma(client, symbol, "BUY", quantity)
        
        # Profit ile kapatma
        price = current_price * 1.005
        price = round(price, 4)
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
        await asyncio.sleep(60)
        
    await client.close_connection()
    


asyncio.run(main())
