==Installation==

==Initialization==

    ./manage.py flush --noinput
    ./manage.py parse /srv/voting/audit/corla/opencount-arapahoe-2014p/selections.lookup

    ./manage.py migrate # ?
    ./manage.py createinitialrevisions # ?  for django-reversion, Whenever you register a model with the VersionAdmin class
