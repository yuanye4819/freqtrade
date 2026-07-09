"""=================================================
@PROJECT_NAME: freqtrade
@File    : test.py
@Author  : Kepler
@Date    : 2026/6/16 上午10:31
@Function: 

@Modify History:
         
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""
import ccxt
exchange = ccxt.okx({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET',
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot',  # or 'future'
    }
})
markets = exchange.load_markets()
print(markets.keys())