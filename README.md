==Installation==

Tested on Ubuntu Trusty 14.04 with Django 1.6.1

First install necessary packages:

    apt-get install python-django-debug-toolbar python-django-extensions python-django-south python-django-reversion python-werkzeug

In a virtualenv if desired:

    pip install django-databrowse

==Initialization==

    ./manage.py flush --noinput
    ./manage.py parse /srv/voting/audit/corla/opencount-arapahoe-2014p/selections.lookup

    ./manage.py migrate # ?
    ./manage.py createinitialrevisions # ?  for django-reversion, Whenever you register a model with the VersionAdmin class

==Run==

    ./manage.py runserver_plus
