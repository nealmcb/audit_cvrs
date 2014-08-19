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

    name = models.CharField(max_length=200)
    cvr_text = models.TextField()
    status = models.CharField(choices=STATUS_CHOICES, max_length=20)
    discrepancy = models.IntegerField(choices=DISCREPANCY_CHOICES, null=True, blank=True)

class CountyElection(models.Model):
    "An election, comprising a set of Contests and Batches of votes"

    name = models.CharField(max_length=200)
    random_seed = models.CharField(max_length=50, blank=True, null=True,
       help_text="The seed for random selections, from verifiably random sources.  E.g. 15 digits" )

    def __unicode__(self):
        return "%s" % (self.name)

class Contest(models.Model):
    "The name of a race, the associated margin of victory, and other parameters"

    name = models.CharField(max_length=200)
    election = models.ForeignKey(CountyElection)
    numWinners = models.IntegerField(default = 1,
                    help_text="Number of winners to be declared" )
    confidence = models.IntegerField(default = 75,
                    help_text="Desired level of confidence in percent, from 0 to 100, assuming WPM of 20%" )
    #confidence_eb = models.IntegerField(default = 50,
    #                help_text="Desired level of confidence in percent, from 0 to 100, incorporating rigorous error bounds" )
    proportion = models.FloatField(default = 100.0,
                    help_text="This county's proportion of the overall number of votes in this contest" )
    margin = models.FloatField(blank=True, null=True,
                    help_text="Calculated when data is parsed" )
    overall_margin = models.FloatField(blank=True, null=True,
                    help_text="(Winner - Second) / total including under and over votes, in percent" )
    U = models.FloatField(blank=True, null=True,
                    help_text="Total possible miscount / total apparent margin." )
    margin_offset = models.IntegerField(default = 0,
                    help_text="Reduce overall margins by this amount, e.g. for ballots yet to be counted." )

    selected = models.NullBooleanField(null=True, blank=True,
                    help_text="Whether contest has been selected for audit" )

    @transaction.commit_on_success
    def error_bounds(self):
        """Calculate winners, losers, overall Margin between each pair of them in this contest,
        and error bound 'u' for each audit unit.
        """

        choices = self.choice_set.all()
        ranked = sorted([choice for choice in choices if choice.name not in ["Under", "Over"]], key=lambda o: o.votes, reverse=True)
        winners = ranked[:self.numWinners]
        losers = ranked[self.numWinners:]

        if len(winners) == 0 or winners[0].votes == 0:
            logging.warning("Contest %s has no votes" % self)
            return

        # margins between winners and losers

        margins={}
        # FIXME: delete existing Margin database entries for this contest
        for winner in winners:
            margins[winner] = {}
            for loser in losers:
                margins[winner][loser] = max(0, winner.votes - loser.votes - self.margin_offset)

                # FIXME: Look for, deal with ties....

                margin, created = Margin.objects.get_or_create(votes = margins[winner][loser], choice1 = winner, choice2 = loser)
                margin.save()

        self.U = 0.0

        for au in self.contestbatch_set.all():
            au.u = 0.0
            vc = {}
            for voteCount in VoteCount.objects.filter(contest_batch__id__exact=au.id):
                 vc[voteCount.choice] = voteCount.votes

            for winner in winners:
                 for loser in losers:
                     if margins[winner][loser] <= 0:
                         logging.warning("Margin is %d for %s vs %s" % (margins[winner][loser], winner, loser))
                         continue
                     au.u = max(au.u, float(au.contest_ballots() + vc[winner] - vc[loser]) / margins[winner][loser])

            au.save()
            self.U = self.U + au.u

        self.save()

        return {'U': self.U,
                'winners': winners,
                'losers': losers,
                'margins': margins,
                }

    def tally(self):
        "Tally up all the choices and calculate margins"

        # First just calculate the winner and second place

        total = 0
        winner = Choice(name="None", votes=0, contest=self)
        second = Choice(name="None", votes=0, contest=self)

        for choice in self.choice_set.all():
            choice.tally()
            total += choice.votes
            if choice.name not in ["Under", "Over"]:
                if choice.votes >= winner.votes:
                    second = winner
                    winner = choice
                elif choice.votes >= second.votes:
                    second = choice

        if winner.votes > 0:
            self.margin = (winner.votes - second.votes) * 100.0 / total
            self.save()
        else:
            self.margin = -1.0       # => float('nan') after windows fix in python 2.6 
            # don't save for now - may run in to odd NULL problems

        return {'contest': self.name,
                'total': total,
                'winner': winner.name,
                'winnervotes': winner.votes,
                'second': second.name,
                'secondvotes': second.votes,
                'margin': self.margin }

    def stats(self, confidence=None, s=0.20):
        """Generate selection statistics for this Contest.
        Use given confidence (percentage). The default of None means
        to use the confidence in the database for this contest.
        The "s" parameter gives the maximum Within Precinct Miscount to assume, which
        defaults to the fraction 0.20.
        """

        if not confidence:
            confidence = self.confidence

        cbs = [(cb.contest_ballots(), str(cb.batch))
               for cb in self.contestbatch_set.all()]

        m = self.overall_margin  or  self.margin
        # Test stats with lots of audit units: Uncomment to use
        #  (Better to turn this on and off via a GET parameter....)
        # cbs = [(500,)]*300 + [(200,)]*200 + [(40,)]*100
        return selection_stats(cbs, m/100.0, self.name, alpha=((100-confidence)/100.0), s=s, proportion=self.proportion)

    def threshhold(self):
        if (self.overall_margin  or  self.margin):
            return 1.0 / (self.overall_margin  or  self.margin)
        else:
            return ""

    def ssr(self):
        """Sum of Square Roots (SSR) pseudorandom number calculated from
        our id and the random seed for the election"""

        return erandom.ssr(self.id, self.election.random_seed)

    def priority(self):
        if self.ssr() == ""  or  self.threshhold() == "":
            return ""
        else:
            return self.threshhold() / self.ssr()

    def km_select_units(self, factor=2.0, prng=None):
        """Return a list of selected contest_batches for the contest, based on error bounds and seed
        Return "factor" times as many as the current confidence level requires to show what may be needed if there are discrepancies.
        prng (Pseudo-Random Number Generator) is a function.  It defaults to Rivest's Sum of Square Roots, but
        can be specified as a function that returns numbers in the range [0, 1)
        """

        contest_batches = self.contestbatch_set.all()
        weights = [cb.u for cb in contest_batches]

        confidence = self.confidence
        if confidence == 90:	# FIXME: make this more general - use log ratio like this?
            confidence = 50

        alpha = ((100-confidence)/100.0)
        n = int(math.ceil(math.log(alpha) / math.log(1.0 - (1.0 / self.U))) * factor)	#  FIXME: deal with U = None

        if not prng:
            # The default pseudo-random number generator is to call ssr (Rivest's Sum of Square Roots algorithm)
            # with an incrementing first argument, and the current election seed: ssr(1, seed); ssr(2, seed), etc.
            prng = itertools.imap(erandom.ssr, itertools.count(1), itertools.repeat(self.election.random_seed)).next

        # FIXME: avoid tricks to retain random values here and make this and weightedsample() into
        # some sort of generator that returns items that are nicely bundled with associated random values
        random_values = [prng() for i in range(n)]
        prng_replay = iter(random_values).next

        return zip(erandom.weightedsample(contest_batches, weights, n, replace=True, prng=prng_replay), random_values)

    def select_units(self, stats):
        """Return a list of contest_batches for the contest,
        augmented with ssr, threshhold and priority, 
        in selection priority order if possible"""

        contest_batches = self.contestbatch_set.all()

        wpm = 0.2

        audit_units = []
        for cb in contest_batches:
            cb.stats = stats
            cb.margin = self.overall_margin  or  self.margin
            cb.ssr = cb.batch.ssr()
            cb.threshhold = 1.0 - math.exp(-(cb.contest_ballots() * 2.0 * wpm) / stats['negexp_w'])
            if cb.ssr != "":
                cb.priority = cb.threshhold / cb.ssr
            else:
                cb.priority = ""
            audit_units.append(cb)

            if audit_units[0].priority != "":
                audit_units.sort(reverse=True, key=operator.attrgetter('priority'))

        return audit_units

    def __unicode__(self):
        return "%s" % (self.name)

