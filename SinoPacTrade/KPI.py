# Library import
import datetime
import threading
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
        elif "InTime" in strategy:
            self.consolidationDiffThreshold5 = 0.21
            self.consolidationDiffThreshold10 = 0.19
        self.windowSize = 20
        assert(self.windowSize >= 2)

        # Flow control
        self.initState = True
        self.actionRequired = False # Every minute we check whether or not to buy or sell something.
        self.buffer = []

        # Indexes
        self.recentPrices = [0 for x in range(self.windowSize)] # The latest prices are push_back into the list
        self.recentTimes = [datetime.datetime.now() for x in range(self.windowSize)]
        self.recentSpeeds = [0 for x in range(self.windowSize - 1)]
        self.movingAvg5 = 0.0
        self.movingAvg5GoingUp = True
        self.movingAvg10 = 0.0
        self.movingAvg10GoingUp = True
        self.consolidating5 = True   # 5MA 盤整
        self.consolidating10 = True  # 10MA 盤整
        self.consecutiveUp = 0   # Number of consecutive price-going-up
        self.consecutiveUpAmplitude = 0   # max - min during the consecutive price going up
        self.consecutiveDown = 0 # Number of consecutive price-going-down
        self.consecutiveDownAmplitude = 0 # max - min during the consecutive price going down

        # private
        self.currentMinute = 0 # 0~59


    def start(self):
        monitor = threading.Thread(target=self.monitorAndProcessData)
        monitor.start()


    def monitorAndProcessData(self):
        while True:
            if self.actionRequired:
                # Wait for Strategy to consume the action 
                continue
            if not self.buffer:
                continue

            Util.log(f"Buffered count: {len(self.buffer)}", dump=False)
            pair = self.buffer.pop(0)
            timeString = pair[0]   # Should look like "21:59:56.123456"
            currentPrice = pair[1] # Should look like 16000.0
            currentDateTime = datetime.datetime.strptime(timeString, "%H:%M:%S.%f")
            currentTime = currentDateTime.time()

            if Util.inBreakTime(currentTime):
                continue

            update = False
            if self.strategy == "OneMinK":
                minute = currentTime.minute
                if minute != self.currentMinute:
                    # Another minute passed, need to update average moving lines and (maybe) make some deals
                    if self.currentMinute != 0 and minute != (self.currentMinute + 1) % 60:
                        missedMinutes = minute - self.currentMinute if minute - self.currentMinute >= 0 else minute + 60 - self.currentMinute
                        Util.log(f"Miss {missedMinutes} minutes of data", level="Warning")
                    self.currentMinute = minute
                    update = True

            elif "InTime" in self.strategy:
                update = True

            if update:
                previousPrice = self.recentPrices[-1]
                previousDateTime = self.recentTimes[-1]
                # TODO: Fix it: speed might be negative when changing to next day during 0:00am
                timeDiff = (currentDateTime - previousDateTime).total_seconds()
                speed = 0 if timeDiff == 0 else (currentPrice - previousPrice) / timeDiff
                self.recentSpeeds.append(speed)
                self.recentSpeeds.pop(0)
                self.recentPrices.append(currentPrice)
                self.recentPrices.pop(0)
                self.recentTimes.append(currentDateTime)
                self.recentTimes.pop(0)
                self.actionRequired = self.updateKPIs()


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
            # Update 5MA and 10MA
            idx = -1
            nonZeroCount = 0
            while idx >= -self.windowSize:
                if self.recentPrices[idx] != 0:
                    nonZeroCount += 1
                idx -= 1

            startValidIdx5 = self.windowSize - min(5, nonZeroCount)
            self.movingAvg5 = mean(self.recentPrices[startValidIdx5:])
            startValidIdx10 = self.windowSize - min(10, nonZeroCount)
            self.movingAvg10 = mean(self.recentPrices[startValidIdx10:])

            # Update consecution indexes
            maxPriceInSequence = self.recentPrices[-1]
            minPriceInSequence = self.recentPrices[-1]
            downSequenceStop = False
            upSequenceStop = False
            self.consecutiveUp = 1
            self.consecutiveDown = 1
            idx = -2
            while idx >= -self.windowSize and not (upSequenceStop and downSequenceStop):
                if not upSequenceStop:
                    if self.recentPrices[idx] <= self.recentPrices[idx+1]:
                        self.consecutiveUp += 1
                        minPriceInSequence = self.recentPrices[idx]
                    else:
                        upSequenceStop = True
                if not downSequenceStop:
                    if self.recentPrices[idx] >= self.recentPrices[idx+1]:
                        self.consecutiveDown += 1
                        maxPriceInSequence = self.recentPrices[idx]
                    else:
                        downSequenceStop = True
                idx -= 1

            self.consecutiveUpAmplitude = self.recentPrices[-1] - minPriceInSequence
            self.consecutiveDownAmplitude = maxPriceInSequence - self.recentPrices[-1]

        if self.strategy == "OneMinK":
            self.initState = (nonZeroCount < 5)
        elif "InTime" in self.strategy:
            self.initState = (nonZeroCount < self.windowSize)

        self.movingAvg5GoingUp = (previousMovingAvg5 < self.movingAvg5)
        self.movingAvg10GoingUp = (previousMovingAvg10 < self.movingAvg10)
        self.consolidating5 = (abs(previousMovingAvg5 - self.movingAvg5) <= self.consolidationDiffThreshold5)
        self.consolidating10 = (abs(previousMovingAvg10 - self.movingAvg10) <= self.consolidationDiffThreshold10)

        if self.debugMode:
            # Util.log(dump=False) # Show time, stdout only
            Util.log(f"recentPrices: {self.recentPrices}", level="Info", dump=False)
            # Util.log(f"recentTimes : {self.recentTimes}", level="Info", dump=False)
            # Util.log(f"recentSpeeds: {self.recentSpeeds}", level="Info", dump=False)
            # print(f"initState: {self.initState}")
            # print(f"previousMovingAvg5: {previousMovingAvg5}")
            print(f"movingAvg 5 / 10 GoingUp: {self.movingAvg5GoingUp} / {self.movingAvg10GoingUp}")
            # print(f"previousMovingAvg10: {previousMovingAvg10}")
            # print(f"consolidating5: {self.consolidating5} ({previousMovingAvg5} --> {self.movingAvg5})")
            print(f"consolidating10: {self.consolidating10} ({previousMovingAvg10} --> {self.movingAvg10})")
            print(f"consecutiveUp   count / amplitude: {self.consecutiveUp} / {self.consecutiveUpAmplitude}")
            print(f"consecutiveDown count / amplitude: {self.consecutiveDown} / {self.consecutiveDownAmplitude}")

        return not self.initState


    def quoteCallback(self, topic: str, quote: dict):
        # print(f"MyTopic: {topic}, MyQuote: {quote}")
        # Util.log("CurrentPrice: {}".format(quote["Close"][0]), level="Info", stdout=True, dump=False)
        # quote["Time"]      # Should look like "21:59:56.123456"
        # quote["Close"][0] # Should look like 16000.0
        self.buffer.append((quote["Time"], quote["Close"][0]))
