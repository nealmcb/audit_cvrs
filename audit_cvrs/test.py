"""Test rlacalc
Use hypothesis testing framework:
 https://hypothesis.readthedocs.io/en/latest/quickstart.html

TODO:
 see what's up with really small margins, e.g.
 falsified: test_nmin(alpha=1e-06, gamma=1.001, margin=1e-10, o1=0, o2=0, u1=0, u2=0)

"""

import sys
# TODO: get pytest working without this and without python3 -m pytest
#sys.path.insert(0, '/home/neal/py/projects/audit_cvrs/audit_cvrs')

import logging
logging.basicConfig(filename='hypothesis-test.log', level=logging.DEBUG)
logging.debug("pytest path: %s" % sys.path)

import rlacalc

# print("raw nmin test: %s" % rlacalc.nmin(0.05, 1.03905, 0.02, 0, 0, 0, 0))

from hypothesis import given, settings, Verbosity, example, assume

import hypothesis.strategies as st

@given(st.floats(10**-6, 1.01),
       st.floats(1.01, 10.0),
       st.floats(10**-6, 1.01),
       st.integers(0, 100), st.integers(0, 100), st.integers(0, 100), st.integers(0, 100))
@settings(max_examples=1000)
@example(0.05, 1.03905, 0.02, 1, 1, 1, 1)
def test_nmin(alpha, gamma, margin, o1, o2, u1, u2):

    assume(0.0 < alpha <= 1.0)
    assume(0.0 < margin <= 1.0)
    assume(gamma > 1.0)
    assume(not (o1 < 0  or  o2 < 0  or u1 < 0  or u2 < 0))

    samples = rlacalc.nmin(alpha, gamma, margin, o1, o2, u1, u2)
    assert samples >= 0
    assert rlacalc.KM_P_value(samples, gamma, margin, o1, o2, u1, u2) <= alpha, "Didn't meet alpha; samples = %d" % samples

"""
    perhaps useful?
    try: ...nmin...
    except OverflowError:
        assume(False)
"""
