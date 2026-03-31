import operator

def start(x):
    return x

PRIORITY = ("<-", "**", "*", "/", "+", "-")

OPERATIONS = {
    '<-': start, 
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,  
    '//': operator.floordiv, # деление без остатка 
    '%': operator.mod, # остаток от деления
    '**': operator.pow, # число в степень
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>': operator.ge,
    '&': operator.and_,
    '|': operator.or_,
    '=': operator.eq,
} 

