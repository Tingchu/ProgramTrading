# Library import
import datetime
from statistics import mean

# Self defined class import
import Util

class KPI:
    def __init__(self, api, code, subcode, debugMode=True):
        # Settings
        self.debugMode = debugMode
        self.api = api
        self.code = code
        self.subcode = subcode

        # Constants
        self.consolidationDiffThreshold = 0.61  # 0.01 to workaround for python float substraction error

        # Flow control
        self.initState = True
        self.actionRequired = False # Every minute we check whether or not to buy or sell something.

        # 5-minute average moving line
        self.windowSize = 20
        self.last20MinPrices = [0 for x in range(self.windowSize)] # The latest prices are push_back into the list
        self.avg5MinPrice = 0.0
        self.avg5MinMovingLineGoingUp = True
        self.avg10MinPrice = 0.0
        self.avg10MinMovingLineGoingUp = True
        self.consolidating = True   # 盤整

        self.currentMinute = 0 # 0~59


    def getStreamingData(self):
        target = self.api.Contracts.Futures[self.code][self.subcode]
        self.api.quote.set_quote_callback(self.quoteCallback)
        self.api.quote.subscribe(target, quote_type="tick")


    def updateKPIs(self):
        previousAvg5MinPrice = self.avg5MinPrice
        previousAvg10MinPrice = self.avg10MinPrice

        # Handled initial states where no enough prices are collected
        if self.last20MinPrices[-1] == 0:
            self.avg5MinPrice = 0.0
            self.avg10MinPrice = 0.0
        else:
            # Update 5MA
            idx = -1
            nonZeroCount = 0
            while idx >= -5:
                if self.last20MinPrices[idx] == 0:
                    break
                nonZeroCount += 1
                idx -= 1
            startValidIdx = self.windowSize - nonZeroCount
            self.avg5MinPrice = mean(self.last20MinPrices[startValidIdx:])

            # Update 10MA
            idx = -1
            nonZeroCount = 0
            while idx >= -10:
                if self.last20MinPrices[idx] == 0:
                    break
                nonZeroCount += 1
                idx -= 1
            startValidIdx = self.windowSize - nonZeroCount
            self.avg10MinPrice = mean(self.last20MinPrices[startValidIdx:])

        self.initState = (previousAvg5MinPrice == 0.0)
        self.actionRequired &= (not self.initState)
        self.avg5MinMovingLineGoingUp = (previousAvg5MinPrice < self.avg5MinPrice)
        self.avg10MinMovingLineGoingUp = (previousAvg10MinPrice < self.avg10MinPrice)
        self.consolidating = (abs(previousAvg5MinPrice - self.avg5MinPrice) <= self.consolidationDiffThreshold)

        if self.debugMode:
            Util.log(dump=False) # Show time, stdout only
            Util.log(f"last20MinPrices: {self.last20MinPrices}", level="Info", dump=False)
            # print(f"initState: {self.initState}")
            # print(f"previousAvg5MinPrice: {previousAvg5MinPrice}")
            print(f"avg5MinPrice: {self.avg5MinPrice}")
            print(f"avg5MinMovingLineGoingUp: {self.avg5MinMovingLineGoingUp}")
            # print(f"previousAvg10MinPrice: {previousAvg10MinPrice}")
            # print(f"avg10MinPrice: {self.avg10MinPrice}")
            # print(f"avg10MinMovingLineGoingUp: {self.avg10MinMovingLineGoingUp}")
            print(f"consolidating: {self.consolidating} ({previousAvg5MinPrice} --> {self.avg5MinPrice})")


    def quoteCallback(self, topic: str, quote: dict):
        # print(f"MyTopic: {topic}, MyQuote: {quote}")
        # Util.log("CurrentPrice: {}".format(quote["Close"][0]), level="Info", stdout=True, dump=False)
        timeString = quote["Time"]      # Should look like "21:59:56.123456"
        currentTime = datetime.datetime.strptime(timeString, "%H:%M:%S.%f").time()
        if Util.inBreakTime(currentTime):
            return
        currentPrice = quote["Close"][0] # Should look like 16000.0
        minute = currentTime.minute
        if minute != self.currentMinute:
            # Another minute passed, need to update average moving lines and (maybe) make some deals
            if self.currentMinute != 0 and minute != (self.currentMinute + 1) % 60:
                missedMinutes = minute - self.currentMinute if minute - self.currentMinute >= 0 else minute + 60 - self.currentMinute
                Util.log(f"Miss {missedMinutes} minutes of data", level="Warning")
            self.currentMinute = minute
            self.last20MinPrices.append(currentPrice)
            self.last20MinPrices.pop(0)
            self.updateKPIs()
            self.actionRequired = True
