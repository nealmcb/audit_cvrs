#!/usr/bin/env python
"""
rlacalc: Risk-Limiting Audit calculations
~~~~~~~~

rlacalc computes the expected sample size for a Risk-Limiting Audit (RLA),
as described in:

  A Gentle Introduction to Risk-limiting Audits
   http://www.stat.berkeley.edu/~stark/Preprints/gentle12.pdf

  sample-size multiplier rho as described in

  Super-Simple Simultaneous Single-Ballot Risk-Limiting Audits [s4rla]
   https://www.usenix.org/legacy/events/evtwote10/tech/full_papers/Stark.pdf

  BRAVO: Ballot-polling Risk-limiting Audits to Verify Outcomes
   Mark Lindeman, Philip B. Stark, Vincent S. Yates
   https://www.usenix.org/system/files/conference/evtwote12/evtwote12-final27.pdf

  Introduction to Risk-Limiting Election Audits, Statistics 157, Fall 2017, UC Berkeley
   https://github.com/pbstark/S157F17/blob/master/audit.ipynb

%InsertOptionParserUsage%

With the -n option, specify the actual number of discrepancies of various
kinds via the --o1, o2, u1 and u2 options.
Without -n, specify the fractional RATE of discrepancies, via
the --or1, or2, ur1 and ur2 options.

Example: calculate initial sample size for RLA with 2% margin,
default 10% risk limit, and default error rates (0.1% chance of
1-vote under or overstatement, rounded up, and 0.01% chance of
2-vote under or overstatement, not rounded up):

 rlacalc.py -m 2

Calculate sample size needed for RLA with 5% margin, 20% risk limit and one 1-vote overstatement:
 rlacalc.py -n -m 5 -r 20 --o1=1

Deploy as a web API (local testing mode):

 hug -f rlacalc.py

 then visit  http://localhost:8000/  for help
 or to e.g. calculate the sample size for a margin of 5%, for a 10% risk limit, visit
   http://localhost:8000/nmin?alpha=0.1&margin=0.05

Run unit tests:

 rlacalc.py --test

TODO:
 check hug parameters, test more
 check command line calling sequences and printouts
 use different names if I change parameter order
 update rlacalc.html
 make "Note, can be less than nmin" example into test case
 more p-value tests
 test multi-times thru loop

 Model variance for ballot-polling audits, add estimates for quantiles.
 Add calculations for DiffSum, ClipAudit etc.
 Add pretty API documentation via pydoc3 and json2html
   (https://github.com/timothycrosley/hug/issues/448#issuecomment-281878767)
"""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import os
import sys
import logging
from optparse import OptionParser
from math import log, exp, ceil, isnan
# from numpy import log, ceil

try:
    import hug
except:
    import hug_noop as hug

def annotate(annotations):
    """
    Add function annotations (PEP 3107) in a way that parses cleanly for python2.
    cf. https://www.python.org/dev/peps/pep-0484/#suggested-syntax-for-python-2-7-and-straddling-code
    """

    def decorator(f):
        f.__annotations__ = annotations
        return f
    return decorator

__author__ = "Neal McBurnett <http://neal.mcburnett.org/>"
__version__ = "0.2.0"
__date__ = "2017-02-23"
__copyright__ = "Copyright (c) 2017 Neal McBurnett"
__license__ = "MIT"

parser = OptionParser(prog="rlacalc.py",
                      usage=__doc__.replace("%InsertOptionParserUsage%\n", 'Usage: %prog [options]\n'),
                      version=__version__)

parser.add_option("-m", "--margin",
  type="float", default=5.0,
  help="margin of victory, in percent")

parser.add_option("-n", "--nmin",
  action="store_true", default=False,
  help="Calculate nmin from observed discrepancies, not rates")

parser.add_option("--rawrates",
  action="store_true", default=False,
  help="Calculate KM_Expected_sample_size value, with no rounding")

parser.add_option("-o", "--nminFromRates",
  action="store_true", default=False,
  help="Calculate obsolete nminFromRates value")

parser.add_option("-t", "--nminToGo",
  action="store_true", default=False,
  help="Calculate nminToGo value: calculate rates from o1 o2 u1 u2 / samplesize")

parser.add_option("--level",
  action="store_true", default=False,
  help="Calculate risk level, the p-value")

parser.add_option("-p", "--polling",
  action="store_true", default=False,
  help="Ballot polling audit. Add --level for levels")

