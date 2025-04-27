import time
import math
import csv
import os
import numpy as np
import talib
import logging
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
from pathlib import Path
from multiple import *
from gpt import *

# ========== Ayarlar ==========
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

API_KEY       = os.getenv("API_KEY")
API_SECRET    = os.getenv("API_SECRET")
TELEGRAM_URL  = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/sendMessage"
CHAT_ID       = os.getenv("TELEGRAM_CHAT_ID")

LEVERAGE      = 4           # Kaldıraç
POSITION_USDT = 10          # İşlem başı riske atılan USDT
RSI_PERIOD    = 14
OVERBOUGHT    = 70
OVERSOLD      = 30
TP_PCT        = 6           # %6 kâr hedefi
SL_PCT        = 1           # %3 zarar eşiği
BUFFER_PCT    = 0.1         # %0.1 buffer
SCAN_INTERVAL = 55          # saniye
HISTORY_LEN   = 110
LOG_LEVEL     = logging.INFO

EXPIRE_SECONDS = 5 * 60     # 5 dk sonra zorunlu kapanış

CSV_FILE = Path(__file__).parent / "trades.csv"

# ========== Kurulum ==========
logging.basicConfig(level=LOG_LEVEL,
                    format="%(asctime)s %(levelname)s: %(message)s")
client = Client(API_KEY, API_SECRET, {"timeout": 30})

open_positions = {}
insufficient_notified = False

# CSV başlıkları
if not CSV_FILE.exists():
    with open(CSV_FILE, "w", newline="") as f:
        csv.writer(f).writerow([
            "symbol","side","entry_time","entry_price","qty",
            "tp_price","sl_price","exit_time","exit_price",
            "exit_type","pnl"
        ])

