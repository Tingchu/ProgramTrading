# Library import
import datetime
import time
import matplotlib.pyplot as plt
from statistics import mean

# Self defined class import
import KPI
import Util
from Strategy import Strategy

class OneMinKStrategy(Strategy):
    def __init__(self, api, code, subcode, positionAction, positions, maxPositions, debugMode=True):
        super(OneMinKStrategy, self).__init__(api, code, subcode, positionAction, positions, maxPositions, debugMode)
        Util.log(f"Create OneMinKStrategy with code:{code}, subcode:{subcode}, positions:{positions}, maxPositions:{maxPositions}, debugMode:{debugMode}", level="Info")

        self.kpi = KPI.KPI(api, code, subcode, "OneMinK", debugMode)

        # Chart
        # plt.show()
        # self.axes = plt.gca()
        # self.lines, = self.axes.plot([], [], color='green', linestyle='-', linewidth=2, marker='o', markerfacecolor='black', markersize=8)
        # Util.initializeChart(self.lines, self.axes)

    def orderCallback(self, stat, msg):
        if stat == "FDEAL":
            positions = Util.getPositions(self.api)
            self.positions = positions[1]
            self.positionAction = positions[0]
            self.dealSignal = True

            Util.log("Deal action: {}, price: {}, quantity: {}".format(msg["action"], msg["price"], msg["quantity"]), level="Info")
            Util.log(f"positions: {self.positions}, positionAction: {self.positionAction}")

        elif stat == "FORDER":
            pass

    def Run(self, orderType="ROD", priceType="LMT"):
        if orderType == "ROD":
            if priceType != "LMT":
                Util.log("Order type is ROD but price type is not LMT. Abort.", level="Error")
                return False
        elif orderType == "IOC":
            if priceType != "MKT":
                Util.log("Order type is IOC but price type is not MKT. Abort.", level="Error")
                return False

        # KPI.getStreamingData() will create a thread by api.quote.subscribe
        self.kpi.getStreamingData()
        # KPI.start() will create another thread to handle data
        self.kpi.start()

        self.api.set_order_callback(self.orderCallback)

        # Start making money
        target = self.api.Contracts.Futures[self.code][self.subcode]
        while True:
            time.sleep(1)
            if not self.kpi.actionRequired:
                continue

            self.kpi.actionRequired = False

            if self.kpi.movingAvg5GoingUp:
                priceGoingUp = self.kpi.recentPrices[-1] > self.kpi.recentPrices[-2]
                if priceGoingUp:
                    numOpenPosition = len(self.positions)
                    orderPrice = self.kpi.recentPrices[-1]
                    if self.positionAction == "B" and numOpenPosition >= self.maxOpenPosition:
                        Util.log(f"Number of open positions ({numOpenPosition}) reached upper limit ({self.maxOpenPosition})", level="Info")
                    elif self.positionAction == "S" and     \
                         self.kpi.consolidating5 == True and \
                         orderPrice > mean(self.positions) - 2:
                        Util.log("Attempting to close out positions (buy) but consolidating", level="Info")
                    else:
                        quantity = 1
                        if self.debugMode:
                            if not self.positions: # No positions
                                self.positions.append(orderPrice)
                                self.positionAction = "B"
                            elif self.positionAction == "B":
                                self.positions.append(orderPrice)
                            elif self.positionAction == "S":
                                sellPrice = self.positions.pop(0)
                                if not self.positions:
                                    self.positionAction = ""
                                self.profit += ((sellPrice - orderPrice) * self.contractSize)
                            self.cost += (int(orderPrice * 50 * 0.00002) + self.handlingFee)
                            self.netIncome = self.profit - self.cost
                            Util.log(f"===  Buy at {orderPrice} positions: {self.positions} ({self.positionAction}), profit: {self.profit}, cost: {self.cost}, net income: {self.netIncome}  ===", level="Info")
                        else:
                            order = self.api.Order(
                                action="Buy",
                                price=orderPrice,
                                quantity=quantity,
                                order_type=orderType, # ROD: Rest of Day, IOC: Immediate or Cancel, FOK, Fill or Kill
                                price_type=priceType, # LMT: limit, MKT: market, MKP, marget range
                                octype="Auto",        # Auto: ??????, NewPosition: ??????, Cover: ??????, DayTrade: ??????
                                account=self.api.futopt_account
                            )
                            trade = self.api.place_order(target, order)
                            Util.log(f"Trade status: {trade.status.status}", "Info")

                            result = self.waitForDeal(trade)
                            if result == "Dealed":
                                numOpenPosition += quantity
                                self.cost += (int(orderPrice * 50 * 0.00002) + self.handlingFee)
                                Util.log(f"=== Buy at {orderPrice} ===", level="Info")
                                Util.log(f"=== Current open interest: {numOpenPosition} ===", level="Info")
                            else:
                                Util.log(f"Cancelling order due to the result of waiting for deal: {result}", level="Warning")
                                self.cancelOrder(trade)

            else: # moving line going down
                priceGoingDown = self.kpi.recentPrices[-1] < self.kpi.recentPrices[-2]
                if priceGoingDown:
                    # self.maxOpenPosition should always be positive
                    numOpenPosition = len(self.positions)
                    orderPrice = self.kpi.recentPrices[-1]
                    if self.positionAction == "S" and numOpenPosition >= self.maxOpenPosition:
                        Util.log(f"Number of open positions ({numOpenPosition}) reached lower limit ({self.maxOpenPosition})", level="Info")
                    elif self.positionAction == "B" and     \
                         self.kpi.consolidating5 == True and \
                         orderPrice < mean(self.positions) + 2:
                        Util.log("Attempting to close out positions (sell) but consolidating", level="Info")
                    else:
                        quantity = 1
                        if self.debugMode:
                            if not self.positions: # No positions
                                self.positions.append(orderPrice)
                                self.positionAction = "S"
                            elif self.positionAction == "S":
                                self.positions.append(orderPrice)
                            elif self.positionAction == "B":
                                buyPrice = self.positions.pop(0)
                                if not self.positions:
                                    self.positionAction = ""
                                self.profit += ((orderPrice - buyPrice) * self.contractSize)
                            self.cost += (int(orderPrice * 50 * 0.00002) + self.handlingFee)
                            self.netIncome = self.profit - self.cost
                            Util.log(f"=== Sell at {orderPrice} positions: {self.positions} ({self.positionAction}), profit: {self.profit}, cost: {self.cost}, net income: {self.netIncome} ===", level="Info")
                        else:
                            order = self.api.Order(
                                action="Sell",
                                price=orderPrice,
                                quantity=quantity,
                                order_type=orderType, # ROD: Rest of Day, IOC: Immediate or Cancel, FOK, Fill or Kill
                                price_type=priceType, # LMT: limit, MKT: market, MKP, marget range
                                octype="Auto",        # Auto: ??????, NewPosition: ??????, Cover: ??????, DayTrade: ??????
                                account=self.api.futopt_account
                            )
                            trade = self.api.place_order(target, order)
                            Util.log(f"Trade status: {trade.status.status}", "Info")

                            result = self.waitForDeal(trade)
                            if result == "Dealed":
                                numOpenPosition -= quantity
                                self.cost += (int(orderPrice * 50 * 0.00002) + self.handlingFee)
                                Util.log(f"=== Sell at {orderPrice} ===", level="Info")
                                Util.log(f"=== Current open interest: {numOpenPosition} ===", level="Info")
                            else:
                                Util.log(f"Cancelling order due to the result of waiting for deal: {result}", level="Warning")
                                self.cancelOrder(trade)
        
    def cancelOrder(self, trade):
        # cancel
        self.api.update_status(self.api.futopt_account)
        self.api.cancel_order(trade) # Test OK
        self.api.update_status(self.api.futopt_account)
        Util.log(f"Cancelled status:{trade}", level="Warning")

    def waitForDeal(self, trade):
        # Call api.update_status to see the change of trade status
        maxWaitingSecond = 10
        timeout = 0
        while timeout < maxWaitingSecond:
            # self.api.update_status(self.api.futopt_account)
            time.sleep(1)
            if self.dealSignal == True:
                self.dealSignal = False
                return "Dealed"
            # if trade.status.status == "PendingSubmit":
            #     timeout += 1
            #     Util.log("trade status: submitting...", level="Info")
            
            # elif trade.status.status == "Submitted":
            #     Util.log("trade submit succeeded", level="Info")
            
            # elif trade.status.status == "Failed":
            #     Util.log("trade submit failed", level="Warning")
            #     return "Failed"

            # elif trade.status.status == "Filled":
            #     Util.log("trade totally dealed", level="Info")
            #     return "Filled"
            
            # elif trade.status.status == "Filling":
            #     Util.log("trade partially dealed", level="Info")
            
            # elif trade.status.status == "Cancelled":
            #     Util.log("trade cancelled", level="Warning")
            #     return "Cancelled"
            
            # else:
            #     Util.log("Unknown status: {}".format(trade.status.status), level="Error")
            #     return "Unknown"

        return "Timeout"
