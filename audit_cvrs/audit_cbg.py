#!/usr/bin/python
"""audit_cbg: assist in auditing cast vote records of ballots from Clear Ballot Group scans.

%InsertOptionParserUsage%

Used for now from /srv/voting/audit/corla/cbg/arapahoe/1113cvr/corla_anal.ipynb

Example:
    audit_cbg.py -p co_arapahoe_2013g -m ../ballotManifest.csv -s 27405096441431501170

ToDo:
    Report sorted vote totals for each contest
    Given info on number of winners per contest, list winners and margins
    Calculate number of ballots to select, given selected contests
    Read manifest and generate selections based on that and seed

    Perhaps switch away from requirement for Pandas, which adds complexity
     But helps allow analysis in notebook, adds some convenience.
"""

import os
import sys
import logging
from optparse import OptionParser
from datetime import datetime
import re
import sampler
import math
import pandas as pd

__author__ = "Neal McBurnett <http://neal.mcburnett.org/>"
__version__ = "0.1.0"
__date__ = "2013-11-26"
__copyright__ = "Copyright (c) 2013 Neal McBurnett"
__license__ = "GPL v3"

parser = OptionParser(prog="audit_cbg.py", version=__version__)

parser.add_option("-p", "--prefix",
  help="prefix for CBG files, e.g. co_arapahoe_2013g" )

parser.add_option("-m", "--manifest",
  help="manifest file name" )

parser.add_option("-s", "--seed",
  help="seed for random selection" )

# FIXME: should be able to automatically calculate better default for number to select
parser.add_option("-n", "--N",
  default = 10,
  help="number of ballots to select" )

parser.add_option("-d", "--debuglevel",
  type="int", default=logging.WARNING,
  help="Set logging level to debuglevel: DEBUG=10, INFO=20,\n WARNING=30 (the default), ERROR=40, CRITICAL=50")

# incorporate OptionParser usage documentation in our docstring
__doc__ = __doc__.replace("%InsertOptionParserUsage%\n", parser.format_help())

choiceIDre = re.compile(r'Choice_(?P<id>[0-9]*)_')
ballotIDre = re.compile(r'(?P<type>..)-(?P<batch>[0-9]*)\+(?P<image>[0-9]*)')

class Audit(object):
    def __init__(self, prefix, manifest):
        "Create an audit object based on the CBG files starting with given filename prefix"

        self.choices = pd.read_csv(prefix + '.choices.csv')
        self.contests = pd.read_csv(prefix + '.contests.csv')

        # Make a mapping from contest numbers to contest names
        self.contestid_name = {}
        for id, contest_row in self.contests.iterrows():
            self.contestid_name[contest_row[0]] = contest_row[1]

        # Make a mapping from choice numbers to contests, and to choice names
        self.choiceid_contest = {}
        self.choiceid_name = {}

        for id, choice_row in self.choices.iterrows():
            contest = choice_row[1]
            self.choiceid_contest[choice_row[0]] = contest

            name = choice_row[2]
            if name in ["NO / AGAINST", "YES / FOR", "YES", "NO"]:
                name += " on " + self.contestid_name[contest]
            self.choiceid_name[choice_row[0]] = name

        self.cvr = pd.read_csv(prefix + '.cvr.csv')

        self.manifest = pd.read_csv(manifest)

    def select_ballots(self, seed, n):
        "Randomly select n ballots using Rivest's sampler library"

        old_output_list, new_output_list = sampler.generate_outputs(16, True, 0, len(self.cvr) - 1, seed, False)

        # print new_output_list
        new_output_list = sorted(new_output_list)

        self.selected = self.cvr.iloc[new_output_list]

        # print header row
        print('sorted_number,ballot, batch_label, which_ballot_in_batch')

        for i, (seqid, ballot) in enumerate(self.selected.iterrows()):
            # print i, ballot

            m = ballotIDre.match(ballot['BallotID'])

            batch = "%s-%s" % (m.groups()[:2])
            image = int(m.group('image'))

            print "%d,%d,%s,%d" % (i + 1, seqid, batch, (image - 10000) / 2)

        # Old manual kludge...
        # selected_names = [ 'AB-002+10003' ]
        # selected_names = [ 'AB-001+11353', 'AB-005+10247', 'AB-008+11181', 'AB-009+11115', 'AB-009+11361', 'AB-010+10711', 'AB-011+10963', 'AB-013+11755', 'AB-021+10885', 'AB-022+10423', 'AB-026+10847', 'AB-027+10755', 'AB-027+10965', 'AB-027+11667', 'AB-028+10403', 'AB-028+11471', 'AB-030+11545', 'AB-035+10053', 'AB-037+10563', 'AB-039+10251', 'AB-041+10881', 'AB-048+10329', 'AB-058+10131', 'AB-061+11227', 'AB-062+11023', 'AB-064+10093', 'AB-068+10171', 'AB-069+11295', 'AB-070+10651', 'AB-073+10231', 'AB-073+11043', 'AB-073+11681', 'AB-089+10559', 'AB-089+11153', 'AB-091+11519', 'AB-095+11555', 'AB-096+10989', 'AB-101+11667', 'AB-113+11749', 'AB-115+10829', 'AB-128+10729', 'AB-132+11463', 'AB-132+11899', 'AB-141+11433' ]

        #self.selected = self.cvr[self.cvr.id.isin(selected_names)]