parser.add_option("-R", "--risk_level",
  type="float", default=100.0,
                  help="risk level based on ballots tallied so far."
                  "Corresponds to one divided by the test statistic, as a fraction."
                  "Default: 1.0 (corresponding to no ballots tallied)")

parser.add_option("-r", "--alpha",
  type="float", default=10.0,
  help="maximum risk level (alpha), in percent")

parser.add_option("-g", "--gamma",
  type="float", default=1.03905,
  help="gamma: error inflation factor, greater than 1.0")

parser.add_option("-s", "--samplesize",
  type="int", default=95,
  help="Sample size, for --level option")

parser.add_option("-W", "--winnervotes",
  type="int", default=0,
  help="Reported votes for the winner -p --level options")

parser.add_option("-L", "--loservotes",
  type="int", default=0,
  help="Reported votes for the loser -p --level options")

parser.add_option("-w", "--winnersamples",
  type="int", default=0,
  help="Sampled votes for the winner -p --level options")

parser.add_option("-l", "--losersamples",
  type="int", default=0,
  help="Sampled votes for the winner -p --level options")

parser.add_option("-b", "--binom",
  action="store_true", default=False,
  help="Calculate binomial confidence interval")

"""
# For when we add an option to calculate rho:
parser.add_option("--lambdatol",
  type="float", default=50.0,
  help="lambda: error tolerance for overstatements in percent, less than 100.0")

and later...

    if lambdatol >= 1.0:
        raise ValueError("lambdatol is %f but must be < 1.0" % lambdatol)

"""

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

parser.add_option("-v", "--verbose",
  action="store_true", default=False,
  help="Verbose doctests")

# incorporate OptionParser usage documentation in our docstring
__doc__ = __doc__.replace("%InsertOptionParserUsage%\n", parser.format_help())


class RLAError(Exception):
    "Basic exception for errors raised by rlacalc"

class RLAValueError(RLAError, ValueError):
    "rlacalc ValueErrors"

def rho(alpha=0.1, gamma=1.03905, lambdatol=0.2):
    """Calculate the sample-size multiplier rho, using the formula from page 4 of s4rla

    >>> rho(alpha=0.1, gamma=1.03905, lambdatol=0.2)
    6.5796033506092035
    >>> rho(alpha=0.1, gamma=1.1, lambdatol=0.5)
    15.200833727738756
    """

    return(-log(alpha) / ((1.0 / (2.0 * gamma)) + (lambdatol * log(1.0 - (1.0 / (2.0 * gamma))))))


def checkArgs(alpha, gamma, margin):
    "Raise an exception if any of the given arguments is invalid"

    if not (0.0 < alpha <= 1.0):
        raise RLAValueError("alpha is %f but must be 0.0 < alpha <= 1.0" % alpha)

    if gamma <= 1.0:
        raise RLAValueError("gamma is %f but must be > 1.0" % gamma)

    if not (0.0 < margin <= 1.0):
        raise RLAValueError("margin is %f but must be 0.0 < margin <= 1.0" % margin)


@hug.get(examples='alpha=0.1&gamma=1.03905&margin=0.05&o1=0&o2=0&u1=0&u2=0')
@hug.local()
@annotate(dict(alpha=hug.types.float_number, gamma=hug.types.float_number, margin=hug.types.float_number,
               o1=hug.types.number, o2=hug.types.number, u1=hug.types.number, u2=hug.types.number))
def nmin(alpha=0.1, gamma=1.03905, margin=0.05, o1=0, o2=0, u1=0, u2=0):
    """Return needed sample size during a ballot-level comparison Risk-Limiting Audit.
    Raises RLAValueError if any arguments are obviously invalid.

    alpha: maximum risk level (alpha), as a fraction
    gamma: error inflation factor, greater than 1.0
    margin: margin of victory, as a fraction
    o1: 1-vote overstatements
    u1: 1-vote understatements
    o2: 2-vote overstatements
    u2: 2-vote understatements

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

    FIXME: confirm those and this
    >>> nmin(margin=0.05, alpha=0.2)
    67.0
    """

    logging.debug("%s, %s, %s, %f, %f, %f, %f" % (alpha, gamma, margin, o1, o2, u1, u2))

    checkArgs(alpha, gamma, margin)

    if o1 < 0  or  o2 < 0  or u1 < 0  or u2 < 0:
        raise RLAValueError("nmin: Discrepancy counts %d %d %d %d must all be >= 0" % (o1, o2, u1, u2))

    return max(
        o1 + o2 + u1 + u1,
        ceil(-2.0 * gamma * ( log(alpha) +
                                 o1 * log(1.0 - 1.0 / (2.0 * gamma)) +
                                 o2 * log(1.0 - 1.0 / gamma) +
                                 u1 * log(1.0 + 1.0 / (2.0 * gamma)) +
                                 u2 * log(1.0 + 1.0 / gamma)) / margin ))


