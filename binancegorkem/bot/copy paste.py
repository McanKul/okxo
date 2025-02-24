from binance.client import Client
import time

api_key = ''
api_secret = ''
client = Client(api_key, api_secret)

def get_account_info():
    try:
        account_info = client.futures_account()

        total_balance = float(account_info['totalWalletBalance'])
        available_balance = float(account_info['availableBalance'])
        total_balance = round(total_balance,2)
        available_balance = round(available_balance,2)

        print(f"💰 Toplam Bakiye : {total_balance}$")
        print(f"💰 Kullanılabilir Bakiye : {available_balance}$")
        print("-" * 50)

        
    except Exception as e:
        print(f"Hata: {e}")



def get_open_positions():
    try:
        open_positions = client.futures_position_information()

        if not any(abs(float(position['positionAmt'])) > 0 for position in open_positions):
            print("Açık pozisyon bulunmuyor.")
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


def open_trade(symbol, side, quantity):
    try:
        order = client.futures_create_order(
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

def close_trade(symbol, side, price, quantity):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="LIMIT",
            price = price,
            quantity=quantity,
            timeInForce="GTC"
        )
        print(f"{symbol}: {side} Emir verildi - ID: {order['orderId']}")
        return order['orderId']  # İşlem ID'sini döndür

    except Exception as e:
        print(f"{symbol}: {side} işlem açma hatası - {e}")
        return None



# Ana döngü
while True:
    try: 
        
        get_account_info()
        get_open_positions()



        
        exchange_info = client.futures_exchange_info()

        for symbol_info in exchange_info['symbols']:
            symbol = symbol_info['symbol']

            klines = client.futures_klines(symbol=symbol, interval='1m', limit=2)
            current_price = float(klines[1][4])
            previous_price = float(klines[0][4])
            price_change_percent = ((current_price - previous_price) / previous_price) * 100
            
            #Haberciler 
            
            if price_change_percent > 0.01 :
                print(f"💰 {symbol} ")
                print(f" Değişim : 🔴%{abs(price_change_percent):.2f} ")
                print("-" * 50)
            elif price_change_percent < -0.01 :
                print(f"💰 {symbol} ")           
                print(f" Değişim : 🟢-%{abs(price_change_percent):.2f} ")
                print("-" * 50)
                
            #SELL
            

                
                
            if price_change_percent > 0.8 :
                print(f"💰 {symbol} ")
                print(f" Değişim : 🔴%{abs(price_change_percent):.2f} ")
                quantity = 120 / current_price
                quantity = round(quantity, 0)
                usdt = ( quantity * current_price ) / 20
                print(f"{usdt} dolar işlem açıldı.")
                print("-" * 50)
                open_trade(symbol, "SELL", quantity)
                
            #Kar alma yeri
            
                price = current_price * 0.995
                price = round(price, 4)
                close_trade(symbol, "BUY", price , quantity)
                
            #BUY
                
            elif price_change_percent < -0.8 :
                print(f"💰 {symbol} ")
                print(f" Değişim : 🟢-%{abs(price_change_percent):.2f} ")
                quantity = 120 / current_price
                quantity = round(quantity, 0)
                usdt = ( quantity * current_price ) / 20
                print(f"{usdt} dolar işlem açıldı.")
                print("-" * 50)
                open_trade(symbol, "BUY", quantity)
            
            #Kar alma yeri

                price = current_price * 1.005
                price = round(price, 4)
                close_trade(symbol, "SELL", price , quantity)

                
    except Exception as e:
        print(f"Hata: {e}")