class Batch(models.Model):
    "A batch of ballots all counted at the same time and stored together"

    name = models.CharField(max_length=200)
    election = models.ForeignKey(CountyElection)
    type = models.CharField(max_length=20, help_text="AB for Absentee, EV for Early, ED for Election")
    ballots = models.IntegerField(null=True, blank=True,
                    help_text="Number of ballots in the batch" )
    random = models.FloatField(null=True, blank=True,
                    help_text="Random number assigned for selection" )
    notes = models.CharField(max_length=200, null=True, blank=True,
                    help_text="Free-form notes" )

    @transaction.commit_on_success
    def merge(self, other):
        "merge this Batch with another Batch, along with associated ContestBatches and VoteCounts"

        if self.election != other.election:
            logging.error("Error: %s is election %d but %s is election %d" % (self, self.election, other, other.election))

        if self.type != other.type:
            logging.error("Error: %s is type %d but %s is type %d" % (self, self.type, other, other.type))

        for other_cb in other.contestbatch_set.all():
            my_cb, created = ContestBatch.objects.get_or_create(contest = other_cb.contest, batch = self)
            my_cb.merge(other_cb)

        self.name += "+" + other.name
        self.ballots += other.ballots
        self.notes = (self.notes or "") + "; " + (other.notes or "")

        self.save()
        other.delete()

    def ssr(self):
        """Sum of Square Roots (SSR) pseudorandom number calculated from
        batch id and the random seed for the election"""

        return erandom.ssr(self.id, self.election.random_seed)

    def __unicode__(self):
        return "%s:%s" % (self.name, self.type)

    class Meta:
        unique_together = ("name", "election", "type")

