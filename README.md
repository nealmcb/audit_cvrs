==Installation==

Tested on Ubuntu Trusty 14.04 with Django 1.6.1

First install necessary packages:

    apt-get install python-django-debug-toolbar python-django-extensions python-django-south python-django-reversion python-werkzeug

In a virtualenv if desired:

    pip install django-databrowse

==Preparation==
Run the election, save Cast Vote Records, create a manifest of how many ballots are in each batch, e.g.

    s1b1,1:1050
    s1b2,1051:2100
    s1b3,2101:3150

Generate selection via http://www.stat.berkeley.edu/~stark/Vote/auditTools.htm, yielding e.g.

    sorted_number,ballot, batch_label, which_ballot_in_batch
    1, 288, s1b1, 288
    2, 324, s1b1, 324
    3, 377, s1b1, 377

from test/selections.lookup
or /srv/voting/audit/corla/opencount-arapahoe-2014p/selections.lookup

==Initialization==

    ./manage.py syncdb   # and create an admin user, with password and optional email
    ./manage.py parse selections.lookup

    ./manage.py migrate		       # ?
    ./manage.py createinitialrevisions # ?  for django-reversion, Whenever you register a model with the VersionAdmin class

    # to start over with cvr database: ./manage.py flush --noinput

==Run==

    ./manage.py runserver_plus

    Open the Audit CVRs application in your browser, e.g. http://127.0.0.1:8000/

    and follow the directions.

    http://127.0.0.1:8000/admin/audit_cvrs/cvr/