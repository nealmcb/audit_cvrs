import os
import math
import operator
import logging
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django import forms
from django.contrib.admin.views.decorators import staff_member_required

def report(request, contest):
    "Generate Kaplan-Markov audit report for selected ContestBatches"

    contest = get_object_or_404(Contest, id=contest)

    selections = contest.km_select_units()

    return render_to_response('electionaudits/kmselectionreport.html',
                              {'contest': contest,
                               'selections': selections } )

"""
from electionaudits.models import *
import electionaudits.parsers

def km_selection_report(request, contest):
    "Generate Kaplan-Markov audit report for selected ContestBatches"

    contest = get_object_or_404(Contest, id=contest)

    selections = contest.km_select_units()

    return render_to_response('electionaudits/kmselectionreport.html',
                              {'contest': contest,
                               'selections': selections } )

"""
