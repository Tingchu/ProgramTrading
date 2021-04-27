import datetime
import matplotlib.pyplot as plt
import numpy

def log(msg="", level="", stdout=True, dump=True):
    dateAndTime = datetime.datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
    levelString = "" if level == "" else f"[{level}]"
    outputString = f"{dateAndTime} : {msg}"
    if stdout:
        print(levelString + " " + outputString)
    if dump:
        with open("MoneyMaker.log", "a") as log:
            log.write(f"{dateAndTime} : {levelString} {msg}\n")


def getPositions(api):
    # query_type = '0': detail; '1': summary
    # If detail, return a list with each position having one dict, volume = 1 and "ContractAverPrice" = each position's closing price
    # If summary, return a list with only one dict, averaging all positions' closing price as "ContractAverPrice"
    positions = api.get_account_openposition(query_type='0', account=api.futopt_account)
    positions = positions.data() # get the list

    closingPrices = []
    positionAction = "Unknown"
    if positions[0]:
        positionAction = positions[0]["OrderBS"] # "B" or "S"
        for position in positions:
            assert(position["OrderBS"] == positionAction)
            assert(int(float(position["Volume"])) == 1)
            closingPrices.append(position["ContractAverPrice"])

    return positionAction, closingPrices

def initializeChart(lines, axes):
    # function to show the plot
    # plt.show()

    # axes = plt.gca()

    # plotting the points
    # plt.plot(xCoordinates, yCoordinates, color='green', linestyle='-', linewidth = 2, markerfacecolor='black')
    # lines, = axes.plot([], [], color='green', linestyle='-', linewidth = 2, marker='o', markerfacecolor='black', markersize=8)
    xdata = []
    ydata = []
    lines.set_xdata(xdata)
    lines.set_ydata(ydata)

    # setting x and y axis range
    # plt.ylim(1,8)
    # plt.xlim(1,8)

    # naming the axes
    plt.xlabel('x axis')
    plt.ylabel('y axis')

    # giving a title to my graph
    plt.title('Dealed prices')

def updateChart(lines, axes, xValue, yValue):
    print(f"{xValue} {yValue}")
    xdata = lines.get_xdata()
    xdata.append(xValue)
    ydata = lines.get_ydata()
    ydata.append(yValue)
    axes.set_xlim(min(xdata), max(xdata))
    axes.set_ylim(min(ydata), max(ydata))
    lines.set_xdata(xdata)
    lines.set_ydata(ydata)
    plt.draw()
    plt.pause(1e-17)
