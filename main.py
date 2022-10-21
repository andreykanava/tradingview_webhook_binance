import pandas as pd
from binance.client import Client
from binance.helpers import round_step_size
import info
from flask import Flask,request,json


client = Client(api_key=info.api, api_secret=info.secret_api, testnet=False)
app = Flask(__name__)

def get_qsize(symbol):
    info = client.futures_exchange_info()
    for item in info['symbols']:
        if(item['symbol'] == symbol):
            for f in item['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    return f['stepSize']

def get_pricesize(symbol):
    info = client.futures_exchange_info()
    for item in info['symbols']:
        if(item['symbol'] == symbol):
            for f in item['filter']:
                if f['filterType'] == 'PRICE_FILTER':
                    return f['tickSize']

for i in info.tokens:
        try:
            client.futures_change_margin_type(symbol=i, marginType='ISOLATED')
            client.futures_change_leverage(symbol=i, leverage=info.laverage)
        except:
            continue


pos_list = {}

class Position:
    def new_position(self, side, symbol, price, stopl, takep):

        b=client.futures_account_balance()
        b = pd.DataFrame.from_dict(b)
        b = b.loc[b['asset']=='USDT']
        balance = float(b['balance'].values) * 0.05
        q = balance / price * info.laverage

        #rounding
        q_size = get_qsize(symbol)
        price_size = get_pricesize(symbol)

        #opening order
        buyorder = client.futures_create_order(symbol=symbol, side=side, type="MARKET", quantity=round_step_size(q, q_size), isIsolated='TRUE')
        self.stop = client.futures_create_order(symbol=symbol, side="SELL", type="STOP_MARKET", stopPrice=round_step_size(float(stopl), float(price_size)), closePosition="true")
        self.take = client.futures_create_order(symbol=symbol, side="SELL", type="TAKE_PROFIT_MARKET", stopPrice=round_step_size(float(takep), float(price_size)), quantity=round_step_size(q/2, q_size))
        if side == "BUY":
            self.close_side = "SELL"
        else:
            self.close_side = "BUY"
        self.symbol = symbol
        self.q = round_step_size(q, q_size)

    def close_position(self):
        #post close order
        close = client.futures_create_order(symbol=self.symbol, side=self.close_side, type="MARKET", quantity=self.q, reduceOnly='true')
        #close orders
        try:
            client.futures_cancel_order(symbol=self.symbol, orderId=self.stop['orderId'], timestamp='true')
        except:
            pass
        try:
            client.futures_cancel_order(symbol=self.symbol, orderId=self.take['orderId'], timestamp='true')
        except:
            pass


#WEBHOOK EVENT
@app.route('/webhook', methods=['POST'])
def webhook():
    global pos_list
    if request.method == 'POST':
        raw_data = request.json["content"].split()
        if raw_data[0] == "/open":
            position = Position()
            position.new_position(raw_data[1], raw_data[2].replace("PERP", ""), float(raw_data[3]), float(raw_data[4]), float(raw_data[5]))
            pos_list[raw_data[2]] = position
            print(pos_list)
        elif raw_data[0] == "/close":
            position = pos_list[raw_data[1]]
            position.close_position()

if __name__ == '__main__':
    app.run(debug=True)
