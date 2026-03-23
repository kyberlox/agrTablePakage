import operator

def start(x):
    return x

OPERATIONS = {
    'start': start, 
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,  
    '//': operator.floordiv,  
    '%': operator.mod,
    '**': operator.pow,
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>': operator.ge,
    '&': operator.and_,
    '|': operator.or_,
    '^': operator.xor,
    '=': operator.eq,
} 

