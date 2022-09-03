import requests
import pandas as pd
from binance.client import Client
from binance.helpers import round_step_size
import info
import math
import asyncio
from discord.ext import commands
import discord
import logging
client = Client(api_key=info.api, api_secret=info.secret_api, testnet=False)
DS = commands.Bot(command_prefix='~', intents = discord.Intents(messages = True, guild_messages = True, members = True, guilds = True))
DS.remove_command("help")
logging.basicConfig(filename="logs.txt", level=logging.DEBUG, format="%(asctime)s %(message)s")
data = []

all_orders = 0
opened_orders = 0
take_orders = 0
stop_orders = 0

def get_pricesize(symbol):
    info = client.futures_exchange_info()
    for item in info['symbols']:
        if(item['symbol'] == symbol):
            for f in item['filters']:
                if f['filterType'] == 'PRICE_FILTER':
                    return f['tickSize']

def get_qsize(symbol):
    info = client.futures_exchange_info()
    for item in info['symbols']:
        if(item['symbol'] == symbol):
            for f in item['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    return f['stepSize']
def BalanceUSDT():
    try:
        b=client.futures_account_balance()
        b = pd.DataFrame.from_dict(b)
        b = b.loc[b['asset']=='USDT']
        balance_USDT = float(b['balance'].values)
    except:
        balance_USDT=0
    return balance_USDT

def get_price(symbol, prices):
        for price in prices:
            if symbol == price['symbol']:
                return price['price']

allbal = BalanceUSDT()
trading_bal = {}
tokens = info.tokens
token_len = len(info.tokens)
token_bal = math.floor(allbal/token_len)
for i in range(token_len):
    trading_bal[tokens[i]] = token_bal

bal = BalanceUSDT()
logging.debug(trading_bal)
print("ready")
@DS.event
async def on_message(ctx):
    for i in info.tokens:
        try:
            client.futures_change_margin_type(symbol=i, marginType='ISOLATED')
        except:
            continue
    logging.debug(ctx.content)
    ch = ctx.channel.id
    if ctx.author != DS.user and ch == 1009370759979868260 and ctx.content != '!stat' and ctx.content != '!balance':
        global data
        global all_orders
        global opened_orders
        global take_orders
        global stop_orders
        global trading_bal
        logging.debug(trading_bal)
        await ctx.channel.send(":white_check_mark:сигнал принят!:white_check_mark: ")
        rawdata = ctx.content
        rawdata = rawdata.split()
        data = rawdata
        logging.debug(data)
        side = data[0]
        symbol = data[1]
        symbol = symbol.replace("PERP", "")
        price = data[2]
        stopl = data[3]
        takep = data[4]
        sl_cof = float(data[5])
        if tokens.count(symbol) != 0:
            logging.debug(symbol)
            price_size = get_pricesize(symbol)
            price = round_step_size(float(price), float(price_size))
            stopl = round_step_size(float(stopl), float(price_size))
            takep = round_step_size(float(takep), float(price_size))
            if side == "BUY" and client.futures_get_open_orders(symbol=symbol) == []:
                new_stop_trigger = price * 1.06
                startbal = trading_bal[symbol]
                try:
                    q_size = get_qsize(symbol)
                    q = trading_bal.get(symbol) / price
                    q = q * info.laverage
                    if q_size == '1':
                        q = int(q)
                    else:
                        q = round_step_size(q, q_size)
                    logging.debug('info: ' + side + ' ' + symbol + ' ' + str(price) + ' ' + str(stopl) + ' ' + str(takep) + ' ' + str(q))
                    client.futures_change_leverage(symbol=symbol, leverage=info.laverage)
                    buyorder = client.futures_create_order(symbol=symbol, side=side, type="LIMIT", price=price, quantity=q, timeInForce="GTC", isIsolated='TRUE')
                    stop = client.futures_create_order(symbol=symbol, side="SELL", type="STOP_MARKET", stopPrice=stopl, closePosition="true")
                    take = client.futures_create_order(symbol=symbol, side="SELL", type="TAKE_PROFIT_MARKET", stopPrice=takep, closePosition="true")
                    embed = discord.Embed(color=discord.Color.green(), title=":money_with_wings:Сделка открыта!:money_with_wings:")
                    embed.add_field(name=":coin:Монета:coin:", value=f'{symbol}')
                    embed.add_field(name="Позиция:", value=f'{side}')
                    embed.add_field(name="Количество:", value=f'{q}')
                    embed.add_field(name=":moneybag:Цена открытия:moneybag:", value=f'{price} :money_with_wings:')
                    embed.add_field(name=":no_entry_sign:стоп-лосс:no_entry_sign:", value=f'{stopl}')
                    embed.add_field(name=":money_mouth:тейк-профит:money_mouth: ", value=f'{takep}')
                    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1009370759979868260/986256233579302922/5271665807120666932.jpeg")
                    embed.set_footer(text=f"bot v.{info.bot_version}")
                    channel = DS.get_channel(1009370759979868260)
                    await channel.send(embed=embed)
                    all_orders = all_orders + 1
                    opened_orders = opened_orders + 1
                    a = True
                except Exception as e :
                    logging.ERROR("Ошибка открытия: ",e)
                    await ctx.channel.send(content=f":red_circle:Ошибка открытия! ({e}):red_circle:")
                    a = False
                while a == True:
                    orders = client.futures_get_open_orders(symbol=symbol)
                    if len(orders) == 2 or len(orders) == 3:
                        prices = requests.get('https://api.binance.com/api/v3/ticker/price').json()
                        sym_price = get_price(symbol, prices)
                        if float(sym_price)>= new_stop_trigger:
                            stop_price = new_stop_trigger*sl_cof
                            stop_price = new_stop_trigger - stop_price
                            new_stop_trigger = new_stop_trigger * 1.06
                            stop_price = round_step_size(float(stop_price), float(price_size))
                            client.futures_cancel_order(symbol=symbol, orderId=stop['orderId'], timestamp='true')
                            stop = client.futures_create_order(symbol=symbol, side="SELL", type="STOP_MARKET", stopPrice=stop_price, closePosition="true")
                        await asyncio.sleep(60)
                    else:
                        try:
                            client.futures_cancel_order(symbol=symbol, orderId=stop['orderId'], timestamp='true')
                            channel = DS.get_channel(1009370759979868260)
                            logging.debug(orders)
                            await channel.send(content=f":dollar:Позиция на монету {symbol} закрыта по тейк-профиту!:dollar:")
                            take_orders = take_orders + 1
                            opened_orders = opened_orders - 1
                            d1 = startbal*info.laverage
                            d2 = takep/price
                            d3 = d2 - 1
                            d4 = d1 * d3
                            d5 = d4 + startbal - 0.1
                            trading_bal[symbol] = d5
                            a = False
                        except:
                            client.futures_cancel_order(symbol=symbol, orderId=take['orderId'], timestamp='true')
                            channel = DS.get_channel(1009370759979868260)
                            logging.debug(orders)
                            await channel.send(content=f":red_circle:Позиция на монету {symbol} закрыта по стоп-лоссу!:red_circle:")
                            stop_orders = stop_orders + 1
                            opened_orders = opened_orders + 1
                            d1 = startbal * info.laverage
                            d2 = stopl/price
                            d3 = d2 - 1
                            d4 = d3 * -100
                            d5 = d4/100
                            d6 = d1 * d5
                            d7 = startbal - d6 - 0.1
                            trading_bal[symbol] = d7
                            a = False


            elif side == "SELL" and client.futures_get_open_orders(symbol=symbol) == []:
                new_stop_trigger = price - price * 0.06
                startbal = trading_bal[symbol]
                try:
                    q_size = get_qsize(symbol)
                    q = trading_bal.get(symbol) / price
                    q = q * info.laverage
                    if q_size == '1':
                        q = int(q)
                    else:
                        q = round_step_size(q, q_size)
                    logging.debug('info: ' + side + ' ' + symbol + ' ' + str(price) + ' ' + str(stopl) + ' ' + str(takep) + ' ' + str(q))
                    client.futures_change_leverage(symbol=symbol, leverage=info.laverage)
                    buyorder = client.futures_create_order(symbol=symbol, side=side, type="LIMIT", quantity=q, price=price, timeInForce="GTC", isIsolated='TRUE')
                    stop = client.futures_create_order(symbol=symbol, side="BUY", type="STOP_MARKET", stopPrice=stopl, closePosition="true")
                    take = client.futures_create_order(symbol=symbol, side="BUY", type="TAKE_PROFIT_MARKET", stopPrice=takep, closePosition="true")
                    embed = discord.Embed(color=discord.Color.green(), title=":money_with_wings:Сделка открыта!:money_with_wings:")
                    embed.add_field(name=":coin:Монета:coin:", value=f'{symbol}')
                    embed.add_field(name="Позиция:", value=f'{side}')
                    embed.add_field(name="Количество:", value=f'{q}')
                    embed.add_field(name=":moneybag:Цена открытия:moneybag:", value=f'{price} :money_with_wings:')
                    embed.add_field(name=":no_entry_sign:стоп-лосс:no_entry_sign:", value=f'{stopl}')
                    embed.add_field(name=":money_mouth:тейк-профит:money_mouth: ", value=f'{takep}')
                    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/984743487037644833/986256233579302922/5271665807120666932.jpeg")
                    embed.set_footer(text=f"bot v.{info.bot_version}")
                    channel = DS.get_channel(1009370759979868260)
                    await channel.send(embed=embed)
                    all_orders = all_orders + 1
                    opened_orders = opened_orders + 1
                    a = True
                except Exception as e:
                    await ctx.channel.send(content=f":red_circle:Ошибка открытия! ({e}):red_circle:")
                    a = False

                while a == True:
                    orders = client.futures_get_open_orders(symbol=symbol)
                    if len(orders) == 2 or len(orders) == 3:
                        prices = requests.get('https://api.binance.com/api/v3/ticker/price').json()
                        sym_price = get_price(symbol, prices)
                        if float(sym_price) <= new_stop_trigger:
                            stop_price = new_stop_trigger*sl_cof
                            stop_price = new_stop_trigger + stop_price
                            new_stop_trigger = new_stop_trigger - new_stop_trigger * 0.06
                            stop_price = round_step_size(float(stop_price), float(price_size))
                            client.futures_cancel_order(symbol=symbol, orderId=stop['orderId'], timestamp='true')
                            stop = client.futures_create_order(symbol=symbol, side="BUY", type="STOP_MARKET", stopPrice=stop_price, closePosition="true")
                        await asyncio.sleep(60)
                    else:
                        try:
                            if client.futures_get_open_orders(symbol=symbol, type="STOP_MARKET") != []:
                                    channel = DS.get_channel(1009370759979868260)
                                    await channel.send(
                                        content=f":dollar:Позиция на монету {symbol} закрыта по тейк-профиту!:dollar:")
                                    client.futures_cancel_order(symbol=symbol, orderId=stop['orderId'], timestamp='true')
                                    take_orders = take_orders + 1
                                    opened_orders = opened_orders - 1
                                    d1 = startbal * info.laverage
                                    d2 = takep / price
                                    d3 = d2 - 1
                                    d32 = d3 * -100
                                    d33 = d32 / 100
                                    d4 = d1 * d33
                                    d5 = d4 + startbal - 0.1
                                    trading_bal[symbol] = d5
                                    a = False
                            elif client.futures_get_open_orders(symbol=symbol, type="TAKE_PROFIT_MARKET") != []:
                                    channel = DS.get_channel(1009370759979868260)
                                    await channel.send(
                                        content=f":red_circle:Позиция на монету {symbol} закрыта по стоп-лоссу!:red_circle:")
                                    client.futures_cancel_order(symbol=symbol, orderId=take['orderId'], timestamp='true')
                                    stop_orders = stop_orders + 1
                                    opened_orders = opened_orders - 1
                                    d1 = startbal * info.laverage
                                    d2 = stopl / price
                                    d3 = d2 - 1
                                    d4 = d3 * 100
                                    d5 = d4 / 100
                                    d6 = d1 * d5
                                    d7 = startbal - d6 - 0.1
                                    trading_bal[symbol] = d7
                                    a = False
                        except:
                            continue
            else:
                await  ctx.channel.send(content=":beginner:Ордер на эту монету уже открыт:beginner:")
        else:
            await  ctx.channel.send(content=":beginner:Монеты нет в списке:beginner:")
    elif ctx.channel.id == 1009370701448351835 and ctx.content == '!stat':
        embed = discord.Embed(color=discord.Color.green(), title=":money_with_wings:Статистика за сессию:money_with_wings:")
        embed.add_field(name="Всего сделок:", value=f'{all_orders}')
        embed.add_field(name="Открытых сделок:", value=f'{opened_orders}')
        embed.add_field(name="Закрытых по стоп-лоссу:", value=f'{stop_orders}')
        embed.add_field(name="закрытых по тейк-профиту: ", value=f'{take_orders}')
        embed.set_footer(text=f"bot v.{info.bot_version}")
        await ctx.channel.send(embed=embed)
    elif ctx.channel.id == 1009370701448351835 and ctx.content == '!balance':
        embed = discord.Embed(color=discord.Color.green(), title=":money_with_wings:Баланс на монетах:money_with_wings:")
        for i in trading_bal.items():
            embed.add_field(name=f"{i[0]}", value=f'{round(i[1])}')
        embed.set_footer(text=f"bot v.{info.bot_version}")
        await ctx.channel.send(embed=embed)

DS.run(info.discord_token)