@hug.get(examples='alpha=0.1&gamma=1.03905&margin=0.05&or1=0.001&or2=0.0001&ur1=0.001&ur2=0.0001&roundUp1=1&rountUp2=')
@hug.local()
@annotate(dict(alpha=hug.types.float_number, gamma=hug.types.float_number, margin=hug.types.float_number,
               or1=hug.types.float_number, or2=hug.types.float_number,
               ur1=hug.types.float_number, ur2=hug.types.float_number,
               roundUp1=hug.types.boolean, roundUp2=hug.types.boolean))
def KM_Expected_sample_size(alpha=0.1, gamma=1.03905, margin=0.05, or1=0.001, or2=0.0001, ur1=0.001, ur2=0.0001):
    """
    Note this is an estimate, not an exact calculation. In an audit, the final determination of whether
    the risk limit has been reached should be checked via nmin().

    Raises RLAValueError if any arguments are obviously invalid.
    Returns nan if the sample size 

    Without error checking, note invalid result with invalid input (negative rates)
    rlacalc -m 5 -r 5 --roundUp1 0  --or2 -2 --ur2 -3
    KM_exp_smps = 1 for margin 5%, risk 5%, gamma 1.03905, or1 0.001, or2 -2, ur1 0.001, ur2 -3

    From https://github.com/pbstark/S157F17/blob/master/audit.ipynb

    Note, can be less than nmin, e.g.:
    rlacalc -m 5 -r 5 --roundUp1 0 --ur1 0 --or1 0  --or2 0 --ur2 0 -R
    KM_exp_smps = 124 for margin 5%, risk 5%, gamma 1.03905, or1 0, or2 0, ur1 0, ur2 0
    rlacalc -m 5 -r 5 --roundUp1 0 --u1 0 --o1 0  --o2 0 --u2 0 -n
    Sample size = 125 for margin 5%, risk 5%, gamma 1.03905, o1 0, o2 0, u1 0, u2 0

    >>> alpha = 0.05
    >>> gamma = 1.03905
    >>> margin = (354040 - 337589)/(354040+337589+33234) # New Hampshire 2016
    >>> KM_Expected_sample_size(alpha, gamma, 0.05, 0.001, 0, 0.001, 0)
    125.0
    >>> KM_Expected_sample_size(alpha, gamma, margin, .001, 0., 0., 0.)
    291.0
    >>> KM_Expected_sample_size(alpha, gamma, 0.05, 0., 0., 0., 0.05)
    52.0
    >>> KM_Expected_sample_size(alpha, gamma, 0.05, .05, 0., 0., 0.)
    nan
    """

    checkArgs(alpha, gamma, margin)

    if or1 < 0.0  or  or2 < 0.0  or ur1 < 0.0  or ur2 < 0.0:
        raise RLAValueError("Discrepancy rates %f %f %f %f must all be >= 0.0" % (or1, or2, ur1, ur2))

    n = float('nan')
    denom = log( 1 - margin / (2 * gamma) ) -\
            or1 * log(1 - 1 /(2 * gamma)) -\
            or2 * log(1 - 1 / gamma) -\
            ur1 * log(1 + 1 /(2 * gamma)) -\
            ur2 * log(1 + 1 / gamma)
    if (denom < 0):
        n = ceil(log(alpha)/denom)

    return(n)


@hug.get(examples='alpha=0.1&gamma=1.03905&margin=0.05&or1=0.001&or2=0.0001&ur1=0.001&ur2=0.0001&roundUp1=1&rountUp2=')
@hug.local()
@annotate(dict(alpha=hug.types.float_number, gamma=hug.types.float_number, margin=hug.types.float_number,
               or1=hug.types.float_number, or2=hug.types.float_number,
               ur1=hug.types.float_number, ur2=hug.types.float_number,
               roundUp1=hug.types.boolean, roundUp2=hug.types.boolean))
