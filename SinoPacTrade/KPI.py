# Library import
import datetime
from statistics import mean

# Self defined class import
import Util

class KPI:
    def __init__(self, api, code, subcode, strategy, debugMode=True):
        # Settings
        self.debugMode = debugMode
        self.api = api
        self.code = code
        self.subcode = subcode
        self.strategy = strategy

        # Constants
        if strategy == "OneMinK":
            self.consolidationDiffThreshold5 = 0.61  # 0.01 to workaround for python float substraction error
            self.consolidationDiffThreshold10 = 0.41 # TODO: Not tuned yet
        elif strategy == "InTime":
            self.consolidationDiffThreshold5 = 0.21
            self.consolidationDiffThreshold10 = 0.19
        self.windowSize = 20

        # Flow control
        self.initState = True
        self.actionRequired = False # Every minute we check whether or not to buy or sell something.

        # Indexes
        self.recentPrices = [0 for x in range(self.windowSize)] # The latest prices are push_back into the list
        self.movingAvg5 = 0.0
        self.movingAvg5GoingUp = True
        self.movingAvg10 = 0.0
        self.movingAvg10GoingUp = True
        self.consolidating5 = True   # 5MA 盤整
        self.consolidating10 = True  # 10MA 盤整

        self.currentMinute = 0 # 0~59

    def getStreamingData(self):
        target = self.api.Contracts.Futures[self.code][self.subcode]
        self.api.quote.set_quote_callback(self.quoteCallback)
        self.api.quote.subscribe(target, quote_type="tick")


    def updateKPIs(self):
        previousMovingAvg5 = self.movingAvg5
        previousMovingAvg10 = self.movingAvg10

        # Handled initial states where no enough prices are collected
        if self.recentPrices[-1] == 0:
            self.movingAvg5 = 0.0
            self.movingAvg10 = 0.0
        else:
            # Update 5MA
            idx = -1
            nonZeroCount = 0
            while idx >= -5:
                if self.recentPrices[idx] == 0:
                    break
                nonZeroCount += 1
                idx -= 1
            startValidIdx = self.windowSize - nonZeroCount
            self.movingAvg5 = mean(self.recentPrices[startValidIdx:])

            # Update 10MA
            idx = -1
            nonZeroCount = 0
            while idx >= -10:
                if self.recentPrices[idx] == 0:
                    break
                nonZeroCount += 1
                idx -= 1
            startValidIdx = self.windowSize - nonZeroCount
            self.movingAvg10 = mean(self.recentPrices[startValidIdx:])

        if self.strategy == "OneMinK":
            self.initState = (nonZeroCount < 5)
        elif self.strategy == "InTime":
            self.initState = (nonZeroCount < 10)

        self.movingAvg5GoingUp = (previousMovingAvg5 < self.movingAvg5)
        self.movingAvg10GoingUp = (previousMovingAvg10 < self.movingAvg10)
        self.consolidating5 = (abs(previousMovingAvg5 - self.movingAvg5) <= self.consolidationDiffThreshold5)
        self.consolidating10 = (abs(previousMovingAvg10 - self.movingAvg10) <= self.consolidationDiffThreshold10)

        if self.debugMode:
            Util.log(dump=False) # Show time, stdout only
            Util.log(f"recentPrices: {self.recentPrices}", level="Info", dump=False)
            # print(f"initState: {self.initState}")
            # print(f"previousMovingAvg5: {previousMovingAvg5}")
            # print(f"movingAvg5: {self.movingAvg5}")
            print(f"movingAvg5GoingUp: {self.movingAvg5GoingUp}")
            # print(f"previousMovingAvg10: {previousMovingAvg10}")
            # print(f"movingAvg10: {self.movingAvg10}")
            print(f"movingAvg10GoingUp: {self.movingAvg10GoingUp}")
            print(f"consolidating5: {self.consolidating5} ({previousMovingAvg5} --> {self.movingAvg5})")
            print(f"consolidating10: {self.consolidating10} ({previousMovingAvg10} --> {self.movingAvg10})")

        return not self.initState


    def quoteCallback(self, topic: str, quote: dict):
        # print(f"MyTopic: {topic}, MyQuote: {quote}")
        # Util.log("CurrentPrice: {}".format(quote["Close"][0]), level="Info", stdout=True, dump=False)
        timeString = quote["Time"]      # Should look like "21:59:56.123456"
        currentPrice = quote["Close"][0] # Should look like 16000.0
        currentTime = datetime.datetime.strptime(timeString, "%H:%M:%S.%f").time()
        if Util.inBreakTime(currentTime):
            return

        if self.strategy == "OneMinK":
            minute = currentTime.minute
            if minute != self.currentMinute:
                # Another minute passed, need to update average moving lines and (maybe) make some deals
                if self.currentMinute != 0 and minute != (self.currentMinute + 1) % 60:
                    missedMinutes = minute - self.currentMinute if minute - self.currentMinute >= 0 else minute + 60 - self.currentMinute
                    Util.log(f"Miss {missedMinutes} minutes of data", level="Warning")
                self.currentMinute = minute
                self.recentPrices.append(currentPrice)
                self.recentPrices.pop(0)
                self.actionRequired = self.updateKPIs()

        elif self.strategy == "InTime":
            self.recentPrices.append(currentPrice)
            self.recentPrices.pop(0)
            self.actionRequired = self.updateKPIs()
