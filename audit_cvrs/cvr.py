#!/usr/bin/env python
"read in and cache csv file of Cast Vote Records, looking up sequential ids in 'seqno' column"

import csv
import logging
from collections import OrderedDict

#ESS_CVR_FILE = "/srv/voting/audit/corla/pilot-cvr-lat/ES&S/Jefferson/2nd Submission/IncompleteJeffcoCastVoteRecord.csv"
#CVR_FILE = "/srv/voting/audit/corla/jeffco-2015/box-list-final.csv"
CVR_FILE = "/srv/voting/audit/corla/dominion/cvr-export-recommendation/cvr.csv"

CVRS = {}

def read_ess_cvr(path):
    with open(path, 'rU') as data:
        reader = csv.DictReader(data)

        for seqno, row in enumerate(reader):
            yield (str(seqno), OrderedDict( (f, row[f]) for f in reader.fieldnames))

def init(cvrfilename = CVR_FILE):

    # print read_ess_cvr(cvrfilename).next()
    global CVRS

    CVRS = dict(list(read_ess_cvr(cvrfilename)))

    print("Read in %d CVRs" % len(CVRS))
    logging.debug("Read in %d CVRs" % len(CVRS))

def lookup_cvr(id):

    global CVRS

    return '\n'.join(("%s: %s" % (key, value) for key, value in CVRS[id].iteritems() if value))


if __name__ == "__main__":
    "Run a simple test to read in a test file and print the 2nd record"

    print("Testing\n")
    #init("/home/neal/py/projects/audit_cvrs/test/ess-test.cvr")
    init("/srv/voting/audit/corla/dominion/cvr-export-recommendation/cvr.csv")
    print("\nSecond record:\n%s" % lookup_cvr("2"))