def KM_Expected_sample_size_rounded(alpha=0.1, gamma=1.03905, margin=0.05, or1=0.001, or2=0.0001, ur1=0.001, ur2=0.0001, roundUp1=True, roundUp2=False):
    """Return expected sample size for a ballot-level comparison Risk-Limiting Audit
    Raises RLAValueError if any arguments are obviously invalid.
    Returns nan if it seems the sample size is unbounded.

    alpha: maximum risk level (alpha), as a fraction
    gamma: error inflation factor, greater than 1.0
    margin: margin of victory, as a fraction
    or1: 1-vote overstatement rate
    ur1: 1-vote understatement rate
    or2: 2-vote overstatement rate
    ur2: 2-vote understatement rate
    roundUp1: whether to round up 1-vote differences
    roundUp2: whether to round up 2-vote differences

    Combines KM_Expected_sample_size from https://github.com/pbstark/S157F17/blob/master/audit.ipynb
    with nminFromRates based on https://www.stat.berkeley.edu/~stark/Java/Html/auditTools.htm

    >>> alpha = 0.05
    >>> gamma = 1.03905
    >>> margin = (354040 - 337589)/(354040+337589+33234) # New Hampshire 2016

    >>> KM_Expected_sample_size_rounded(alpha, gamma, 0.05, 0.001, 0, 0.001, 0, roundUp1=False)
    125.0
    >>> KM_Expected_sample_size_rounded(alpha, gamma, 0.05, 0.001, 0, 0.001, 0)
    136.0
    >>> KM_Expected_sample_size_rounded(alpha, gamma, margin, .001, 0., 0., 0.)
    335.0
    >>> KM_Expected_sample_size(alpha, gamma, 0.05, 0., 0., 0., 0.05)
    52.0
    >>> KM_Expected_sample_size_rounded(alpha, gamma, 0.05, .05, 0., 0., 0.)
    nan
    >>> KM_Expected_sample_size_rounded(alpha, gamma, 0.05, 0., 0., 0., 0.05)
    nan
    >>> KM_Expected_sample_size_rounded(alpha, gamma, 0.05, 1., 1., 1., 1)
    nan
    """

    n0 = KM_Expected_sample_size(alpha, gamma, margin, or1, or2, ur1, ur2)
    lastn0 = n0

    logging.info("n0 = %f" % n0)

    # Run a few times thru a loop to quickly try to converge on a stable estimated
    # sample size, and corresponding discrepancy counts based on the rounding rules.
    # I.e. generate the number of discrepencies of each type based on the rate, the
    # candidate sample size n0, and the relevant roundUp setting.
    # Recompute nmin each time.
    rounds = 10
    for i in range(rounds):
        if (roundUp1):
             o1 = ceil(or1 * n0)
             u1 = ceil(ur1 * n0)
        else:
             o1 = round(or1 * n0)
             u1 = round(ur1 * n0)

        if (roundUp2):
             o2 = ceil(or2 * n0)
             u2 = ceil(ur2 * n0)
        else:
             o2 = round(or2 * n0)
             u2 = round(ur2 * n0)

        n0 = nmin(alpha, gamma, margin, o1, o2, u1, u2)
        logging.info("n0 = %f in round %d" % (n0, i))

        if n0 == lastn0  or  isnan(n0):
            logging.info("Break at round %d" % (i))
            break
        else:
            lastn0 = n0

    if i == rounds - 1:
        logging.info("Went to round %d: %s" % (i, (alpha, gamma, margin, or1, or2, ur1, ur2, roundUp1, roundUp2)))
        n0 = float('nan')

    return(n0)


@hug.get(examples='audited=95&alpha=0.1&gamma=1.03905&margin=0.05&o1=0&o2=0&u1=0&u2=0')
@hug.local()
@annotate(dict(alpha=hug.types.float_number, gamma=hug.types.float_number, margin=hug.types.float_number,
               o1=hug.types.number, o2=hug.types.number, u1=hug.types.number, u2=hug.types.number))
def nminToGo(audited=95, alpha=0.1, gamma=1.03905, margin=0.05, o1=0, o2=0, u1=0, u2=0):
    """Return expected sample size during a ballot-level comparison Risk-Limiting Audit,
    based on observed discrepancy rates.

    Raises RLAValueError if any arguments are obviously invalid.

    audited: number of samples audited so far
    alpha: maximum risk level (alpha), as a fraction
    gamma: error inflation factor, greater than 1.0
    margin: margin of victory, as a fraction
    o1: 1-vote overstatements
    u1: 1-vote understatements
    o2: 2-vote overstatements
    u2: 2-vote understatements
    """

    logging.debug("%s, %s, %s, %f, %f, %f, %f" % (alpha, gamma, margin, o1, o2, u1, u2))

    checkArgs(alpha, gamma, margin)

    if o1 < 0  or  o2 < 0  or u1 < 0  or u2 < 0:
        raise RLAValueError("nmin: Discrepancy counts %d %d %d %d must all be >= 0" % (o1, o2, u1, u2))

    return KM_Expected_sample_size_rounded(alpha, gamma, margin, o1/audited, o2/audited, u1/audited, u2/audited, roundUp1=False)

