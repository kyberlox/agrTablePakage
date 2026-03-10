import operator
        
OPERATIONS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,  
    '//': operator.floordiv,  
    '%': operator.mod,
    '**': operator.pow,
    '<<': operator.lshift,
    '>>': operator.rshift,
    '&': operator.and_,
    '|': operator.or_,
    '^': operator.xor,
} 

