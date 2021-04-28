import matplotlib.pyplot as plt
from datetime import datetime

def collectDataFromFile(filename, startTime, endTime):
    with open(filename) as log:
        lines = log.readlines()

    times = []
    prices = []
    actions = []
    for line in lines:
        # A line looks like this.
        # 2021/04/23, 12:03:00 | === Buy at 17172.0 positions: [17213.0], profit: 850.0 ===
        if "|" not in line:
            continue
        dateStr = line.split("|")[0].strip()
        dateAndTime = datetime.strptime(dateStr, "%Y/%m/%d, %H:%M:%S")
        if dateAndTime < startTime:
            continue
        elif dateAndTime > endTime:
            break

        msg = line.split("|")[1].strip()
        if "Buy at" in msg:
            pos = msg.find("Buy at") + 7
            price = int(float(msg[pos:].split()[0]))
            times.append(dateAndTime)
            prices.append(price)
            actions.append("B")

        elif "Sell at" in msg:
            pos = msg.find("Sell at") + 8
            price = int(float(msg[pos:].split()[0]))
            times.append(dateAndTime)
            prices.append(price)
            actions.append("S")

    return times, prices, actions


def draw(times, prices, actions):
    # Draw the line
    plt.plot(times, prices, color='black', linestyle='-', linewidth=2)

    # Draw buy/sell points
    for point in zip(times, prices, actions):
        if point[2] == "B": # action = Buy
            color = "red"
        else: # action = Sell
            color = "green"
        plt.scatter(point[0], point[1], s=50, marker='o', color=color)

    # naming the axes
    plt.xlabel('time')
    plt.ylabel('price')

    # giving a title to my graph
    plt.title('Buy/Sell Points')

    # Open the window
    plt.show()

if __name__ == '__main__':
    startTime = datetime.strptime("2021/04/28, 08:45:00", "%Y/%m/%d, %H:%M:%S")
    endTime = datetime.strptime("2021/04/29, 08:45:00", "%Y/%m/%d, %H:%M:%S")
    times, prices, actions = collectDataFromFile("MoneyMaker.log", startTime, endTime)
    draw(times, prices, actions)
