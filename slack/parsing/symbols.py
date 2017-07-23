from pyparsing import alphanums, nums, CaselessLiteral, CharsNotIn, delimitedList, OneOrMore, originalTextFor, printables, QuotedString, quotedString, Regex, removeQuotes, Suppress, White, Word

emoji = Regex(':[\\S]+:').setResultsName('emoji')
message = OneOrMore(Word(alphanums + "#")).setResultsName('message')


def tail(name):
    return Suppress(White(max=1)) + OneOrMore(CharsNotIn('')).setResultsName(name)

channel_name = Word(alphanums + '-').setResultsName('channel')

user_name = Word(alphanums + '-_.')

link = Word(printables)

int_num = Word(nums)

dumb_single_quotes = QuotedString("‘", endQuoteChar="’", escChar="\\")
dumb_double_quotes = QuotedString("“", endQuoteChar="”", escChar="\\")
quotedString.addParseAction(removeQuotes)
comma_list = delimitedList((dumb_single_quotes | dumb_double_quotes | quotedString
                            | originalTextFor(OneOrMore(Word(printables, excludeChars=","))))).setResultsName('comma_list')


def flag(name):
    dashes = '--' if len(name) > 1 else '-'
    return CaselessLiteral(dashes + name).setResultsName(name)


def flag_with_arg(name, argtype):
    dashes = '--' if len(name) > 1 else '-'
    return CaselessLiteral(dashes + name) + argtype.setResultsName(name)
