import os
import discord
from dotenv import load_dotenv
import requests
import pandas as pd
import matplotlib.pyplot as plt
import csv
import re
import sqlite3

load_dotenv()
api_key = os.getenv('KEY')
conn = sqlite3.connect('people.db')
c = conn.cursor()

c.execute("""CREATE TABLE persons (
          name text,
          net_worth real,
          cash real,
          shares text
)



""")

c.execute("""CREATE TABLE orders (
        person text,
        activity text,
        share_name text,
        share_price real,
        number_of_shares int,
        stop_loss real,
        total real
)
""")

client = discord.Client()



gl_counter = 0


def get_price(symbol):
    stock_url = r'https://www.alphavantage.co/query?function=' + 'TIME_SERIES_INTRADAY' + '&symbol=' + symbol + '&interval=1min' + '&apikey=' + api_key + '&data_type=csv'
    price = 0
    # get data in csv format
    with requests.Session() as s:
        download = s.get(stock_url)
        decoded_content = download.content.decode('utf-8')
        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        my_list = list(cr)

        price = float(re.findall('[0-9]*\.[0-9]*', my_list[14][0])[1])
        return price


def add_event(person, action, symbol, share_number, stop_loss):
    stock_url = r'https://www.alphavantage.co/query?function=' + 'TIME_SERIES_INTRADAY' + '&symbol=' + symbol + '&interval=1min' + '&apikey=' + api_key + '&data_type=csv'

    price = get_price(symbol)
    c.execute('INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)', ( person, action, symbol, price, share_number, stop_loss, share_number * price))
    conn.commit()
    # print an order summary
    return price


def check_bought_without_stop_loss(symbol):
    c.execute('SELECT * FROM orders WHERE share_name = (?) AND stop_loss != (?)', (symbol, 0))
    symbol_orders = c.fetchall()
    s = 0
    b = 0
    for order in symbol_orders:
        if order[2] == 'S':
            s += order[5]
        else:
            b += order[5]

    if s == b:
        return True
    else:
        return False



def check_cash(person, symbol, share_number):
    price = get_price(symbol)
    c.execute('SELECT cash FROM persons WHERE name=(?)', [person])
    cash_owned = float(c.fetchall()[0][0])

    total = price * share_number
    if cash_owned >= total:
        return True
    else:
        return False



def check_bought_with_stop_loss(symbol):
    c.execute('SELECT * FROM orders WHERE share_name = (?) AND stop_loss != (?)', (symbol, 0))
    symbol_orders = c.fetchall()
    s = 0
    b = 0
    for order in symbol_orders:
        if order[2] == 'S':
            s += order[5]
        else:
            b += order[5]

    if s <= b:
        return True
    else:
        return False

def check_stop_loss(symbol):
        c.execute('SELECT * FROM orders WHERE share_name = (?) AND stop_loss != (?)', (symbol, 0))
        symbol_orders = c.fetchall()
        s = 0
        b = 0
        for order in symbol_orders:
            if order[2] == 'S':
                s += order[5]
            else:
                b += order[5]

        if s <= b:
            return b-s
        else:
            return 0

def add_shares_to_portfolio(person, symbol, buying_shares, price):
    c.execute('SELECT shares FROM persons WHERE name = (?)', [person])
    portfolio = c.fetchall()
    shares_symbol = re.findall('[A-Z]*', portfolio[0][0])
    if shares_symbol == ['', '']:
        shares_symbol = []
    temp_shares_value = re.findall('[0-9]*', portfolio[0][0])
    shares_value = []

    temp = 0




    for local_counter in range(0, len(shares_symbol)):
        shares_value.append(int(temp_shares_value[local_counter]))
        if shares_symbol[local_counter] == symbol:
            shares_value[local_counter] = shares_value[local_counter] + buying_shares
            temp = 0
        temp = temp + 1

    if temp == len(shares_symbol):
        shares_symbol.append(symbol)
        shares_value.append(buying_shares)

    string_portfolio = ''
    for i in range(0, len(shares_symbol)):
        string_portfolio = string_portfolio + str(shares_symbol[i]) + '-' + str(shares_value[i])

    total = price * buying_shares
    print(total)
    print(string_portfolio)
    c.execute('SELECT cash FROM persons WHERE name = (?)', [person])
    new_cash = float(c.fetchall()[0][0]) - total
    print(new_cash)
    c.execute('UPDATE persons SET shares= ?, cash=? WHERE name=?', (string_portfolio, new_cash, person))
    conn.commit()