@hug.get(examples='alpha=0.1&gamma=1.03905&margin=0.05&or1=0.001&or2=0.0001&ur1=0.001&ur2=0.0001&roundUp1=1&rountUp2=')
@hug.local()
@annotate(dict(alpha=hug.types.float_number, gamma=hug.types.float_number, margin=hug.types.float_number,
               or1=hug.types.float_number, or2=hug.types.float_number,
               ur1=hug.types.float_number, ur2=hug.types.float_number,
               roundUp1=hug.types.boolean, roundUp2=hug.types.boolean))
def nminEst(alpha=0.1, gamma=1.03905, margin=0.05, or1=0.001, or2=0.0001, ur1=0.001, ur2=0.0001, roundUp1=True, roundUp2=False):
    """Return expected sample size for a ballot-level comparison Risk-Limiting Audit
    alpha: maximum risk level (alpha), as a fraction
    gamma: error inflation factor, greater than 1.0
    margin: margin of victory, as a fraction
    or1: 1-vote overstatement rate
    ur1: 1-vote understatement rate
    or2: 2-vote overstatement rate
    ur2: 2-vote understatement rate
    roundUp1: whether to round up 1-vote differences
    roundUp2: whether to round up 2-vote differences

    Incomplete, based on Stephanie Singer's proposal at https://github.com/FreeAndFair/ColoradoRLA/issues/695
    """

    A = -2 * gamma * log(alpha) / margin
    B = (-2 * gamma / margin ) * ( log(1 - 1 / (2 * gamma )) )
    C = (-2 * gamma / margin ) * ( log(1 - 1 / gamma) )
    D = (-2 * gamma / margin ) * ( log(1 + 1 / (2 * gamma )) )
    E = (-2 * gamma / margin ) * ( log(1 + 1 / gamma) )


@hug.get(examples='alpha=0.1&gamma=1.03905&margin=0.05&or1=0.001&or2=0.0001&ur1=0.001&ur2=0.0001&roundUp1=1&rountUp2=')
@hug.local()
@annotate(dict(alpha=hug.types.float_number, gamma=hug.types.float_number, margin=hug.types.float_number,
               or1=hug.types.float_number, or2=hug.types.float_number,
               ur1=hug.types.float_number, ur2=hug.types.float_number,
               roundUp1=hug.types.boolean, roundUp2=hug.types.boolean))
def nminFromRates(alpha=0.1, gamma=1.03905, margin=0.05, or1=0.001, or2=0.0001, ur1=0.001, ur2=0.0001, roundUp1=True, roundUp2=False):
    """Return expected sample size for a ballot-level comparison Risk-Limiting Audit
    alpha: maximum risk level (alpha), as a fraction
    gamma: error inflation factor, greater than 1.0
    margin: margin of victory, as a fraction
    or1: 1-vote overstatement rate
    ur1: 1-vote understatement rate
    or2: 2-vote overstatement rate
    ur2: 2-vote understatement rate
    roundUp1: whether to round up 1-vote differences
    roundUp2: whether to round up 2-vote differences

    Based on Javascript code in https://www.stat.berkeley.edu/~stark/Java/Html/auditTools.htm

    >>> alpha = 0.05
    >>> gamma = 1.03905
    >>> margin = (354040 - 337589)/(354040+337589+33234) # New Hampshire 2016
    >>> nminFromRates(alpha, gamma, margin, .001, 0, 0, 0, 0.05)
    335.0
    >>> nminFromRates(alpha, gamma, 0.05, 0.001, 0, 0.001, 0)
    136.0
    >>> nminFromRates(alpha, gamma, margin, .05, 0, 0, 0, 0.05)
    Traceback (most recent call last):
    RLAValueError: nmin: Discrepancy counts -6 0 0 0 must all be >= 0

    Without nmin error checking, the last one returns
    2781959.0 after calculating n0 = -136.8445412898146
    """

    checkArgs(alpha, gamma, margin)

    n0 = (-2 * gamma * log(alpha) /
          (margin + 2 * gamma * (or1 * log(1-1/(2 * gamma)) +
                                 or2 * log(1 - 1/gamma) +
                                 ur1 * log(1 + 1/(2 * gamma)) +
                                 ur2 * log(1 + 1/gamma)) ))

    logging.info("n0 = %f" % n0)

    # Run a few times thru a loop to quickly try to converge on a stable estimated
    # sample size, and corresponding discrepancy counts based on the rounding rules.
    # I.e. generate the number of discrepencies of each type based on the rate, the
    # candidate sample size n0, and the relevant roundUp setting.
    # Recompute nmin each time.
    rounds = 10
    for i in range(rounds):
        if (roundUp1):
             o1 = ceil(or1 * n0)
             u1 = ceil(ur1 * n0)
        else:
             o1 = round(or1 * n0)
             u1 = round(ur1 * n0)

        if (roundUp2):
             o2 = ceil(or2 * n0)
             u2 = ceil(ur2 * n0)
        else:
             o2 = round(or2 * n0)
             u2 = round(ur2 * n0)

        n0 = nmin(alpha, gamma, margin, o1, o2, u1, u2)

        logging.info("n0 = %f in round %d" % (n0, i))

    return(n0)