class ContestBatch(models.Model):
    "The set of VoteCounts for a given Contest and Batch"

    contest = models.ForeignKey(Contest)
    batch = models.ForeignKey(Batch)
    u = models.FloatField(blank=True, null=True,
                    help_text="Maximum miscount / total apparent margin." )
    selected = models.NullBooleanField(null=True, blank=True,
                    help_text="Whether audit unit has been specifically targeted for audit" )
    notes = models.CharField(max_length=200, null=True, blank=True,
                    help_text="Free-form notes" )

    def threshhold(self):
        wpm = 0.2
        return 1.0 - math.exp(-(self.contest_ballots() * 2.0 * wpm) / self.contest.stats()['negexp_w'])

    def contest_ballots(self):
        "Sum of recorded votes and under/over votes.  C.v. batch.ballots"
        return sum(a.votes for a in self.votecount_set.all())

    @transaction.commit_on_success
    def merge(self, other):
        "merge this ContestBatch with another ContestBatch, along with associated VoteCounts"

        logging.debug("merging: %s and %s" % (self, other))

        for other_vc in other.votecount_set.all():
            my_vc, created = VoteCount.objects.get_or_create(contest_batch = self, choice = other_vc.choice, defaults={'votes': 0})
            logging.debug("merging: %s and %s" % (my_vc, other_vc))
            my_vc.votes += other_vc.votes
            my_vc.save()
            other_vc.delete()

        self.notes = (self.notes or "") + "; " + (other.notes or "") + "; M: " + str(self)
        self.save()
        other.delete()

    def taintfactor(self, discrepancy):
        "Taint for a given discrepancy - assume it is for closest margin"

        # First figure out the minumum margin of all pairs of winners and losers for this contest
        min_margin = sys.maxint
        for choice in self.contest.choice_set.all():
            min_margin = min([min_margin] + [margin.votes for margin in Margin.objects.filter(choice1__exact = choice.id)])

        maxrelerror = discrepancy * 1.0 / min_margin
        taint = maxrelerror / self.u
        return (1.0 - (1.0 / self.contest.U)) / (1.0 - taint)

    def __unicode__(self):
        return "%s:%s" % (self.contest, self.batch)

    class Meta:
        unique_together = ("contest", "batch")

class Choice(models.Model):
    "A candidate or issue name: an alternative for a Contest"

    name = models.CharField(max_length=200)
    votes = models.IntegerField(null=True, blank=True)
    contest = models.ForeignKey(Contest)

    def tally(self):
        "Tally up all the votes for this choice and save result"

        from django.db import connection
        cursor = connection.cursor()
        cursor.execute('SELECT sum(votes) AS total_votes FROM electionaudits_votecount WHERE "choice_id" = %d' % self.id)

        row = cursor.fetchone()
        self.votes = row[0]
        self.save()
        return self.votes

    def __unicode__(self):
        return "%s" % (self.name)

class VoteCount(models.Model):
    "The count of votes for a particular Choice in a ContestBatch"

    votes = models.IntegerField()
    choice = models.ForeignKey(Choice)
    contest_batch = models.ForeignKey(ContestBatch)

    def __unicode__(self):
        return "%d\t%s\t%s\t%s" % (self.votes, self.choice.name, self.contest_batch.contest, self.contest_batch.batch)

    class Meta:
        unique_together = ("choice", "contest_batch")

def selection_stats(units, margin=0.01, name="test", alpha=0.08, s=0.20, proportion=100.0):
    """Prepare statistics on how many audit units should be selected
    in order to be able to reduce the risk of confirming an incorrect
    outcome to a given probability.
    units = a list of audit units, giving just size of each
    margin = margin of victory, between 0 and 1
    name = name for this contest
    alpha = significance level desired = 1 - confidence
    s = maximum within-precinct miscount as a fraction from 0.0 to 1.0
    proportion = This county's proportion of the overall number of votes in this contest

    Capture a dictionary of statistics and printed results.
    Cache the results for speed.
    """

    cachekey = "%s:%r:%f:%f:%f" % (name, margin, alpha, s, proportion)
    saved = cache.get(cachekey)
    logging.debug("selection_stats: %d cached. contest %s" % (len(cache._expire_info), name))

    if saved:
        return saved

    if not margin:
        return {}

    save = sys.stdout
    sys.stdout = StringIO.StringIO()
    try:
        stats = varsize.paper(units, name, margin, alpha, s)
    except Exception, e:
        logging.exception("selection_stats: contest %s" % (name))
        return {}
    stats['prose'] = sys.stdout.getvalue()
    sys.stdout = save

    for stat in ['ppebwr_work', 'ppebwr_precincts',
                 'negexp_work', 'negexp_precincts', 
                 'safe_work', 'safe_precincts', ]:
        stats[stat] = stats[stat] * proportion/100.0

    cache.set(cachekey, stats, 86400)
    return stats

class Margin(models.Model):
    "Margin in votes between two Choices for a given tabulation"

    votes = models.IntegerField()
    choice1 = models.ForeignKey(Choice, related_name = 'choice1')
    choice2 = models.ForeignKey(Choice, related_name = 'choice2')

    def __unicode__(self):
        return "%s-%s" % (self.choice1.name, self.choice2.name)

    class Meta:
        unique_together = ("choice1", "choice2")
