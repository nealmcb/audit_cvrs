**audit_cvrs** helps auditors manage a ballot-level risk-limiting post-election audit.
It reads in a variety of cast vote record formats,
does the random selection in the quasi-standard way that [Philip Stark's online tool](https://www.stat.berkeley.edu/~stark/Java/Html/auditTools.htm) does,
allows auditors to assign and track the status of ballots as they're audited,
provides point-and-click access to selected CVRs to provide the system interpretation of the ballot,
logs events during the audit with timestamps, and produces an audit report.

The user interface is a web application based on a local Django server and can support multiple users simultaneously.

# Installation

Tested on Ubuntu Trusty 14.04 with Django 1.6.1

First install necessary packages:

    apt-get install python-django-debug-toolbar python-django-extensions python-django-south python-django-reversion python-werkzeug

In a virtualenv if desired, include this useful debugging tool:

    pip install django-databrowse

# Preparation for real audit

Common steps:

* Run the election
* Obtain overall margin of victory for audit calculations
* Publish Tally and Cast Vote Records

## To audit Clear Ballot election

* Run `audit_cbg.py` to produce selections.lookup file

E.g. `./audit_cbg.py -p ../test/cbg/fl_bay_2012m -s 95562794305371208920 -n 16 > /tmp/audit_cbg.out`

* The beginning of `/tmp/audit_cbg.out` has a csv file: a header and 16 rows in this case. Copy that part to a file `selections.lookup`

## To audit Dominion election

* Use `parse_dominion_cvrs.py` along with `audit_cbg.py` to produce selections.lookup file. The steps aren't currently all automated, and the format could use more work.

# Initialization of database

In the `audit_cvrs` directory:

    ./manage.py syncdb   # and create an admin user, with password and optional email
    ./manage.py parse selections.lookup # You'll need to edit a hard-coded path in cvr.py first

    ./manage.py migrate
    ./manage.py createinitialrevisions

To start over with cvr database: `./manage.py flush --noinput`

# Run server and frontend

    ./manage.py runserver_plus

    Open the Audit CVRs application in your browser, e.g. http://127.0.0.1:8000/

    Follow the directions on that web page, which you can also see in audit_cvrs/templates/index.html
