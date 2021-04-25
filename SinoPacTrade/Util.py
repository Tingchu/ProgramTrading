import datetime

def log(msg, level="", stdout=True, dump=True):
    dateAndTime = datetime.datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
    levelString = "" if level == "" else f"[{level}]"
    outputString = f"{dateAndTime} : {msg}"
    if stdout:
        print(outputString)
    if dump:
        with open("MoneyMaker.log", "a") as log:
            log.write(f"{dateAndTime} : {msg}\n")


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
