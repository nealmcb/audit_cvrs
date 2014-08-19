"""
audit_cvrs utility functions and classes
"""

import re
import logging
#import audit_cvrs.models as models

def selection_to_cvr(batch, sequence):
    """return CVR file name given scanner batch and sequence number from auditTools for OpenCount

    >>> selection_to_cvr('s1b1', '288')
    'Scanner1~000288_side0.txt'
    >>> selection_to_cvr('s1b1', '3251234')
    'Scanner1~3251234_side0.txt'
    >>> selection_to_cvr('s1b11', '10041')
    'Scanner1~0010041_side0.txt'
    >>> selection_to_cvr('s3b16', '665030')
    'Scanner3~665030_side0.txt'

    FIXME: do this all in more configurable way - format expresion/statement?
    """
    
    OpenCount_batch_re = re.compile(r's(?P<scanner>[0-9]+)b(?P<batch>[0-9]+)')
    m = re.match(OpenCount_batch_re, batch)

    scanner = m.group('scanner')

    if scanner == "1"  and  len(sequence) >= 5:
        filled_sequence = sequence.zfill(7)
    else:
        filled_sequence = sequence.zfill(6)

    return "Scanner%s~%s_side0.txt" % (scanner, filled_sequence)

if __name__ == '__main__':
     import doctest
     doctest.testmod()
