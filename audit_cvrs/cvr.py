# read in and cache csv file of Cast Vote Records

import csv
from collections import OrderedDict

#ESS_CVR_FILE = "/srv/voting/audit/corla/pilot-cvr-lat/ES&S/Jefferson/2nd Submission/IncompleteJeffcoCastVoteRecord.csv"
ESS_CVR_FILE = "/srv/voting/audit/corla/jeffco-2015/box-list-final.csv"

def read_ess_cvr(path):
    with open(path, 'rU') as data:
        reader = csv.DictReader(data)

        for row in reader:
            yield (row["seqno"], OrderedDict( (f, row[f]) for f in reader.fieldnames))

def init(cvrfilename = ESS_CVR_FILE):

    # print read_ess_cvr(cvrfilename).next()
    global CVRS

    CVRS = dict(list(read_ess_cvr(cvrfilename)))

    print("Read in %d CVRs" % len(CVRS))

def lookup_cvr(id):

    global CVRS

    return '\n'.join(("%s: %s" % (key, value) for key, value in CVRS[id].iteritems() if value))


if __name__ == "__main__":
    init("/home/neal/py/projects/audit_cvrs/test/ess-test.cvr")
