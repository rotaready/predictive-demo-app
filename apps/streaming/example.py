'''
This file contains a simple animation demo using mplfinance "external axes mode".

Note that presently mplfinance does not support "blitting" (blitting makes animation
more efficient).  Nonetheless, the animation is efficient enough to update at least
once per second, and typically more frequently depending on the size of the plot.

https://github.com/matplotlib/mplfinance/blob/master/examples/mpf_animation_demo1.py

'''
import pandas as pd

import matplotlib.pyplot as plt
import mplfinance as mpf
import matplotlib.animation as animation

from datetime import datetime

# idf = pd.read_csv('notebooks/streaming/data/SPY_20110701_20120630_Bollinger.csv',index_col=0,parse_dates=True)
idf = pd.read_csv('apps/streaming/coco_temper.csv',index_col=0,parse_dates=True)

start_of_year = datetime.today().replace(day=1).replace(month=1).date().strftime('%Y-%m-%d')
today = datetime.today().strftime('%Y-%m-%d')

df = idf.loc[start_of_year:today,:]

fig = mpf.figure(style='charles',figsize=(7,8))
plt.rcParams['xtick.labelsize'] = 10  # Adjust the size as needed

ax1 = fig.add_subplot(2,1,1)
ax2 = fig.add_subplot(3,1,3)

def animate(ival):
    if (20+ival) > len(df):
        print('no more data to plot')
        ani.event_source.interval *= 3
        if ani.event_source.interval > 12000:
            exit()
        return
    data = df.iloc[0:(20+ival)]
    # ax1.clear()
    # ax2.clear()
    ax1.set_title('2024 cost control evolution for temper')
    mpf.plot(data,
             ax=ax1,
             volume=ax2,
             type='candle', 
             datetime_format='%d-%b', 
             xrotation=0,
             ylabel="Revenue", 
             ylabel_lower="Num transactions",
             returnfig=True)

ani = animation.FuncAnimation(fig, animate, interval=50)

mpf.show()
