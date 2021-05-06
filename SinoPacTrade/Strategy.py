
class Strategy:
    def __init__(self, api, code, subcode, positionAction, positions, maxPositions, debugMode=True):
        # Common settings
        self.debugMode = debugMode
        self.api = api
        self.maxOpenPosition = maxPositions   # The maximum allowed num of open positions (unit: 口)
        self.code = code
        self.subcode = subcode

        # Constants
        self.handlingFee = 22 # per position

        # Flow control
        self.dealSignal = False

        # Strategy data
        self.positions = positions
        self.positionAction = positionAction # Allowed values are "B", "S" and ""
        self.profit = 0
        self.cost = 0 # transfer tax plus handling fees
        self.netIncome = 0 # equal to (profit - cost)
        self.contractSize = 50 if code == "MXF" else 0 # Only support MXF (小台) currently