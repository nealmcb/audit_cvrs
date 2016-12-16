#!/usr/bin/env python
"""
rlacalc: Risk-Limiting Audit calculations
~~~~~~~~

rlacalc computes expected sample size for a Risk-Limiting Audit (RLA),
 as described in
  Super-Simple Simultaneous Single-Ballot Risk-Limiting Audits
  https://www.usenix.org/legacy/events/evtwote10/tech/full_papers/Stark.pdf

%InsertOptionParserUsage%

Example: calculate initial sample size for RLA with 2% margin and default 10% risk limit:
 rlacalc.py -m 2

Calculate sample size needed for RLA with 2% margin and default 10% risk limit and no errors:
 rlacalc.py -m 2 -n

"""

import os
import sys
import logging
from optparse import OptionParser
import math

__author__ = "Neal McBurnett <http://neal.mcburnett.org/>"
__version__ = "0.1.0"
__date__ = "2016-12-04"
__copyright__ = "Copyright (c) 2016 Neal McBurnett"
__license__ = "MIT"

parser = OptionParser(prog="rlacalc.py", version=__version__)

parser.add_option("-m", "--margin",
  type="float",
  help="[REQUIRED] margin of victory, in percent")

parser.add_option("-n", "--nmin",
  action="store_true", default=False,
  help="Calculate nmin, not nminFromRates")

parser.add_option("-r", "--alpha",
  type="float", default=10.0,
  help="maximum risk level (alpha), in percent")

parser.add_option("-g", "--gamma",
  type="float", default=1.03905,
  help="gamma: error inflation factor, greater than 1.0")

parser.add_option("-l", "--lambdatol",
  type="float", default=50.0,
  help="lambda: error tolerance for overstatements in percent, less than 100.0")

parser.add_option("--or1",
  type="float", default=0.001,
  help="1-vote overstatement rate")

parser.add_option("--ur1",
  type="float", default=0.001,
  help="1-vote understatement rate")

parser.add_option("--or2",
  type="float", default=0.0001,
  help="2-vote overstatement rate")

parser.add_option("--ur2",
  type="float", default=0.0001,
  help="2-vote understatement rate")

parser.add_option("--roundUp1", "--r1",
  action="store_false", default=True,
  help="Round up 1-vote differences")

parser.add_option("--roundUp2", "--r2",
  action="store_true", default=False,
  help="Round up 2-vote differences")

parser.add_option("--o1",
  type="int", default=0,
  help="1-vote overstatements")

parser.add_option("--u1",
  type="int", default=0,
  help="1-vote understatements")

parser.add_option("--o2",
  type="int", default=0,
  help="2-vote overstatements")

parser.add_option("--u2",
  type="int", default=0,
  help="2-vote understatements")

parser.add_option("-d", "--debuglevel",
  type="int", default=logging.WARNING,
  help="Set logging level to debuglevel: DEBUG=10, INFO=20,\n WARNING=30 (the default), ERROR=40, CRITICAL=50")

parser.add_option("--test",
  action="store_true", default=False,
  help="Run tests")

# incorporate OptionParser usage documentation in our docstring
__doc__ = __doc__.replace("%InsertOptionParserUsage%\n", parser.format_help())

def nmin(alpha=0.1, gamma=1.03905, margin=0.05, o1=0, o2=0, u1=0, u2=0, lambdatol=0.5):
    """Return needed sample size during a Risk-Limiting Audit
    alpha: maximum risk level (alpha), as a fraction
    gamma: error inflation factor, greater than 1.0
    margin: margin of victory, as a fraction
    o1: 1-vote overstatements
    u1: 1-vote understatements
    o2: 2-vote overstatements
    u2: 2-vote understatements
    lambdatol: error tolerance for overstatements as a fraction, less than 1.0  # FIXME - implement this

    FIXME: return ints?

    Based on Javascript code in https://www.stat.berkeley.edu/~stark/Java/Html/auditTools.htm

    Tests, more exact than but based on p. 5 of http://www.stat.berkeley.edu/~stark/Preprints/gentle12.pdf
    >>> nmin(margin=0.2)
    24.0
    >>> nmin(margin=0.1)
    48.0
    >>> nmin(margin=0.002)
    2393.0
    >>> nmin(margin=0.05, o1=1)
    123.0
    >>> nmin(margin=0.005, o1=1, u1=1)
    1067.0
    >>> nmin(margin=0.05)
    96.0

    FIXME: confirm these
    >>> nmin(margin=0.05, alpha=0.2)
    67.0

    From p. 9 of https://www.usenix.org/legacy/events/evtwote10/tech/full_papers/Stark.pdf
    
    >>> nmin(margin=0.02, gamma=1.1, lambdatol=0.1) # FIXME - implement entry of lambda other than default of 50%
    293.0

    FIXME: Look at p.10, Table 4 - seem off by a factor of about 3
    # >>> nmin(margin=0.05, alpha=0.1, gamma=1.1, lambdatol=0.5)  # produces 102, not 305 as in table
    And what does this mean?
     The values of the simultaneous risk bound P(n, n1, n2; U, gamma)
     are generally on the order of 2/3 of the nominal values in the column headings.
    """

    logging.debug("%s, %s, %s, %d, %d, %d, %d, %s" % (alpha, gamma, margin, o1, o2, u1, u2, lambdatol))

    if gamma <= 1.0:
        raise ValueError("gamma is %f but must be > 1.0" % gamma)

    if lambdatol >= 1.0:
        raise ValueError("lambdatol is %f but must be < 1.0" % lambdatol)

    return max(
        o1 + o2 + u1 + u1,
        math.ceil(-2 * gamma * ( math.log(alpha) +
                                 o1 * math.log(1 - 1 / (2 * gamma)) +
                                 o2 * math.log(1 - 1 / gamma) +
                                 u1 * math.log(1 + 1 / (2 * gamma)) +
                                 u2 * math.log(1 + 1 / gamma)) / margin ))