def KM_P_value(n=95, gamma=1.03905, margin=0.05, o1=0, o2=0, u1=0, u2=0):
    """Return P-values (risk level achieved) for a comparison audit with the
    given sample size n and discrepancy counts.

    n: sample size
    margin: diluted margin; 
    From https://github.com/pbstark/S157F17/blob/master/audit.ipynb

    >>> margin = (354040 - 337589)/(354040+337589+33234) # New Hampshire 2016
    >>> KM_P_value(200, 1.03905, margin, 1, 0, 0, 0)
    0.21438135077031842
    """

    return((1 - margin/(2*gamma))**n *\
           (1 - 1/(2*gamma))**(-o1) *\
           (1 - 1/gamma)**(-o2) *\
           (1 + 1/(2*gamma))**(-u1) *\
           (1 + 1/gamma)**(-u2))


def ballot_polling_risk_level(winner_votes, loser_votes, winner_obs, loser_obs):
    """
    Return the ballot polling risk level for a contest with the given overall
    vote totals and observed votes on selected ballots during a ballot polling
    risk-limiting audit.

    This method should be called for each winner-loser pair (w,l).
    calculate s_wl = (number of votes for w)/(number of votes for w + number of votes for l)
    For each contest, for each winner-loser pair (w,l), set T_wl =1.
    For each line in `all_contest_audit_details_by_cvr` with consensus = "YES",
     change any T_wl values as indicated by the BRAVO algorithm.
    The risk level achieved so far is the inverse of the resulting T_wl value.

    >>> ballot_polling_risk_level(1410, 1132, 170, 135) # Custer County 2018
    0.1342382069344729
    >>> ballot_polling_risk_level(2894, 1695, 45, 32)   # Las Animas County 2018
    0.47002027242290234
    >>> ballot_polling_risk_level(0, 0, 2000, 0)
    1.0
    >>> ballot_polling_risk_level(2894, 0, 1130, 0)   # Test overflow
    nan
    >>> ballot_polling_risk_level(100000, 0, 50000, 0)   # Test overflow
    nan

    The code is equivalent to this, but uses logs to prevent overflow
    T_wl = 1.0
    T_wl = T_wl * ((s_wl)/0.5) ** winner_obs
    T_wl = T_wl * ((1.0 - s_wl)/0.5) ** loser_obs
    """

    try:
        s_wl = winner_votes / (winner_votes + loser_votes)
    except ZeroDivisionError:
        return 1.0

    log_T_wl = log(1.0)
    try:
        log_T_wl = log_T_wl + ((log(s_wl) - log(0.5)) * winner_obs)
        log_T_wl = log_T_wl + ((log(1.0 - s_wl) - log(0.5)) * loser_obs)
        risk_level = log(1.0) - log_T_wl
    except ValueError:
        risk_level = float('NaN')

    return exp(risk_level)


