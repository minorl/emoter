import abc

class SlackParser(metaclass=abc.ABCMeta):
    def parse(self, s):
        return self.expr.parseString(s)
