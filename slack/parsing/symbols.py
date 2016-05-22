from pyparsing import alphanums, CaselessLiteral, CharsNotIn, OneOrMore, printables, Regex, Word

emoji = Regex(':[\S]+:').setResultsName('emoji')
message = OneOrMore(Word(alphanums + "#")).setResultsName('message')

tail = CharsNotIn('').setResultsName('tail')
channel_name = Word(alphanums + '-').setResultsName('channel')

user_name = Word(alphanums + '-_.')

link = Word(printables)


def flag(name):
    return CaselessLiteral('--' + name).setResultsName(name)


def flag_with_arg(name, argtype):
    return CaselessLiteral('--' + name) + argtype.setResultsName(name)
