
class Test:
    def __init__(self):
        self.aa = 3
        if self.aa == 3:
            self.bb = 5

    def func(self):
        if self.aa == 3:
            print(self.bb)


test = Test()
test.func()