def remove_shares_from_portfolio(person, symbol, buying_shares, price):
    c.execute('SELECT shares FROM persons WHERE name = (?)', [person])
    portfolio = c.fetchall()
    shares_symbol = re.findall('[A-Z]*', portfolio[0][0])
    temp_shares_value = re.findall('[0-9]*', portfolio[0][0])
    shares_value = []

    temp = 0
    pos = 0
    for local_counter in range(0, len(shares_symbol)):
        individual_shares_value = int(temp_shares_value[local_counter])
        if individual_shares_value == symbol:
            individual_shares_value = individual_shares_value - buying_shares
            if individual_shares_value != 0:
                shares_value.append(individual_shares_value)
            else:
                temp = 1
                pos = local_counter
        else:
            shares_value.append(individual_shares_value)

    string_portfolio = ''
    for i in range(0, len(shares_symbol)):
        if temp == 0:
            string_portfolio = string_portfolio + str(shares_symbol[i]) + '-' + str(shares_value[i])
        else:
            if (i > pos):
                string_portfolio = string_portfolio + str(shares_symbol[i]) + '-' + str(shares_value[i-1])
            elif (i < pos):
                string_portfolio = string_portfolio + str(shares_symbol[i]) + '-' + str(shares_value[i])

    total = price * buying_shares

    c.execute('SELECT cash FROM persons WHERE name = (?)', (person))
    new_cash = float(c.fetchall()[0][0]) + total
    c.execute('UPDATE persons SET shares=? AND cash=? WHERE name=?', (string_portfolio, new_cash, person))
    conn.commit()

def get_current_shares(account, person):
    c.execute('SELECT shares FROM persons WHERE name = (?)', (person))
    portfolio = c.fetchall()
    shares_symbol = re.findall('[A-Z]*', portfolio[0][0])
    temp_shares_value = re.findall('[0-9]*', portfolio[0][0])
    shares_value = []

    temp = 0
    for local_counter in range(0, len(shares_symbol)):
        shares_value.append(int(temp_shares_value[local_counter]))

        return shares_value


# first message given when online
@client.event
async def on_ready():

  # local 'general' channel. NEEDS TO BE CHANGED
  channel = client.get_channel(848518342533054467)
  await channel.send('Hi! I\'m Finn, your Financial Friend. To know more about me, type `-Finn, help`')



