from pyparsing import alphanums, CaselessLiteral, CharsNotIn, OneOrMore, Regex, Word

emoji = Regex(':[\S]+:').setResultsName('emoji')
message = OneOrMore(Word(alphanums + "#")).setResultsName('message')

tail = CharsNotIn('').setResultsName('tail')
channel_name = Word(alphanums + '-').setResultsName('channel')


def flag(name):
    return CaselessLiteral('--' + name).setResultsName(name)
