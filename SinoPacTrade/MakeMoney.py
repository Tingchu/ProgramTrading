import pandas as pd
import shioaji as sj
import sys
import time
from datetime import date
from datetime import timedelta

import InTimeStrategy
import OneMinKStrategy
import Util

class MakeMoney:
    def __init__(self):
        self.debugMode = True
        self.api = sj.Shioaji()
        self.loginFetchItemNum = 0
        self.loginMaxFetchItemNum = 4
        self.loginDone = False
        self.availableStrategies = ["OneMinK", "InTime"]
        self.strategy = ""
        self.password = "wDVT10203054"
        self.personID = "B122547371"
        self.caPassword = "wDVT21504"
        self.caPersonID = "B122547371"

        # Account status
        self.margin = 0  # 可動用保證金
        self.riskIndicator = 0 # 風險指標
        # self.openPositions = 0 # 未平倉口數
        self.closingPrices = [] # 各未平倉部位成交價
        self.positionAction = ""
        # print(dir(self.api.quote))

        # live KPIs

    def login(self, enableTrading=False):
        try:
            self.api.login(
                person_id=self.personID,
                passwd=self.password,
                contracts_cb=self.loginCallback
                # contracts_cb=lambda security_type: print(f"{repr(security_type)} Fetch done")
            )
            if enableTrading:
                self.api.activate_ca(
                    ca_path="/mnt/hgfs/Ubuntu16.04_Shared_Folder/SinoPac.pfx",
                    ca_passwd=self.caPassword,
                    person_id=self.caPersonID)
            else:
                self.loginDone = True
        except Exception as exception:
            self.handleError(str(exception))


    def loginCallback(self, security_type):
        print(f"{repr(security_type)} Fetched")
        self.loginFetchItemNum += 1
        if self.debugMode:
            if security_type == "FUT":
                self.loginDone = True
        else:
            if self.loginFetchItemNum >= self.loginMaxFetchItemNum:
                self.loginDone = True

    
    def getAccountData(self):
        margin = self.api.get_account_margin()
        print("margin:")
        # print(margin.data())
        self.margin = margin.data()[0]["OrderPSecurity"]
        self.riskIndicator = margin.data()[0]["Flow"]
        print(f"margin: {self.margin}, riskIndicator: {self.riskIndicator}")

        balance = self.api.account_balance()
        print("balance:")
        print(balance)

        startDate = (date.today() - timedelta(days=2)).strftime('%Y%m%d')
        accountSettleProfitLoss = self.api.get_account_settle_profitloss(summary="Y", start_date=startDate)
        print("accountSettleProfitLoss:")
        print(accountSettleProfitLoss.data())

        # stockPosition = self.api.list_positions(self.api.stock_account)
        # print("stockPosition:")
        # print(stockPosition)

        # futurePosition = self.api.list_positions(self.api.futopt_account)
        # print("futurePosition:")
        # print(futurePosition)

        # stockSettlement = self.api.list_settlements(self.api.stock_account)
        # print("stockSettlement:")
        # print(stockSettlement)

        # futureSettlement = self.api.list_settlements(self.api.futopt_account)
        # print("futureSettlement:")
        # print(futureSettlement)

        # query_type = '0': detail; '1': summary
        # If detail, return a list with each position having one dict, volume = 1 and "ContractAverPrice" = each position's closing price
        # If summary, return a list with only one dict, averaging all positions' closing price as "ContractAverPrice"
        positions = self.api.get_account_openposition(query_type='0', account=self.api.futopt_account)
        positions = positions.data() # get the list
        print("positions:")
        print(positions)

        currentPositions = Util.getPositions(self.api)
        self.closingPrices = currentPositions[1]
        self.positionAction = currentPositions[0]

        print(f"Positions: {self.closingPrices} action: {self.positionAction}")

    def setStrategy(self, strategy):
        if strategy not in self.availableStrategies:
            self.handleError("Unknown strategy: {}".format(strategy))
        self.strategy = strategy

    def quoteCallback(self, topic: str, quote: dict):
        print(f"MyTopic: {topic}, MyQuote: {quote}")

    def orderCallback(self, stat, msg):
        print(type(stat))
        if stat == "FDEAL":
            print("stat: FDEAL")
            print("Deal price: {}, quantity: {}, action: {}".format(msg["price"], msg["quantity"], msg["action"]))
        elif stat == "FORDER":
            print("stat: FORDER")
        # print(f"My order callback, stat: {stat}, msg: {msg}")

    def getStreamingData(self, code, subcode):
        target = self.api.Contracts.Futures[code][subcode]
        self.api.quote.set_quote_callback(self.quoteCallback)
        self.api.quote.subscribe(target, quote_type="tick")

    def getHistoryData(self, code, subcode, start, end):
        # TODO
        # print(self.api.Contracts.Futures)
        # print(self.api.Contracts.Futures.MXF)
        # print(self.api.Contracts.Futures.MXF.MXF202103)
        # print(self.api.Contracts.Futures[code][subcode])

        target = self.api.Contracts.Futures[code][subcode]
        print("target:")
        print(target)
        ticks = self.api.ticks(target, "2021-03-09")
        # print(ticks)
        df = pd.DataFrame({**ticks})
        df.ts = pd.to_datetime(df.ts)
        print(df.head())

    def updateTradeStatus(self):
        if self.debugMode:
            print("api.update_status")
        try:
            self.api.update_status(self.api.futopt_account)
        except Exception as exception:
            print(exception)

    def startTrading(self, code, subcode, orderType="ROD", priceType="LMT"):
        if self.strategy == "OneMinK":
            woringStrategy = OneMinKStrategy.OneMinKStrategy(self.api, code, subcode, positionAction=self.positionAction, positions=self.closingPrices, maxPositions=2, debugMode=self.debugMode)
            woringStrategy.Run(orderType, priceType)
        elif self.strategy == "InTime":
            woringStrategy = InTimeStrategy.InTimeStrategy(self.api, code, subcode, positionAction=self.positionAction, positions=self.closingPrices, maxPositions=2, debugMode=self.debugMode)
            woringStrategy.Run(orderType, priceType)

    def testTrading(self, code, subcode, orderType="ROD", priceType="LMT"):
        target = self.api.Contracts.Futures[code][subcode]
        self.api.set_order_callback(self.orderCallback)
        order = self.api.Order(
            action="Buy",
            price=33333,
            quantity=1,
            order_type=orderType,   # ROD: Rest of Day, IOC: Immediate or Cancel, FOK, Fill or Kill
            price_type=priceType,   # LMT: limit, MKT: market, MKP, marget range
            octype="Auto",          # Auto: 自動, NewPosition: 新倉, Cover: 平倉, DayTrade: 當沖
            account=self.api.futopt_account
        )
        trade = self.api.place_order(target, order) # Test OK
        print("trade status:")
        print(trade.status.status)

        # Call api.update_status to see the change of trade status
        while True: # Test OK
            time.sleep(1)
            self.updateTradeStatus()
            print(trade.status.status)
            if trade.status.status == "PendingSubmit":
                print("trade status: submitting...")
                continue
            elif trade.status.status == "Submitted":
                print("trade submit succeeded")
            elif trade.status.status == "Failed":
                print("trade submit failed")
                break
            elif trade.status.status == "Filled":
                print("trade totally dealed")
                break
            elif trade.status.status == "Filling":
                print("trade partially dealed")
            elif trade.status.status == "Cancelled":
                print("trade cancelled")
                break
            else:
                print("Unknown status: {}".format(trade.status.status))
                break

        # list
        # print("list trades:")
        # self.updateTradeStatus()
        # self.api.list_trades()

        # self.updateTradeStatus()
        if trade.status.status == "Failed":  # Test OK by set order.price to a very big number
            print("trade failed by some reason...")
            return

        # cancel
        # self.api.cancel_order(trade) # Test OK
        # self.updateTradeStatus()
        # print("Cancelled status:")
        # print(trade)

    def handleError(self, errMsg):
        sys.exit(errMsg)