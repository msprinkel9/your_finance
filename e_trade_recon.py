#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 22:49:23 2020

@author: michaelsprinkel
"""

import pandas as pd

# Import transaction data manually input to Excel
equity_trans = pd.read_excel(r'/Users/michaelsprinkel/Documents/e_trade_transactions.xlsx', sheet_name='equity_transactions')
equity_trans['trans_date'] = equity_trans['trans_date'].dt.date

# For all sell transactions change share count to negative
for i in range(len(equity_trans['share_count'])):
    if equity_trans['trans_type'].loc[i] == 'sell':
        equity_trans['share_count'].loc[i] = equity_trans['share_count'].loc[i] * -1

funding_trans = pd.read_excel(r'/Users/michaelsprinkel/Documents/e_trade_transactions.xlsx', sheet_name='funding_transactions')
funding_trans['trans_date'] = funding_trans['trans_date'].dt.date

# Find unique list of tickers
unique_ticker = equity_trans['ticker'].unique().tolist()

# Iterate through list and return earliest transaction date to a list
earliest_trans = []

for i in range(len(unique_ticker)):
    df = equity_trans[equity_trans.ticker == unique_ticker[i]]
    earliest_trans = earliest_trans + [df['trans_date'].min()]
    
# Combine two lists into a dictionary with each unique ticker and its earliest transaction date
ticker_and_date = dict(zip(unique_ticker, earliest_trans))


from python_wtd import WTD

# Pull data from API for each ticker and filtered by date
wtd = WTD(api_key='Sm5uUlZZpWU32Sc3RE8HTEZ8Jrbe9L5bsmbjyGwr34xrzUBIhhTRpHkFnntf')

d = {}
for name in unique_ticker:
    d[name] = pd.DataFrame()
    
# Pulls data from API and creates dataframe for each ticker and formats
for name, df in d.items():
    d[name] = wtd.historical(name)
    d[name] = d[name].drop(['open','high','low','volume'], axis=1)
    d[name]['date'] = d[name].index
    d[name]['date'] = d[name]['date'].dt.date
    d[name] = d[name].set_index(pd.Series(range(len(d[name]['date']))))
    d[name] = d[name].loc[d[name]['date'] >= ticker_and_date[name]]
    d[name]['share_count'] = 0 * len(d[name]['date'])
    d[name]['market_value'] = 0 * len(d[name]['date'])
    d[name]['cost'] = 0 * len(d[name]['date'])
    d[name]['total_gain'] = 0 * len(d[name]['date'])
    d[name]['daily_gain'] = 0 * len(d[name]['date'])
    d[name]['proceeds'] = 0 * len(d[name]['date'])
    
# Populates the proceeds for each ticker when selling
for i in range(len(equity_trans['trans_date'])):
    if equity_trans['trans_type'].loc[i] == 'sell':
        for j in range(len(d[equity_trans['ticker'].loc[i]])):
            if d[equity_trans['ticker'].loc[i]]['date'].loc[j] == equity_trans['trans_date'].loc[i]:
                d[equity_trans['ticker'].loc[i]]['proceeds'].loc[j] = (equity_trans['share_count'].loc[i] * equity_trans['execution_price'].loc[i] * -1)
    
# Populates the share count values for each ticker based on transactions imported
for i in range(len(equity_trans['trans_date'])):
    if equity_trans['trans_type'].loc[i] == 'buy' or 'dividend':
        for j in range(len(d[equity_trans['ticker'].loc[i]])):
            if d[equity_trans['ticker'].loc[i]]['date'].loc[j] >= equity_trans['trans_date'].loc[i]:
                d[equity_trans['ticker'].loc[i]]['share_count'].loc[j] = d[equity_trans['ticker'].loc[i]]['share_count'].loc[j] + equity_trans['share_count'].loc[i]

# Populates the market value for each ticker 
for name, df in d.items():
    for i in range(len(d[name])):
        d[name]['market_value'].loc[i] = d[name]['share_count'].loc[i] * d[name]['close'].loc[i]

# Populates the cost value for each ticker based on transactions imported
for i in range(len(equity_trans['execution_price'])):
    if equity_trans['trans_type'].loc[i] == 'buy' or 'dividend':
        for j in range(len(d[equity_trans['ticker'].loc[i]])):
            if d[equity_trans['ticker'].loc[i]]['date'].loc[j] >= equity_trans['trans_date'].loc[i] and d[equity_trans['ticker'].loc[i]]['share_count'].loc[j] != 0:
                d[equity_trans['ticker'].loc[i]]['cost'].loc[j] = d[equity_trans['ticker'].loc[i]]['cost'].loc[j] + (equity_trans['execution_price'].loc[i] * equity_trans['share_count'].loc[i])

# Populates daily gain for each ticker at each date
for name, df in d.items():
    for i in range(len(d[name])):
        k = i + 1
        if d[name]['proceeds'].loc[i] == 0:
            if i < (len(d[name]) - 1):
                d[name]['daily_gain'].loc[i] = (d[name]['market_value'].loc[i] - d[name]['market_value'].loc[k]) - (d[name]['cost'].loc[i] - d[name]['cost'].loc[k])
            else:
                d[name]['daily_gain'].loc[i] = (d[name]['market_value'].loc[i] - d[name]['cost'].loc[i])
        else:
            d[name]['daily_gain'].loc[i] = d[name]['proceeds'].loc[i] - d[name]['market_value'].loc[k]
            
# Populates total gain for each ticker at each date
for name, df in d.items():
    for i in range(len(d[name])):
        k = i - 1
        if i == 0:
            d[name]['total_gain'].loc[i] = d[name]['daily_gain'].sum()
        else:
            d[name]['total_gain'].loc[i] = (d[name]['total_gain'].loc[k] - d[name]['daily_gain'].loc[k])

# Find the maximum index to get size of portfolio master dataset
longest_df = []
for name, df in d.items():
    longest_df.append(d[name].index.max())
    
max_index = max(longest_df)

# Aggregate each holding data for master dataset
columns = ['date','market_value','cash','total_balance','cost','daily_gain','total_gain']
portfolio = pd.DataFrame(0, index=range(max_index+1), columns=columns)

for name, df in d.items():
    for i in range(len(d[name])):
        portfolio['date'].loc[i] = d[name]['date'].loc[i]
        portfolio['market_value'].loc[i] = portfolio['market_value'].loc[i] + d[name]['market_value'].loc[i]
        portfolio['cost'].loc[i] = portfolio['cost'].loc[i] + d[name]['cost'].loc[i]
        portfolio['daily_gain'].loc[i] = portfolio['daily_gain'].loc[i] + d[name]['daily_gain'].loc[i]
        portfolio['total_gain'].loc[i] = portfolio['total_gain'].loc[i] + d[name]['total_gain'].loc[i]
        
portfolio['total_balance'] = portfolio['market_value'] + portfolio['']
portfolio['unrealized_gain'] = portfolio['market_value'] - portfolio['cost']
portfolio['realized_gain'] = portfolio['total_gain'] - portfolio['unrealized_gain']


# Only thing we need to do now is to use equity trans and funding trans to calculate cash in account 