def nminFromRates(alpha=0.1, gamma=1.03905, margin=0.05, or1=0.001, or2=0.0001, ur1=0.001, ur2=0.0001, roundUp1=True, roundUp2=False, lambdatol=0.5):
    """Return expected sample size for a Risk-Limiting Audit
    alpha: maximum risk level (alpha), as a fraction
    gamma: error inflation factor, greater than 1.0
    margin: margin of victory, as a fraction
    or1: 1-vote overstatement rate
    ur1: 1-vote understatement rate
    or2: 2-vote overstatement rate
    ur2: 2-vote understatement rate
    roundUp1: whether to round up 1-vote differences
    roundUp2: whether to round up 2-vote differences
    lambdatol: error tolerance for overstatements as a fraction, less than 1.0

    Based on Javascript code in https://www.stat.berkeley.edu/~stark/Java/Html/auditTools.htm
    """

    n0 = (-2 * gamma * math.log(alpha) /
          (margin + 2 * gamma * (or1 * math.log(1-1/(2 * gamma)) +
                                 or2 * math.log(1 - 1/gamma) + ur1 * math.log(1 + 1/(2 * gamma)) + ur2 * math.log(1 + 1/gamma))
       ) )

    for _ in xrange(3):
        if (roundUp1):
             o1 = math.ceil(or1 * n0)
             u1 = math.ceil(ur1 * n0)
        else:
             o1 = round(or1 * n0)
             u1 = round(ur1 * n0)

        if (roundUp2):
             o2 = math.ceil(or2 * n0)
             u2 = math.ceil(ur2 * n0)
        else:
             o2 = round(or2 * n0)
             u2 = round(ur2 * n0)

        n0 = nmin(alpha, gamma, margin, o1, o2, u1, u2, lambdatol)

    return(n0)

def checkRequiredArguments(opts, parser):
    "Make sure that any options described as '[REQUIRED]' are present"

    missing_options = []
    for option in parser.option_list:
        if option.help.startswith('[REQUIRED]') and eval('opts.' + option.dest) == None:
            missing_options.extend(option._long_opts)

    if len(missing_options) > 0:
        parser.error('Missing REQUIRED parameters: ' + str(missing_options))

def _test():
    import doctest
    return doctest.testmod()

def main(parser):
    "Run rlacalc with given OptionParser arguments"

    (opts, args) = parser.parse_args()

    #configure the root logger.  Without filename, default is StreamHandler with output to stderr. Default level is WARNING
    logging.basicConfig(level=opts.debuglevel)   # ..., format='%(message)s', filename= "/file/to/log/to", filemode='w' )

    if opts.test:
        _test()
        sys.exit(0)

    checkRequiredArguments(opts, parser)

    if opts.nmin:
        samplesize = nmin(opts.alpha / 100.0, opts.gamma, opts.margin / 100.0, opts.o1, opts.o2, opts.u1, opts.u2, opts.lambdatol / 100.0)
        print("Sample size = %d for margin %g%%, risk %g%%, gamma %g, o1 %g, o2 %g, u1 %g, u2 %g, lambda %g%%" % (samplesize, opts.margin, opts.alpha, opts.gamma, opts.o1, opts.o2, opts.u1, opts.u2, opts.lambdatol))
    else:
        samplesize = nminFromRates(opts.alpha / 100.0, opts.gamma, opts.margin / 100.0, opts.or1, opts.or2, opts.ur1, opts.ur2, opts.roundUp1, opts.roundUp2, opts.lambdatol / 100.0)

        print("Sample size = %d for margin %g%%, risk %g%%, gamma %g, or1 %g, or2 %g, ur1 %g, ur2 %g, roundUp1 %g, roundUp2 %g, lambda %g%%" % (samplesize, opts.margin, opts.alpha, opts.gamma, opts.or1, opts.or2, opts.ur1, opts.ur2, opts.roundUp1, opts.roundUp2, opts.lambdatol))

if __name__ == "__main__":
    main(parser)