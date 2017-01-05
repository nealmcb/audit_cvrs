import os
import logging
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import audit_cvrs.parsers

class Command(BaseCommand):
    # FIXME before django 1.10: upgrade method of picking up options from audit_cvrs.parsers
    option_list = audit_cvrs.parsers.option_list + BaseCommand.option_list
    help = ("Parse and save audit_cvrs data")
    args = "[filename]"
    label = 'filename'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        "create the options argument from audit_cvrs.parsers.set_options()"

        if len(args) < 1:
            args = [(os.path.join(os.path.dirname(__file__), '../../../testdata/testcum.xml'))]
            logging.debug("using test file: " + args[0])

        audit_cvrs.parsers.parse(args, Bunch(**options))

class Bunch:
    """Map a dictionary into a class for standard optparse referencing syntax"""

    def __init__(self, **kwds):
        self.__dict__.update(kwds)
