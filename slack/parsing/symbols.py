from pyparsing import alphanums, CharsNotIn, OneOrMore, Regex, Word

emoji = Regex(':[\S]+:').setResultsName('emoji')
message = OneOrMore(Word(alphanums + "#")).setResultsName('message')

tail = CharsNotIn('').setResultsName('tail')
channel_name = Word(alphanums).setResultsName('channel')