@hug.get(examples='alpha=0.1&margin=0.05&risk_level=1.0')
@hug.local()
@annotate(dict(alpha=hug.types.float_number, margin=hug.types.float_number, risk_level=hug.types.float_number))
def findAsn(alpha=0.1, margin=0.05, risk_level=1.0):
    """Return expected sample size for a ballot-polling Risk-Limiting Audit
    alpha: maximum risk level (alpha), as a fraction
    margin: margin of victory, as a fraction
    risk_level: risk level for ballots tallied so far.

    Model variance for ballot-polling audits, add estimates for quantiles.
     Quantile           25th        50th    75th    90th    99th
     fraction of mean   0.41        0.71    1.25    2.09    4.64

    Based on Javascript code in https://www.stat.berkeley.edu/~stark/Java/Html/ballotPollTools.htm
    and BRAVO paper

    Tests, based on table 1 in BRAVO: Ballot-polling Risk-limiting Audits to Verify Outcomes
      Mark Lindeman, Philip B. Stark, Vincent S. Yates
      https://www.usenix.org/system/files/conference/evtwote12/evtwote12-final27.pdf

    >>> findAsn(margin=0.01)
    46151.0
    >>> findAsn(margin=0.04)
    2902.0
    >>> findAsn(margin=0.2)
    119.0
    >>> findAsn(margin=0.2,)
    119.0

    TODO: add tests that use risk_level

    v_c: reported votes for the candidate
    p_c: reported proportion of ballots with votes for candidate
    s_c: the fraction of valid votes cast for candidate  (ignoring undervotes etc)
    """

    ballots = 100000
    vw = ballots * (0.5 + margin / 2.)
    vl = ballots * (0.5 - margin / 2.)

    if vl <= 0:
        return 4  # FIXME: for 100% margin, use same value as 99% margin

    if (vw > vl):
        sw = vw / (vw + vl)
        zw = log(2.0 * sw)
        zl = log(2.0 * (1 - sw))
        pw = vw / ballots
        pl = vl / ballots

        logging.debug("%s, %s, %s, %s, %s, %s, %s, %s, %s, %s" % (alpha, margin, ballots, vw, vl, sw, zw, zl, pw, pl))

        asn = ceil((log(1.0 / alpha * risk_level) + zw / 2.0) / (((vw + vl) / ballots) * (pw * zw + pl * zl)))

    else:
        asn = float('nan')

    return asn


'''
FIXME - replace the hard-coded call with a command-line option, and integrate into KM_Expected_sample_size

Situation:

 Observe 50 county audits.
 For EACH of 4 kinds of errors, observe occurrence rate:

 0 in 30
 1 in 75
 0 in 40
 1 in 100
 0 in 150
 2 in 24

=> 4 in sum(...) "successes"

Wanted: 90th confidence interval on each of the 4 error rates
Implemented in Java

Then plug that rate in to KM_Expected_sample_size
 allow both nmin opts (for observed discrepancies) and future rate opts or calculations?
 how to decide when to use default rate and when to calculate one?

binomial distribution with parameters n and p is the discrete probability distribution of the number of successes in a sequence of n independent experiments, each asking a yes-no question, and each with its own boolean-valued outcome

For sampling without replacement, the appropriate confidence interval is hypergeometric.
'''

def binom_conf_interval(n, x, cl=0.975, alternative="two-sided", p=None, **kwargs):
    """
    Compute a confidence interval for a binomial p, the probability of success in each trial.

    Parameters
    ----------
    n : int
        The number of Bernoulli trials.
    x : int
        The number of successes.
    cl : float in (0, 1)
        The desired confidence level.
    alternative : {"two-sided", "lower", "upper"}
        Indicates the alternative hypothesis.
    p : float in (0, 1)
        Starting point in search for confidence bounds for probability of success in each trial.
    kwargs : dict
        Key word arguments

    Returns
    -------
    tuple
        lower and upper confidence level with coverage (approximately)
        1-alpha.

    Notes
    -----
    xtol : float
        Tolerance
    rtol : float
        Tolerance
    maxiter : int
        Maximum number of iterations.
    """
    from scipy.optimize import brentq
    from scipy.stats import binom, hypergeom

    assert alternative in ("two-sided", "lower", "upper")

    if p is None:
        p = x / n
    ci_low = 0.0
    ci_upp = 1.0

    if alternative == 'two-sided':
        cl = 1 - (1 - cl) / 2

    if alternative != "upper" and x > 0:
        f = lambda q: cl - binom.cdf(x - 1, n, q)
        ci_low = brentq(f, 0.0, p, *kwargs)
    if alternative != "lower" and x < n:
        f = lambda q: binom.cdf(x, n, q) - (1 - cl)
        ci_upp = brentq(f, 1.0, p, *kwargs)

    return ci_low, ci_upp


def _test(opts):
    import doctest
    return doctest.testmod(verbose=opts.verbose)


