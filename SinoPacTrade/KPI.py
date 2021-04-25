# Library import
import datetime
from statistics import mean

# Self defined class import
import Util

class KPI:
    def __init__(self, api, code, subcode, debugMode=True):
        self.debugMode = debugMode
        self.api = api
        self.code = code
        self.subcode = subcode

        # Flow control
        self.initState = True
        self.actionRequired = False # Every minute we check whether or not to buy or sell something.

        # 5-minute average moving line
        self.last20MinPrices = [0 for x in range(20)] # The latest prices are push_back into the list
        self.avg5MinPrice = 0.0
        self.avg5MinMovingLineGoingUp = True

        self.currentMinute = 0 # 0~59


    def getStreamingData(self):
        target = self.api.Contracts.Futures[self.code][self.subcode]
        self.api.quote.set_quote_callback(self.quoteCallback)
        self.api.quote.subscribe(target, quote_type="tick")


    def update5MinFactors(self):
        previousAvg5MinPrice = self.avg5MinPrice

        # Handled initial states where no enough prices are collected
        if self.last20MinPrices[-1] == 0:
            self.avg5MinPrice = 0.0
        else:
            idx = -1
            nonZeroCount = 0
            while idx >= -5:
                if self.last20MinPrices[idx] == 0:
                    break
                nonZeroCount += 1
                idx -= 1
            startValidIdx = 20 - nonZeroCount
            self.avg5MinPrice = mean(self.last20MinPrices[startValidIdx:])

        self.initState = (previousAvg5MinPrice == 0.0)
        self.actionRequired &= (not self.initState)
        self.avg5MinMovingLineGoingUp = (previousAvg5MinPrice < self.avg5MinPrice)

        if self.debugMode:
            print(f"last20MinPrices: {self.last20MinPrices}")
            print(f"initState: {self.initState}")
            print(f"previousAvg5MinPrice: {previousAvg5MinPrice}")
            print(f"avg5MinPrice: {self.avg5MinPrice}")
            print(f"avg5MinMovingLineGoingUp: {self.avg5MinMovingLineGoingUp}")


    def quoteCallback(self, topic: str, quote: dict):
        # print(f"MyTopic: {topic}, MyQuote: {quote}")
        # Util.log("CurrentPrice: {}".format(quote["Close"][0]), level="Info", stdout=True, dump=False)
        currentTime = quote["Time"]      # Should look like "21:59:56.123456"
        currentPrice = quote["Close"][0] # Should look like 16000.0
        minute = datetime.datetime.strptime(currentTime, "%H:%M:%S.%f").timetuple().tm_min
        if minute != self.currentMinute:
            # Another minute passed, need to update average moving lines and (maybe) make some deals
            if self.currentMinute != 0 and minute != (self.currentMinute + 1) % 60:
                missedMinutes = minute - self.currentMinute if minute - self.currentMinute >= 0 else minute + 60 - self.currentMinute
                Util.log(f"Miss {missedMinutes} minutes of data", level="Warning")
            self.currentMinute = minute
            self.last20MinPrices.append(currentPrice)
            self.last20MinPrices.pop(0)
            self.actionRequired = True
            self.update5MinFactors()