@client.event
async def on_message(message):
  # message cannot come from bot
  if message.author == client.user:
    return

  msg = message.content


  if len(msg.split()) == 2 and msg.split()[0] == '-open' and (float(msg.split()[1]) <= 500000 and float(msg.split()[1]) >= 20):
      person_store = (str(message.author), float(msg.split()[1]), float(msg.split()[1]), ' ')
      c.execute('INSERT INTO persons VALUES (?,?,?,?)', person_store)
      conn.commit()


  if msg == '-Finn, show account':
      c.execute('SELECT * FROM persons WHERE name=(?)', [str(message.author)])
      account = c.fetchall()

      await message.channel.send('```Name: '+account[0][0]+'\nNet Worth: '+str(account[0][1])+'\nCash: '+str(account[0][2])+'```')
      # change to a proper display
      # add profit to the net_worth
      # print('Name: ' + account[0][0] + '\nNet Worth: ' + str(account[0][1]) + '\nCash: ' + str(account[0][2]) + '\nShares: ')
      # print(account[0][3])
      # conn.commit()

  if msg == '-Finn, show leaderboard':
      c.execute('SELECT * FROM persons ORDER BY net_worth DESC')
      account = c.fetchall()
      for i in range(0, len(account)):
          await message.channel.send('```'+str(i+1)+'nd\n'+'Name: '+account[i][0]+'\nNet Worth: '+str(account[i][1])+'\nCash: '+str(account[i][2])+'\n```')


  if msg.startswith('-Finn, buy') and len(msg.split()) == 4:
      symbol = msg.split()[3]
      buying_shares = int(msg.split()[2])

      if (check_cash(str(message.author), symbol, buying_shares) and check_bought_without_stop_loss(symbol)):
          price = add_event(str(message.author), 'B', symbol, buying_shares, 0)

          await message.channel.send('```Name: '+str(message.author)+'\nAction: B\nStock: '+symbol+'\nNumber of shares: '+ str(buying_shares) +'\nStop Loss: 0' + '\nPrice: '+price+'```')

          add_shares_to_portfolio(str(message.author), symbol, buying_shares, price)

  if msg.startswith('-Finn, buy') and len(msg.split()) == 6:
      symbol = msg.split()[3]
      buying_shares = int(msg.split()[2])
      stop_loss = float(msg.split()[6])

      if (check_cash(str(message.author), symbol, buying_shares) and check_bought_with_stop_loss(symbol)):
          price = add_event(str(message.author), 'B', symbol, buying_shares, stop_loss)

          await message.channel.send('```Name: '+str(message.author)+'\nAction: B\nStock: '+symbol+'\nNumber of shares: '+ str(buying_shares) +'\nStop Loss: '+ str(stop_loss) + '\nPrice: '+price+'```')

          add_shares_to_portfolio(str(message.author), symbol, buying_shares, price)


  if msg.startswith('-Finn, sell') and len(msg.split()) == 4:
      symbol = msg.split()[3]
      selling_shares = int(msg.split()[2])

      if (check_have_shares(symbol, selling_shares)):
          price = add_event(str(message.author), 'S', symbol, buying_shares, stop_loss)
          remove_shares_from_portfolio(str(message.author), symbol, buying_shares, price)






  # help message
  if msg.startswith('-Finn, help'):

    embed = discord.Embed(
      colour = discord.Color.orange()
    )

    embed.set_author(name='Help Terminal')
    embed.add_field(name='Setting Up', value='`-Finn, help` - Brings up this terminal \n \
    -`Finn, open <amount>` - Opens an account for the User with a value `<amount>`.\n `<amount>` should be between `$20` and `$500,000` \n', inline=False)


    embed.add_field(name='Check Account and Leaderboard', value = '`-Finn, show account` - `Account` will be shown\n-Finn, show `<leaderboard>`', inline=False)

    embed.add_field(name='Trading (The Fun Stuff)', value = '`-Finn, search <stock>` - Enter the ticker symbol for `<stock>` to see info\n`-Finn, search <stock> <high/high-long> <xmin> <year1month1/year2month12>` - searches stock for either a day or an entire month')

    channel = client.get_channel(848518342533054467)
    await channel.send(embed=embed)


  # search stock
  if msg.startswith('-Finn, search'):
      if len(msg.split('-Finn, search ',)[1]) > 0:
          interval = '1min'
          function = 'TIME_SERIES_INTRADAY'
          symbol = msg.split()[2]

          if (len(msg.split()) == 3 or (msg.split()[4] == '1min')):
              interval = '1min'
          elif (msg.split()[4] == '5min'):
              interval = '5min'
          elif (msg.split()[4] == '15min'):
              interval = '15min'
          elif (msg.split()[4] == '30min'):
              interval = '30min'
          elif (msg.split()[4] == '60min'):
              interval = '60min'


          if len(msg.split()) == 3 or msg.split()[3] == 'high':
            function = 'TIME_SERIES_INTRADAY'

            # generate URL
            stock_url = r'https://www.alphavantage.co/query?function='+ function
            stock_url = stock_url + '&symbol=' + symbol
            stock_url = stock_url + '&interval=' + interval
            stock_url = stock_url + '&apikey=' + api_key + '&data_type=csv'

            # get data in csv format
            with requests.Session() as s:
                download = s.get(stock_url)
                decoded_content = download.content.decode('utf-8')
                cr = csv.reader(decoded_content.splitlines(), delimiter=',')
                my_list = list(cr)

                # find the last trade time and last closing price
                closing_value = [float(re.findall('[0-9]*\.[0-9]*', my_list[14][0])[1])]
                times = [re.findall('[0-2][0-9]:[0-5][0-9]:00', my_list[10][0])[0]]
                date = re.findall('[0-9]*-[0-9]*-[0-9]*', my_list[10][0])[0]
                time_counter = 17
                ctr = 21

                # find all the times and closing prices
                while (ctr < len(my_list)):
                    if re.findall('[0-9]*-[0-9]*-[0-9]*', my_list[time_counter][0])[0] != date:
                        break
                    closing_value.insert(0, float(re.findall('[0-9]*\.[0-9]*', my_list[ctr][0])[1]))
                    ctr = ctr + 7
                    times.insert(0 , re.findall('[0-2][0-9]:[0-5][0-9]:00', my_list[time_counter][0])[0])
                    time_counter = time_counter + 7


                # entire plotting process
                plt.plot(times, closing_value)
                plt.xlabel('Time')
                plt.ylabel('Price in USD')
                plt.xticks(rotation=90)
                plt.xticks(range(0,len(times)), times)
                plt.locator_params(axis='x', nbins = 10)
                plt.margins(0.05)
                plt.subplots_adjust(bottom=0.2)
                plt.title(symbol + ' Stock Price')
                plt.savefig('trade1.jpg')
                await message.channel.send(file=discord.File('trade1.jpg'))

                os.remove('trade1.jpg')
                plt.close()

                url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol='+ symbol +'&apikey=' + api_key
                r = requests.get(url)
                data = r.json()


                embed = discord.Embed(
                  colour = discord.Color.orange()
                )

                embed.set_author(name='Key Indicators')
                embed.add_field(name='Mathematical Functions', value='`EPS` - `$' + data['EPS']+'`\n \
                `Beta` - `' + data['Beta'] + '`\n `Dividend Per Share` - `' + data['DividendPerShare'] +'`\n \
                `50 Day Moving Average` - `' + data['50DayMovingAverage'] +'`', inline=False)

                embed.add_field(name='Share Price and Company Information', value='`52 Week High` - `$' + data['52WeekHigh'] +'` \n \
                `52 Week Low` - `$'+ data['52WeekLow'] +'` \n `EBITDA` - `$'+ data['EBITDA'] +'` \n `Quarterly Earnings Growth (Y.O.Y)` - `' + data['QuarterlyEarningsGrowthYOY']+'%`', inline=False)
                channel = client.get_channel(848518342533054467)
                await channel.send(embed=embed)












          elif len(msg.split()) > 3 and msg.split()[3] == 'high-long':
              function = 'TIME_SERIES_INTRADAY_EXTENDED'
              if len(msg.split()) == 6:
                  interval = interval + '&slice=' + msg.split()[5]
                  symbol = msg.split()[2]
                  data_type = 'csv'

                  # generate URL
                  stock_url = r'https://www.alphavantage.co/query?function='+ function
                  stock_url = stock_url + '&symbol=' + symbol
                  stock_url = stock_url + '&interval=' + interval
                  stock_url = stock_url + '&apikey=' + api_key + '&data_type=csv'

                  # get data in csv format
                  with requests.Session() as s:
                      download = s.get(stock_url)
                      decoded_content = download.content.decode('utf-8')
                      cr = csv.reader(decoded_content.splitlines(), delimiter=',')
                      my_list = list(cr)
                      price = [float(my_list[1][4])]
                      dates = [1]
                      number = 2
                      last_month = re.findall('[0-9]*-[0-9]*-[0-9]*', my_list[1][0])[0]
                      first_month = re.findall('[0-9]*-[0-9]*-[0-9]*', my_list[len(my_list)-1][0])[0]
                      for row in range(2, len(my_list)):
                          price.insert(0, float(my_list[row][4]))
                          dates.append(number)
                          number += 1

                      dates.reverse()
                      plt.plot(dates, price)
                      plt.xlabel(first_month + ' - ' + last_month)
                      plt.ylabel('Price in USD')
                      plt.xticks(rotation=90)
                      plt.xticks([])
                      plt.margins(0.05)
                      plt.subplots_adjust(bottom=0.2)
                      plt.title(symbol + ' Stock Price')
                      plt.savefig('trade1.jpg')
                      await message.channel.send(file=discord.File('trade1.jpg'))

                      os.remove('trade1.jpg')
                      plt.close()

                      url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol='+ symbol +'&apikey=' + api_key
                      r = requests.get(url)
                      data = r.json()


                      embed = discord.Embed(
                        colour = discord.Color.orange()
                      )

                      embed.set_author(name='Key Indicators')
                      embed.add_field(name='Mathematical Functions', value='`EPS` - `$' + data['EPS']+'`\n \
                      `Beta` - `' + data['Beta'] + '`\n `Dividend Per Share` - `' + data['DividendPerShare'] +'`\n \
                      `50 Day Moving Average` - `' + data['50DayMovingAverage'] +'`', inline=False)

                      embed.add_field(name='Share Price and Company Information', value='`52 Week High` - `$' + data['52WeekHigh'] +'` \n \
                      `52 Week Low` - `$'+ data['52WeekLow'] +'` \n `EBITDA` - `$'+ data['EBITDA'] +'` \n `Quarterly Earnings Growth (Y.O.Y)` - `' + data['QuarterlyEarningsGrowthYOY']+'%`', inline=False)
                      channel = client.get_channel(848518342533054467)
                      await channel.send(embed=embed)






