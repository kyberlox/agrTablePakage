import operator
        
OPERATIONS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,  
    '//': operator.floordiv,  
    '%': operator.mod,
    '**': operator.pow,
    '<': "меньше",
    '>': "больше",
    '&': operator.and_,
    '|': operator.or_,
    '^': operator.xor,
} 