def choice_num(choiceid):
    m = choiceIDre.match(choiceid)
    return int(m.groupdict()['id'])

def monkeypatch(cls):
    """Add the following function to the given class as a member function.

    Usage: @monkeypatch(pd.Series) def new_function(self, args)

    This function makes it easy to add functionality to classes like pandas.Series which are hard to subclass, as described at
    http://stackoverflow.com/questions/11979194/subclasses-of-pandas-object-work-differently-from-subclass-of-other-object

    Credit for this code goes to http://blog.carduner.net/2009/10/07/monkey-patching-decorators/
    """

    def decorator(f):
        setattr(cls, f.__name__, f)
    return decorator

@monkeypatch(pd.Series)
def display(self, audit):
    "Return a string describing a ballot and the choices marked on it"

    ballotID = self['BallotID']
    m = ballotIDre.match(ballotID)
    image = int(m.group('image'))
    show = "%s #%d (%s):\n" % (ballotID, (image - 10000) / 2, self['BallotStyleID'])

    results = []
    contest = -1
    contest_voted = True	# Avoid saying there's an missing vote for fake contest -1
    for choiceid in self.index[5:]:	# FIXME: don't rely on Choices starting at index 5
        if not math.isnan(self[choiceid]):
            if contest != audit.choiceid_contest[choice_num(choiceid)]:
                # We're coming across a new contest.  If last one wasn't voted, record that.
                if not contest_voted:
                    results.append("  invalid vote for %s" % audit.contestid_name[contest])
                contest = audit.choiceid_contest[choice_num(choiceid)]
                contest_voted = False
                results.append(" %d: %s" % (contest, audit.contestid_name[contest]))
                
            if self[choiceid] == 1:
                contest_voted = True
                results.append("  %s" % audit.choiceid_name[choice_num(choiceid)])

    return(show + "\n".join(results))

@monkeypatch(pd.Series)
def batch_name(self, audit):
    "Return just the batch name of a ballot"
    return self['BallotID'][0:5]

class Choice():
    def __init__(self, choice):
        self.choice = choice

    def name(self):
        return choice_name(self.choice.name)

    def __str__(self):
        return self.name()

class Contest():
    def __init__(self, contest):
        self.contest = contest

def main(parser):
    """Run audit_cbg with given OptionParser arguments

    Start by creating Audit class instance with parsed data.
    Publish it
    Select a seed
    Generate selections
    Print them out
    """

    (options, args) = parser.parse_args()

    #configure the root logger.  Without filename, default is StreamHandler with output to stderr. Default level is WARNING
    logging.basicConfig(level=options.debuglevel)   # ..., format='%(message)s', filename= "/file/to/log/to", filemode='w' )

    logging.debug("options: %s; args: %s", options, args)

    # Parse the CBG data
    audit = Audit(options.prefix, options.manifest)

    if options.seed:
        audit.select_ballots(options.seed, options.N)

        i = 0
        for id, s in audit.selected.iterrows():
            i += 1
            print("\n%d: %s" % (i, s.display(audit)))

if __name__ == "__main__":
    main(parser)
