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
idf = pd.read_csv('apps/streaming/data/coco_gusto-NEW.csv',index_col=0,parse_dates=True)

start_of_year = datetime.today().replace(day=1).replace(month=1).date().strftime('%Y-%m-%d')
today = datetime.today().strftime('%Y-%m-%d')

df = idf.loc[start_of_year:today,:]



fig = mpf.figure(figsize=(5,7))
plt.rcParams['xtick.labelsize'] = 10  # Adjust the size as needed

# ax1 = fig.add_subplot(2,1,1)
# ax2 = fig.add_subplot(3,1,3)
# Configure the axes
ax1 = fig.add_subplot(4,1,(1,2))
ax2 = fig.add_subplot(4,1,3, sharex=ax1)
ax3 = fig.add_subplot(4,1,4, sharex=ax1)

ax1.tick_params(labelbottom=False)
ax2.tick_params(labelbottom=False)

ax2.yaxis.set_label_position("right")

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
    ax1.set_title('2024 cost control evolution for gusto')

    moving_averages = [7]

    # s  = mpf.make_mpf_style(base_mpf_style='default',y_on_right=True)
    # apds = mpf.make_addplot((data['Close'] / data['Volume']),panel=1,color='g') #,y_on_right=False,secondary_y=True,ylabel='avg. daily revenue')

     # Create add plots
    aps = [
        mpf.make_addplot(
        data['Close'] / data['Volume'], 
        ax=ax2, 
        ylabel='£/day revenue',
        secondary_y=True,
        color='g'
        )        
        ]

    
    mpf.plot(data,
             type='candle', 
             ax=ax1,
             mav=moving_averages,
             volume=ax3,
            # volume=True,
            #  style=s,
             addplot=aps,
             datetime_format='%d-%b', 
             xrotation=0,
             ylabel="Revenue", 
             ylabel_lower="Num transactions",
             tight_layout = True,
             returnfig=True)

ani = animation.FuncAnimation(fig, animate, interval=50)

mpf.show()
