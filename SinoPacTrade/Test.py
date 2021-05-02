import datetime
import matplotlib.pyplot as plt
import random
import time

import Util

def testChart():
    # # function to show the plot
    plt.show()
    print("after show")

    axes = plt.gca()

    # plotting the points
    # plt.plot(xCoordinates, yCoordinates, color='green', linestyle='-', linewidth = 2, markerfacecolor='black')
    lines, = axes.plot([], [], color='green', linestyle='-', linewidth = 2, marker='o', markerfacecolor='black', markersize=8)
    xdata = []
    ydata = []
    lines.set_xdata(xdata)
    lines.set_ydata(ydata)
    # setting x and y axis range
    # plt.ylim(1,8)
    # plt.xlim(1,8)

    # naming the x axis
    plt.xlabel('x - axis')
    # naming the y axis
    plt.ylabel('y - axis')

    # giving a title to my graph
    plt.title('Some cool customizations!')

    xs = [datetime.datetime.now() + datetime.timedelta(hours=ii+15) for ii in range(100)]
    ys = [ii for ii in range(100)]

    # xs = [x for x in range(100)]
    # ys = random.sample(range(-50, 50), 100)

    idx = 0
    while True:
        Util.updateChart(lines, axes, xs[idx], ys[idx])
        time.sleep(0.5)
        idx += 1

    # xs = [datetime.datetime.now() + datetime.timedelta(hours=ii+7) for ii in range(6)]
    # print(xs)
    # Util.drawCharts(xs, [1, 4, 9, 16, 25, 36])

if __name__ == '__main__':
    testChart()
