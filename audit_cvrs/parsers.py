#!/usr/bin/env python
"""Enter CVR data.  Normally called via manage.py parse ...

%InsertOptionParserUsage%
"""

import os
import sys
import optparse
from optparse import make_option
import logging
import csv
from datetime import datetime

import audit_cvrs.util

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fooproject.settings")
from django.conf import settings

from django.db import transaction
import audit_cvrs.models as models

__author__ = "Neal McBurnett <http://neal.mcburnett.org/>"
__copyright__ = "Copyright (c) 2014 Neal McBurnett"
__license__ = "MIT"


usage = """Usage: manage.py parse [options] [file]....

Example:
 manage.py parse selections.lookup"""

option_list = (
    make_option("--contest", dest="contest",
                  help="only process CONTEST", metavar="CONTEST"),

    make_option("-e", "--election_name", default="Audit_Cvrs Test Election",
                  help="the name for this ELECTION"),

    make_option("-d", "--debug",
                  action="store_true", default=False,
                  help="turn on debugging output"),
)

parser = optparse.OptionParser(prog="parse", usage=usage, option_list=option_list)

# incorporate OptionParser usage documentation into our docstring
__doc__ = __doc__.replace("%InsertOptionParserUsage%\n", parser.format_help())

def set_options(args):
    """Return options for parser given specified arguments.
    E.g. options = set_options(["-c", "-s"])
    """

    (options, args) = parser.parse_args(args)
    return options

def main(parser):
    """obsolete and maybe broken - using management/commands/parse.py now.
    Parse and import files into the database and report summary statistics"""

    (options, args) = parser.parse_args()

    if len(args) == 0:
        args.append(os.path.join(os.path.dirname(__file__), '../../../testdata/testcum.xml'))
        logging.debug("using test file: " + args[0])

    parse(args, options)

def parse(args, options):
    "parse the files"

    if options.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    logging.basicConfig(level=loglevel) # format='%(message)s'

    logging.debug("args = %s" % list(args))

    files = []

    for arg in args:
        if os.path.isdir(arg):
            files += [os.path.join(arg, f) for f in os.listdir(arg)]
        else:
            files.append(arg)

    logging.debug("files = %s" % list(files))

    totals = {}

    logging.info("%s Start processing files" % (datetime.now().strftime("%H:%M:%S")))

    for file in files:
        logging.info("%s Processing %s" % (datetime.now().strftime("%H:%M:%S"), file))
        if file.endswith(".lookup"):
            parse_lookup(file, options)
        else:
            logging.warning("Ignoring %s - unknown extension" % file)
            continue

    logging.info("%s Exit" % (datetime.now().strftime("%H:%M:%S")))

"""
FIXME
when I put this decorator on
@transaction.commit_on_success
I get this:

    "Your database backend doesn't behave properly when "
django.db.transaction.TransactionManagementError: Your database backend doesn't behave properly when autocommit is off. Turn it on before using 'atomic'.
(django16x)neal@rf ~/py/projects/audit_cvrs$ [19/Aug/2014 19:04:55] "GET /admin/audit_cvrs/ HTTP/1.1" 200 1887
"""

def parse_lookup(file, options):
    """Parse a lookup file: a csv file of selections from Stark's auditTools.

    Sample data;

sorted_number,ballot, batch_label, which_ballot_in_batch
1, 288, s1b1, 288
2, 324, s1b1, 324
    """

    election_name = options.election_name
    election, created = models.CountyElection.objects.get_or_create(name=election_name)

    reader = csv.DictReader(open(file), skipinitialspace=True)

    for r in reader:
        batch_label = r['batch_label']
        sequence = r['which_ballot_in_batch']

        cvr_filename = audit_cvrs.util.selection_to_cvr(batch_label, sequence)

        logging.debug("Parse selection: %s %s, CVR filename = %s" % (batch_label, sequence, cvr_filename))

        try:
            cvr_text = open("/srv/voting/audit/corla/opencount-arapahoe-2014p/cvr/" + cvr_filename).read()
        except:
            cvr_text = "Cast Vote Record for Ballot %s not found" % cvr_filename

        logging.debug("Parse: selected CVR: \n%s" % cvr_text)

        models.CVR.objects.create(name=cvr_filename[:-4], cvr_text=cvr_text)  # election=election, 

if __name__ == "__main__":
    main(parser)