def telegram(msg):
    logging.info("Telegram → " + msg)
    try:
        sess = Client(API_KEY, API_SECRET)._session
        sess.post(TELEGRAM_URL, json={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def round_price(raw, tick, ceil=False):
    factor = 1 / tick
    return (math.ceil(raw * factor) / factor) if ceil else (math.floor(raw * factor) / factor)

def safe_balance():
    """
    futures_account_balance() çağrısını -1021 hatasında
    önce zaman offset’ini güncelleyip retry eder.
    """
    try:
        return client.futures_account_balance()
    except BinanceAPIException as e:
        if e.code == -1021:
            st = client.futures_time()["serverTime"]
            lo = int(time.time() * 1000)
            client.timestamp_offset = lo - st
            logging.info(f"Resynced time offset: {client.timestamp_offset}ms")
            return client.futures_account_balance()
        raise

def scan_and_trade():
    global insufficient_notified

    now = time.time()

    # 0) Bakiye kontrolü
    bal = safe_balance()
    usdt_bal = next(float(b["balance"]) for b in bal if b["asset"]=="USDT")
    if usdt_bal < POSITION_USDT:
        if not insufficient_notified:
            telegram(f"Yetersiz bakiye: {usdt_bal:.2f} USDT. Bekleniyor.")
            insufficient_notified = True
        return
    insufficient_notified = False

    # 1) Exchange info ve semboller (sadece TRADING)
    info = client.futures_exchange_info()
    symbols = [
        s["symbol"] for s in info["symbols"]
        if s["contractType"]=="PERPETUAL"
           and s["quoteAsset"]=="USDT"
           and s["status"] == "TRADING"
    ]

    # 2) Açık pozisyonları güncelle & expire kontrolü
    for sym, pos in list(open_positions.items()):
        # 2a) Eğer 5 dk dolduysa zorunlu market kapanışı
        if now - pos["entry_time"] >= EXPIRE_SECONDS:
            side = SIDE_SELL if pos["side"]=="BUY" else SIDE_BUY
            qty  = pos["qty"]
            try:
                client.futures_create_order(
                    symbol=sym, side=side,
                    type=FUTURE_ORDER_TYPE_MARKET,
                    quantity=f"{qty:.8f}"
                )
                telegram(f"{sym}: 5dk doldu, market ile kapatıldı (qty={qty})")
            except Exception as e:
                logging.error(f"{sym}: expire kapatırken hata: {e}")

            # Kayıt, CSV, iptal
            exit_time  = now
            exit_price = float(client.futures_mark_price(symbol=sym)["markPrice"])
            exit_type  = "EXPIRE"
            pnl = ( (exit_price-pos["entry_price"]) if pos["side"]=="BUY"
                    else (pos["entry_price"]-exit_price) ) * qty
            with open(CSV_FILE, "a", newline="") as f:
                csv.writer(f).writerow([
                    sym, pos["side"], pos["entry_time"], pos["entry_price"], qty,
                    pos["tp_price"], pos["sl_price"],
                    exit_time, exit_price, exit_type, round(pnl,4)
                ])

            try:
                client.futures_cancel_all_open_orders(symbol=sym)
            except BinanceAPIException as e:
                if e.code != -2011:
                    logging.warning(f"{sym}: emir iptalinde hata: {e}")
            del open_positions[sym]
            continue

        # 2b) Pozisyon bilgisini al, kapandıysa temizle
        pinfo = client.futures_position_information(symbol=sym)
        raw = next((x["positionAmt"] for x in pinfo if float(x["positionAmt"]) != 0), None)
        if raw is None:
            try:
                client.futures_cancel_all_open_orders(symbol=sym)
            except BinanceAPIException as e:
                if e.code != -2011:
                    logging.warning(f"{sym}: emir iptalinde hata: {e}")
            del open_positions[sym]
            continue

        amt = float(raw)
        if amt == 0:
            # SL/TP tetiklenmiş → rapor, CSV, Telegram
            exit_time  = now
            exit_price = float(client.futures_mark_price(symbol=sym)["markPrice"])
            if pos["side"]=="BUY":
                exit_type = "TP" if exit_price>=pos["tp_price"] else "SL"
                pnl = (exit_price - pos["entry_price"]) * pos["qty"]
            else:
                exit_type = "TP" if exit_price<=pos["tp_price"] else "SL"
                pnl = (pos["entry_price"] - exit_price) * pos["qty"]

            with open(CSV_FILE, "a", newline="") as f:
                csv.writer(f).writerow([
                    sym, pos["side"], pos["entry_time"], pos["entry_price"], pos["qty"],
                    pos["tp_price"], pos["sl_price"],
                    exit_time, exit_price, exit_type, round(pnl,4)
                ])
            telegram(f"{sym}: {exit_type} kapandı. PnL={pnl:.4f}")

            try:
                client.futures_cancel_all_open_orders(symbol=sym)
            except BinanceAPIException as e:
                if e.code != -2011:
                    logging.warning(f"{sym}: emir iptalinde hata: {e}")
            del open_positions[sym]

    # 3) Yeni sinyal arama
    for sym in symbols:
        if sym in open_positions:
            continue

        # 3a) Kline al
        try:
            klines = client.futures_klines(
                symbol=sym,
                interval=Client.KLINE_INTERVAL_1MINUTE,
                limit=HISTORY_LEN
            )
        except Exception as e:
            logging.warning(f"{sym}: kline atlandı ({e})")
            continue

        closes = np.array([float(x[4]) for x in klines])
        highs  = np.array([float(x[2]) for x in klines])
        lows   = np.array([float(x[3]) for x in klines])
        vols   = np.array([float(x[5]) for x in klines])

        # 3b) Sinyal
        signal = rsi_macd_ema_triple_strategy(closes, highs, lows, vols)
        
        if not signal:
            signal = rsi_macd_confirm_strategy(closes, highs, lows, vols)
     
        if not signal:
            signal = rsi_ema_trend_strategy(closes, highs, lows, vols)
            
        if not signal:
            continue
        # 3c) Güncel mark fiyat
        try:
            mark = float(client.futures_mark_price(symbol=sym)["markPrice"])
        except:
            continue

        # 3d) MarginType ve leverage
        try:
            client.futures_change_margin_type(symbol=sym, marginType="ISOLATED")
        except BinanceAPIException as e:
            if e.code != -4046:
                logging.error(f"{sym}: marginType hatası: {e}")
                continue
        try:
            client.futures_change_leverage(symbol=sym, leverage=LEVERAGE)
        except BinanceAPIException as e:
            logging.error(f"{sym}: leverage hatası: {e}")
            continue

        # 3e) Lot ve fiyat adımlarını çıkar
        sinfo = next(x for x in info["symbols"] if x["symbol"]==sym)
        lot = float(next(f for f in sinfo["filters"] if f["filterType"]=="LOT_SIZE")["stepSize"])
        qty_prec  = abs(int(math.log10(lot)))
        tick      = float(next(f for f in sinfo["filters"] if f["filterType"]=="PRICE_FILTER")["tickSize"])
        price_prec= abs(int(math.log10(tick)))

        raw_qty = (POSITION_USDT/mark)*LEVERAGE
        qty     = round(math.floor(raw_qty/lot)*lot, qty_prec)
        if qty <= 0:
            continue

        side = SIDE_BUY if signal=="BUY" else SIDE_SELL
        opp  = SIDE_SELL if side==SIDE_BUY else SIDE_BUY

        # 3f) Pozisyon aç
        try:
            client.futures_create_order(
                symbol=sym, side=side,
                type=FUTURE_ORDER_TYPE_MARKET,
                quantity=f"{qty:.{qty_prec}f}"
            )
        except BinanceAPIException as e:
            logging.warning(f"{sym}: opening order failed ({e}), atlanıyor")
            continue
        telegram(f"{sym}: {signal} açıldı, qty={qty}")

        entry_time  = now
        entry_price = mark

        # 4) TP/SL hesap & buffer
        price_target_pct = TP_PCT / LEVERAGE
        price_stop_pct   = SL_PCT / LEVERAGE
        if side == SIDE_BUY:
            raw_tp = entry_price * (1 + price_target_pct/100)
            raw_sl = entry_price * (1 - price_stop_pct/100)
        else:
            raw_tp = entry_price * (1 - price_target_pct/100)
            raw_sl = entry_price * (1 + price_stop_pct/100)

        # buffer
        if side==SIDE_BUY and raw_sl>=mark:
            raw_sl = mark*(1-BUFFER_PCT/100)
        if side==SIDE_SELL and raw_sl<=mark:
            raw_sl = mark*(1+BUFFER_PCT/100)
        if side==SIDE_BUY and raw_tp<=mark:
            raw_tp = mark*(1+BUFFER_PCT/100)
        if side==SIDE_SELL and raw_tp>=mark:
            raw_tp = mark*(1-BUFFER_PCT/100)

        sl_price = round_price(raw_sl, tick, ceil=False)
        tp_price = round_price(raw_tp, tick, ceil=True)

        # SL emri
        try:
            o = client.futures_create_order(
                symbol=sym, side=opp,
                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                stopPrice=f"{sl_price:.{price_prec}f}",
                closePosition=True
            )
            sl_oid = o["orderId"]
            telegram(f"{sym}: SL @ {sl_price}")
        except Exception as e:
            sl_oid = None
            logging.info(f"{sym}: SL atlandı ({e})")

        # TP emri
        try:
            o = client.futures_create_order(
                symbol=sym, side=opp,
                type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                stopPrice=f"{tp_price:.{price_prec}f}",
                closePosition=True
            )
            tp_oid = o["orderId"]
            telegram(f"{sym}: TP @ {tp_price}")
        except Exception as e:
            tp_oid = None
            logging.info(f"{sym}: TP atlandı ({e})")

        # 5) Açık pozisyon kaydet
        open_positions[sym] = {
            "entry_time": entry_time,
            "entry_price": entry_price,
            "side": signal,
            "qty": qty,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "tp_order_id": tp_oid,
            "sl_order_id": sl_oid
        }

def main():
    logging.info("Program başladı")
    while True:
        try:
            scan_and_trade()
        except Exception as e:
            logging.error("Genel hata: %s", e, exc_info=True)
        time.sleep(SCAN_INTERVAL)

if __name__=="__main__":
    main()
