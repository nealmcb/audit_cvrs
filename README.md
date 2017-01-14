**audit_cvrs** helps auditors manage a ballot-level risk-limiting post-election audit.
It reads in a variety of cast vote record formats,
does the random selection using Rivest's quasi-standard "sampler" method, as used by
[Philip Stark's online tool](https://www.stat.berkeley.edu/~stark/Java/Html/auditTools.htm),
allows auditors to assign and track the status of ballots as they're audited,
provides point-and-click access to selected CVRs to provide the system interpretation of the ballot,
logs events during the audit with timestamps, and produces an audit report.

The user interface is a web application based on a local Django server and can support multiple users simultaneously.

# Goals
It is important to emphasize that the output of an audit should be
a report providing evidence related to election outcome, details about and explanations of any discrepancies found,
and conclusions based on that evidence.  See the paper
[Evidence-Based Elections Stark and Wagner](http://www.stat.berkeley.edu/~stark/Preprints/evidenceVote12.pdf)
and the report [Risk-Limiting Post-Election Audits: Why and How](http://www.stat.berkeley.edu/~stark/Preprints/RLAwhitepaper12.pdf).
An example of this sort of report is provided in the documentation.
This audit support software is only used for convenience,
using publicly verifiable inputs in a transparent way and producing publicly verifiable results.
It thus does not present any new issues of
[Software Independence (Rivest and Wack)](http://people.csail.mit.edu/rivest/RivestWack-OnTheNotionOfSoftwareIndependenceInVotingSystems.pdf).

The eventual goals of this software are:

 * Load and parse all the voting system CVR data automatically
 * Support audits of all contests
 * Calculate and print audit workload information, configuration, plan etc.
 * Publish the data to be audited on the web, publish a commitment (hash) in various blockchains etc.
 * Prompt for the rolling of the dice and input of the resulting random seed
 * Perform the ballot selections in a standardized way based on that random seed and the CVRs
 * Print out a tally sheet to give to the people who will retrieve the boxes and pull the ballots
 * Include useful information to find the ballot in the box.  E.g. tell them which end of the stack of ballots to start counting from, how many to count when starting from that end, etc.
 * Provide entry form for manual CVR, customized to the expected ballot style (in the order found on the ballot) for entry of the auditors own vote interpretations into the database
 * Compare that manual CVR with the original system CVR and record discrepancies
 * Lead auditors thru a good procedure for discrepancies, e.g. did they find the right ballot (perhaps check ballot style up-front?), can you help them find it, etc.
 * Track the progress of the audit in reducing risk, how many ballots remain according to the plan, time estimates
 * Produce a nice audit report at the end, including the plan, results, calculated risk levels, an audit log with timestamps for each iteration of each step above, timing summary information, etc

# Installation

Tested on Ubuntu Trusty 14.04 with Django 1.9

First install necessary packages:

    mkvirtualenv django19
    workon django19
    pip install Django==1.9 django-reversion django-extensions django-debug_toolbar Werkzeug

# Testing

# Preparation for real audit

Common steps:

* Run the election
* Obtain overall margin of victory for audit calculations

For example, the command `rlacalc.py -m 2` will calculate the expected sample size for a 2% margin.

See `rlacalc.py -h` for additional options.

* Publish Tally and Cast Vote Records

## To audit Dominion election

    audit_cvrs/parse_dominion_cvrs.py test/dominion-clear-creek-CVR_Export_20160713143950.zip  > /tmp/q1 2>/tmp/q2
    mv test.lookup selections.lookup

## To audit Clear Ballot election

* Run `audit_cbg.py` to produce selections.lookup file

E.g. `./audit_cbg.py -p ../test/cbg/fl_bay_2012m -s 95562794305371208920 -n 16 > /tmp/audit_cbg.out`

* The beginning of `/tmp/audit_cbg.out` has a csv file: a header and 16 rows in this case. Copy that part to a file `selections.lookup`

# Initialization of database

In the base `audit_cvrs` directory:

    ./manage.py migrate --run-syncdb
    ./manage.py createsuperuser --username=demo --email=demo@example.com

    # FIXME: add csv file option to parse command
    # For now, edit a magic hard-coded path in cvr.py first to match csv file that came out of parsing above
    ./manage.py parse selections.lookup

    ./manage.py createinitialrevisions

To start over with cvr database: `./manage.py flush --noinput`

# Run server and frontend

    ./manage.py runserver_plus

    Open the Audit CVRs application in your browser, e.g. http://127.0.0.1:8000/

    Follow the directions on that web page, which you can also see in audit_cvrs/templates/index.html
