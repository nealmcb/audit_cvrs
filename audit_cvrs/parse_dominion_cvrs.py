#!/usr/bin/env python
"""
Parse the Cast Vote Records (CVR) data from a Dominion voting system,
and produce a cvr.csv file.

Read the CandidateManifest.json file to map ids to candidate names.
Read the CvrExport.json file for the CVR data.
Print out a cvr.csv file

Usage:

cd dominion-cvr-directory
parse_dominion_cvrs.py zip-file > cvr.csv

also produces test.lookup file, and summaries in debugging output

Todo:

Cleanup:
  Rip out unused "votes" variable
  make into a proper module, usable from other code, with a main

Optionally record MarkDensity information (modifying current debugging code)
Optionally record data on Modified (adjudicated) ballots
 perhaps integrate with NOVOTE output
Summarize MarkDensity variance by ballot, identify interesting ones

Parse ElectionId and use it to name CountyElection in electionAudits

Perhaps convert TabulatorID and BatchID into BoxID to help preserve unlinkability.
Perhaps sort output by something like BoxID, if that would help match results with Philip's auditTools?

Optional entry of upper bound for number of phantom paper ballots, for evil zombie entries
"""

import sys
import json
import csv
import collections
import logging
import zipfile
import sampler

def select_ballots(seed, n, N):
    "Randomly select n of N ballots using Rivest's sampler library"

    old_output_list, new_output_list = sampler.generate_outputs(n, True, 0, N, seed, False)

    new_output_list = sorted(new_output_list)

    logging.warning("Output list: %s" % new_output_list)

    return (new_output_list)

