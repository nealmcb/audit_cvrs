"""Generate a relationship diagram via django-extensions and
 ./manage.py graph_models audit_cvrs -g -o ../doc/model_graph.png --settings settings_debug
"""

import sys
import math
import logging
import StringIO
import operator
import itertools
from django.db import models
from django.db import transaction
from django.core.cache import cache
# import electionaudits.erandom as erandom

class CountyElection(models.Model):
    "An election, comprising a set of CVRs etc."

    name = models.CharField(max_length=200)
    random_seed = models.CharField(max_length=50, blank=True, null=True,
       help_text="The seed for random selections, from verifiably random sources.  E.g. 15 digits" )

    def __unicode__(self):
        return "%s" % (self.name)

class CVR(models.Model):
    "A Cast Vote Record: the selections made on a given ballot"

    STATUS_CHOICES = (
        ("Not seen", "Not seen"),
        ("Assigned", "Assigned"),
        ("Completed", "Completed"),
        ("Incomplete", "Incomplete"),
        )

    DISCREPANCY_CHOICES = (
        (-2, '2-vote understatement'),
        (-1, '1-vote understatement'),
        (0,  'Interpretations match'),
        (1,  '1-vote overstatement'),
        (2,  '2-vote overstatement'),
        )

    # election = models.ForeignKey(CountyElection)
    name = models.CharField(max_length=200)
    cvr_text = models.TextField()
    status = models.CharField(choices=STATUS_CHOICES, default="Not seen", max_length=20)
    discrepancy = models.IntegerField(choices=DISCREPANCY_CHOICES, null=True, blank=True)
    # notes = models.TextField(default="")

    def __unicode__(self):
        return "%s: %s / %s" % (self.name, self.status, self.discrepancy)

    class Meta:
        unique_together = ("name",)  # "election", 
