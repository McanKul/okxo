import asyncio
from binance.client import AsyncClient
import time



api_key = ''
api_secret = ''

async def open_trade(client, symbol, side, quantity):
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
        
async def close_trade(client, symbol, side, price, quantity):
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
    open_positions = await client.futures_position_information()
    return [position['symbol'] for position in open_positions if abs(float(position['positionAmt'])) > 0]

async def process_symbol(client, symbol):
    klines = await client.futures_klines(symbol=symbol, interval='1m', limit=2, timeout = 10)
    current_price = float(klines[1][4])
    previous_price = float(klines[0][4])
    price_change_percent = ((current_price - previous_price) / previous_price) * 100
    
    
    


    if price_change_percent > 0.1:
        print(f"💰 {symbol} ")
        print(f" Değişim : 🔴%{abs(price_change_percent):.2f} ")
        open_positions = await get_open_positions(client)
        if symbol in open_positions:
            print(f"{symbol}: Açık pozisyon bulundu, işlem açılmıyor.")
            return
        else:
            #SHORT İŞLEM AÇMA PARAMETRELERİ
            quantity = 120 / current_price
            quantity = round(quantity, 0)
            usdt = ( quantity * current_price ) / 20
            usdt = round (usdt,2)
            print(f"{usdt} dolar işlem açıldı.")
            print("-" * 50)
            await open_trade(client, symbol, "SELL", quantity)
            
            #Kar alma yeri
            price = current_price * 0.995
            price = round(price, 4)
            await close_trade(client, symbol, "BUY", price , quantity)
            
    if price_change_percent < -0.1:
        print(f"💰 {symbol} ")
        print(f" Değişim : 🟢-%{abs(price_change_percent):.2f} ")
        open_positions = await get_open_positions(client)
        if symbol in open_positions:
            print(f"{symbol}: Açık pozisyon bulundu, işlem açılmıyor.")
            return
        else:
            #LONG İŞLEM AÇMA PARAMETRELERİ
            quantity = 120 / current_price
            quantity = round(quantity, 0)
            usdt = ( quantity * current_price ) / 20
            usdt = round (usdt,2)
            print(f"{usdt} dolar işlem açıldı.")
            print("-" * 50)
            await open_trade(client,symbol, "BUY", quantity)

            
            #Kar alma yeri
            price = current_price * 0.1005
            price = round(price, 4)
            await close_trade(client, symbol, "SELL", price , quantity)
        
Forever = True

async def main():
    client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
    exchange_info = await client.futures_exchange_info()
    symbols = [symbol_info['symbol'] for symbol_info in exchange_info['symbols']]

    while Forever == True:
    
        tasks = []
        for symbol in symbols:
            tasks.append(process_symbol(client, symbol))

        await asyncio.gather(*tasks)
        await asyncio.sleep(20)
        
    await client.close_connection()

asyncio.run(main())