def parse():

    logging.basicConfig(level=logging.DEBUG)

    zipf = zipfile.ZipFile(sys.argv[1])

    with zipf.open("ContestManifest.json") as jsonFile:
        rawJson = jsonFile.read()
        logging.debug("ContestManifest.json raw contents:\n%s" % rawJson)

        contestManifest = json.loads(rawJson)

        contests = collections.OrderedDict()

        for contest in contestManifest['List']:
            contests[contest['Id']] = contest['Description']

        numContests = len(contests)

        logging.debug("Manifest for %d contests:\n%s" % (numContests, contests.items()))

    with zipf.open("CandidateManifest.json") as jsonFile:
        rawJson = jsonFile.read()
        logging.debug("CandidateManifest.json raw contents:\n%s" % rawJson)

        candidateManifest = json.loads(rawJson)

        unordered_candidates = {}

        for candidate in candidateManifest['List']:
            unordered_candidates[candidate['Id']] = "%s\t%s" % (contests[candidate['ContestId']], candidate['Description'])

        logging.debug(sorted(unordered_candidates.items()))

    candidates = collections.OrderedDict(sorted(unordered_candidates.items()))
    numCandidates = len(candidates)

    headers = "TabulatorId,BatchId,RecordId,CountingGroupId,IsCurrent,BallotTypeId,PrecinctPortionId,"

    numColumns = numCandidates + headers.count(",")

    # Produce a candidateIndex to map candidate Ids from json to sequential numbers starting at 0, as they should appear in the CSV
    candidateIndex = {}
    i = 0
    for id, name in candidates.iteritems():
        if "," in name:
            print "Error: Found , in name"
        headers += "%s," % name
        candidateIndex[id] = i
        i += 1

    headers = headers.strip(",")

    logging.info("Found %d candidates:\n%s" % (numCandidates, candidates))
    logging.info(candidateIndex)

    logging.info("First manifest item: %s" % candidateManifest['List'][1])

    print(headers)

    seed = "1234"
    N = 1344
    n = 16

    selected = select_ballots(seed, n, N)

    sample_lookup_name = "test.lookup"
    sample_lookup = open(sample_lookup_name, "w")

    sample_lookup.write('sorted_number,ballot, batch_label, which_ballot_in_batch\n')

    n = 0
    sample_index = 0
    totals = [0] * numCandidates
    contestBallots = collections.Counter()
    contestBallotsByBatchManager = {}    # Counters for each contest giving number of ballots by batch

    logging.debug("Density:TabulatorId,BatchId,RecordId,CountingGroupId,IsAmbiguous,MarkDensity,Rank,PartyId")

    # with open("CvrExport.json") as jsonFile:
    for zipinfo in zipf.infolist():
        logging.info("Encountering exported file %s" % zipinfo.filename)

        if "CvrExport" in zipinfo.filename:
            rawJson = zipf.open(zipinfo.filename).read()
            #rawJson = jsonFile.read()        # FIXME: better to use ijson here and not read it all in at once
            cvrs = json.loads(rawJson)

            # Process each session as a ballot
            for session in cvrs['Sessions']:
                n += 1

                # print("Session keys: %s" % session.keys())

                sessionInfo = "%s,%s,%s,%s" % (session['TabulatorId'], session['BatchId'], session['RecordId'], session['CountingGroupId'])

                original = session['Original']

                modified = session.get('Modified', None)
                if modified:
                    if original['IsCurrent'] != False:
                        logging.error("Surprised to see IsCurrent != false given presence of Modified record. It has IsCurrent=%s\n%s" % (modified['IsCurrent'], original))

                    original = modified

                # print original.keys()

                ballotInfo = "%s,%s,%s" % (original['IsCurrent'], original['BallotTypeId'], original['PrecinctPortionId'])

                voteArray = ["0"] * numCandidates
                votes = ""
                for contest in original['Contests']:
                    contestBallots[contest['Id']] += 1
                    contestBallotsByBatch = contestBallotsByBatchManager.get(contest['Id'], collections.Counter())
                    contestBallotsByBatch[session['BatchId']] += 1
                    contestBallotsByBatchManager[contest['Id']] = contestBallotsByBatch

                    votes += "%s," % contest['Id']

                    marks = contest['Marks']
                    if len(marks) > 1:
                        votemarks = [mark for mark in marks if mark['IsVote']]
                        if len(votemarks) > 1:
                            logging.error("FIXME: More than 1 IsVote mark: I can't handle this yet. Council race? %s" % marks) # '\n'.join(list(marks)))
                        marks = votemarks

                    if len(marks) == 0:
                        votes += "-1,"
                    else:
                        mark = marks[0]
                        if mark['IsVote']:
                            voteArray[candidateIndex[mark['CandidateId']]] = "1"
                            votes += "%s," % mark['CandidateId']
                        else:
                            votes += "NOVOTE:%s," % (mark['CandidateId'])
                            logging.error("NOVOTE for %s" % mark)

                    logging.debug("Density:%s,%s,%s,%s,%s" % (sessionInfo, mark['IsAmbiguous'], mark['MarkDensity'], mark['Rank'], mark.get('PartyId')))

                    # print("%s %d" % (contest.keys(), len(contest['Marks'])))
                    # votes +=

                row = ("%s,%s,%s" % (sessionInfo, ballotInfo, ','.join([v for v in voteArray])))
                if row.count(",") + 1 != numColumns:
                    logging.error("FIXME: problem in row, %d columns, not %d. %s" % (row.count(",") + 1, numColumns, row) )
                else:
                    print(row)
                    totals = [totals[i] + int(voteArray[i])  for i in xrange(numCandidates)]

                    if n in selected:
                        sample_index += 1
                        #batch = "%s_%s_%s" % (session['TabulatorId'], session['BatchId'], session['CountingGroupId'])
                        batch = "%s" % (session['BatchId'])
                        sample_lookup.write("%d,%d,%s,%d\n" % (sample_index, n, batch, session['RecordId']))  # FIXME: is RecordId the proper sequence number? or use sequence in file??

                # row = ("%s,%s,%s" % (sessionInfo, ballotInfo, votes))
                # remove trailing comma
                # print(row.strip(','))

                #if not original.get(["IsCurrent"]):
                #  print "not current: %d: %s" % (n, original["IsCurrent"])

    if n != N:
        logging.error("Ballot count mismatch: told %d, found %d" % (N, n))

    candidateRevIndex = {v: k for k, v in candidateIndex.iteritems()}

    for i in xrange(numCandidates):
        logging.warning("Total: %s" % str((totals[i], candidates[candidateRevIndex[i]])))

    print contestBallots.most_common(10)

    for contestId in sorted(contestBallots):
        logging.warning("%d Ballots for contest %s" % (contestBallots[contestId], contests[contestId]))

    import pandas as pd
    df = pd.DataFrame.from_dict(contestBallotsByBatchManager, orient='index').transpose()
    # hmmm - how to add the contest name (Description) to the mix? df['Contest'] = apply(
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        print df.describe().transpose()

    print("Contest\tBatch\tBallots")
    for contest in sorted(contestBallotsByBatchManager.keys()):
        for batchId in contestBallotsByBatchManager[contest].keys():
            print("%s\t%s\t%d" % (contest, batchId, contestBallotsByBatchManager[contest][batchId]))

    print "Done"

def main():
    parse()

if __name__ == "__main__":
    main()