def main(parser):
    "Run rlacalc with given OptionParser arguments"

    (opts, args) = parser.parse_args()

    #configure the root logger.  Without filename, default is StreamHandler with output to stderr. Default level is WARNING
    logging.basicConfig(level=opts.debuglevel)   # ..., format='%(message)s', filename= "/file/to/log/to", filemode='w' )

    if opts.test:
        _test(opts)
        sys.exit(0)

    if opts.polling:
        if opts.level:
            risk_level = ballot_polling_risk_level(opts.winnervotes, opts.loservotes, opts.winnersamples, opts.losersamples)
            print("%.4f" % risk_level)
        else:
            samplesize = findAsn(opts.alpha / 100.0, opts.margin / 100.0, opts.risk_level / 100.0)
            print("Sample size = %d for ballot polling, margin %g%%, risk %g%%" % (samplesize, opts.margin, opts.alpha))

    elif opts.nmin:
        samplesize = nmin(opts.alpha / 100.0, opts.gamma, opts.margin / 100.0, opts.o1, opts.o2, opts.u1, opts.u2)
        print("Sample size = %d for margin %g%%, risk %g%%, gamma %g, o1 %g, o2 %g, u1 %g, u2 %g" %
              (samplesize, opts.margin, opts.alpha, opts.gamma, opts.o1, opts.o2, opts.u1, opts.u2))

    elif opts.nminToGo:
        samplesize = nminToGo(opts.samplesize, opts.alpha / 100.0, opts.gamma, opts.margin / 100.0, opts.o1, opts.o2, opts.u1, opts.u2)
        print("Expanded sample size = %g for samplesize %d, margin %g%%, risk %g%%, gamma %g, o1 %g, o2 %g, u1 %g, u2 %g" %
              (samplesize, opts.samplesize, opts.margin, opts.alpha, opts.gamma, opts.o1, opts.o2, opts.u1, opts.u2))

    elif opts.level:
        samplesize = opts.samplesize
        risk_level = KM_P_value(samplesize, opts.gamma, opts.margin / 100.0, opts.o1, opts.o2, opts.u1, opts.u2)

        print("KM_P_value  = %.4f for margin %g%%, samplesize %.0f, gamma %g, o1 %g, o2 %g, u1 %g, ur %g" %
              (risk_level, opts.margin, samplesize, opts.gamma, opts.o1, opts.o2, opts.u1, opts.u2))

    elif opts.nminFromRates:
        samplesize = nminFromRates(opts.alpha / 100.0, opts.gamma, opts.margin / 100.0, opts.or1, opts.or2, opts.ur1, opts.ur2, opts.roundUp1, opts.roundUp2)

        print("Old sample size = %d for margin %g%%, risk %g%%, gamma %g, or1 %g, or2 %g, ur1 %g, ur2 %g, roundUp1 %g, roundUp2 %g" %
              (samplesize, opts.margin, opts.alpha, opts.gamma, opts.or1, opts.or2, opts.ur1, opts.ur2, opts.roundUp1, opts.roundUp2))

    elif opts.binom:
        n=5000
        x=20
        ci=.90
        sides="upper"
        print("binom_conf_interval(%d, %d, %.3f, %s): %s" % (n, x, ci, sides, binom_conf_interval(n, x, ci, sides),))

    elif opts.rawrates:
        samplesize = KM_Expected_sample_size(opts.alpha / 100.0, opts.gamma, opts.margin / 100.0, opts.or1, opts.or2, opts.ur1, opts.ur2)

        print("KM_exp_smps = %.0f for margin %g%%, risk %g%%, gamma %g, or1 %g, or2 %g, ur1 %g, ur2 %g" % (samplesize, opts.margin, opts.alpha, opts.gamma, opts.or1, opts.or2, opts.ur1, opts.ur2))

    else:
        samplesize = KM_Expected_sample_size_rounded(opts.alpha / 100.0, opts.gamma, opts.margin / 100.0, opts.or1, opts.or2, opts.ur1, opts.ur2, opts.roundUp1, opts.roundUp2)

        print("KM_exp_rnd  = %.0f for margin %g%%, risk %g%%, gamma %g, or1 %g, or2 %g, ur1 %g, ur2 %g, roundUp1 %g, roundUp2 %g" %
              (samplesize, opts.margin, opts.alpha, opts.gamma, opts.or1, opts.or2, opts.ur1, opts.ur2, opts.roundUp1, opts.roundUp2))


if __name__ == "__main__":
    main(parser)
