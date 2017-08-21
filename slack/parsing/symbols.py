from pyparsing import alphanums, nums, CaselessLiteral, CharsNotIn, OneOrMore, printables, Regex, Suppress, White, Word

emoji = Regex(':[\S]+:').setResultsName('emoji')
message = OneOrMore(Word(alphanums + "#")).setResultsName('message')

def tail(name):
    return Suppress(White(max=1)) + CharsNotIn('').setResultsName(name)

channel_name = Word(alphanums + '-').setResultsName('channel')

user_name = Word(alphanums + '-_.')

link = Word(printables)

int_num = Word(nums)

def flag(name):
    dashes = '--' if len(name) > 1 else '-'
    return CaselessLiteral(dashes + name).setResultsName(name)


def flag_with_arg(name, argtype):
    dashes = '--' if len(name) > 1 else '-'
    return CaselessLiteral(dashes + name) + argtype.setResultsName(name)
