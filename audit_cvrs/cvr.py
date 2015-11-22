# read in and cache csv file of Cast Vote Records

import csv

#ESS_CVR_FILE = "/srv/voting/audit/corla/pilot-cvr-lat/ES&S/Jefferson/2nd Submission/IncompleteJeffcoCastVoteRecord.csv"
ESS_CVR_FILE = "/srv/voting/audit/corla/jeffco-2015/box-list-final.csv"

def read_ess_cvr(path):
    with open(path, 'rU') as data:
        reader = csv.DictReader(data)

        for row in reader:
            yield (row["seqno"], row)

def init():

    # print read_ess_cvr(ESS_CVR_FILE).next()
    global CVRS

    CVRS = dict(list(read_ess_cvr(ESS_CVR_FILE)))

    print("Read in %d CVRs" % len(CVRS))

def lookup_cvr(id):

    global CVRS

    return '\n'.join(("%s: %s" % (key, row) for key, value in CVRS[id].iteritems() if value))
