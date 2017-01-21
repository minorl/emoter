from pyparsing import alphanums, nums, CaselessLiteral, CharsNotIn, OneOrMore, printables, Regex, Suppress, White, Word

emoji = Regex(':[\S]+:').setResultsName('emoji')
message = OneOrMore(Word(alphanums + "#")).setResultsName('message')

def tail(name):
    return Suppress(White(exact=1)) + CharsNotIn('').setResultsName(name)
channel_name = Word(alphanums + '-').setResultsName('channel')

user_name = Word(alphanums + '-_.')

link = Word(printables)

int_num = Word(nums)

def flag(name):
    return CaselessLiteral('--' + name).setResultsName(name)


def flag_with_arg(name, argtype):
    return CaselessLiteral('--' + name) + argtype.setResultsName(name)
