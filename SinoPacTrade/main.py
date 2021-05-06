import argparse
from threading import Event

from MakeMoney import MakeMoney
import Util

def getArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", "-s", required=True, choices=["OneMinK", "InTime", "InTimeReverse"], help="strategy")
    return parser.parse_args()

if __name__ == '__main__':
    args = getArguments()
    moneyMaker = MakeMoney()
    moneyMaker.login(enableTrading=False)

    # Wait until enough data are fetched
    while not moneyMaker.loginDone:
        continue

    Util.log("Login completed", level="Info")

    moneyMaker.setStrategy(args.strategy)

    moneyMaker.getAccountData()

    # 'code' can be one of the following (以202103小型台指為例): "MXF202103", "MXFC1"
    # moneyMaker.getHistoryData(code="MXF", subcode="MXF202103", start="2021-01-04", end="2021-01-05")

    # moneyMaker.getStreamingData(code="MXF", subcode="MXF202105")

    # moneyMaker.testTrading(code="MXF", subcode="MXF202105", orderType="ROD", priceType="LMT")
    # moneyMaker.testTrading(code="MXF", subcode="MXF202105", orderType="IOC", priceType="MKT")
    moneyMaker.startTrading(code="MXF", subcode="MXF202105", orderType="IOC", priceType="MKT")

    # Prevent the main thread from exiting
    block = Event()
    block.wait()

    print("Close MakeMoney. Bye!")