if (gl_counter == 30):
    gl_counter = 0
    c.execute('SELECT name FROM persons')
    all_people = c.fetchall()
    for person in all_people:
        c.execute('SELECT shares FROM persons WHERE name = (?)', (person[0]))
        portfolio = c.fetchall()
        shares_symbol = re.findall('[A-Z]*', portfolio[0][0])
        c.execute('SELECT net_worth FROM name=(?)', person[0])
        dollar_worth = float(c.fetchall()[0][0])
        number_shares = get_current_shares(person[0])

        for symbol in shares_symbol:
            shares = check_stop_loss(symbol)
            if shares != 0:
                price = get_price(symbol)
                c.execute('SELECT stop_loss FROM persons WHERE name=(?)', (person[0]))
                stop_loss_local = c.fetchall()
                if price <= stop_loss_local:
                    remove_shares_from_portfolio(person[0], symbol, shares, price)
                    price = add_event(person[0], 'S', symbol, shares, stop_loss_local)

            price = get_price(symbol)
            profit = price * number_shares[shares_symbol.index(symbol)]
            dollar_worth = profit + dollar_worth
            c.execute('UPDATE persons SET net_worth=(?)', dollar_worth)
            conn.commit()
else:
    gl_counter = gl_counter + 1;






client.run(os.getenv('TOKEN'))
