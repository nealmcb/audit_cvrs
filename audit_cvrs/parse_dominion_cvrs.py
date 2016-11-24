#!/usr/bin/env python
"""
Read the Cast Vote Records (CVRs) from a Dominion voting system.

Todo:

FIXME:
some columns not lining up
"""

import sys
import json
import csv
import collections
import logging

logging.basicConfig(level=logging.DEBUG)

# print open("CandidateManifest.json").read()

with open("CandidateManifest.json") as jsonFile:
  rawJson = jsonFile.read()
  candidateManifest = json.loads(rawJson)

  unordered_candidates = {}

  for candidate in candidateManifest['List']:
    unordered_candidates[candidate['Id']] = candidate['Description']

  logging.debug(sorted(unordered_candidates.items()))

candidates = collections.OrderedDict(sorted(unordered_candidates.items()))
numCandidates = len(candidates)

headers = "TabulatorId,BatchId,RecordId,IsCurrent,BallotTypeId,PrecinctPortionId,"

columns = numCandidates + headers.count(",")

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

# print candidateManifest['List'][1]

print(headers)

with open("CvrExport.json") as jsonFile:
  rawJson = jsonFile.read()
  cvrs = json.loads(rawJson)

  n = 0
  for session in cvrs['Sessions']:
    n += 1

    # print("Session keys: %s" % session.keys())

    sessionInfo = "%s,%s,%s" % (session['TabulatorId'], session['BatchId'], session['RecordId'])

    original = session['Original']
    # print original.keys()

    ballotInfo = "%s,%s,%s" % (original['IsCurrent'], original['BallotTypeId'], original['PrecinctPortionId'])

    voteArray = ["0"] * numCandidates
    votes = ""
    for contest in original['Contests']:
      votes += "%s," % contest['Id']

      marks = contest['Marks']
      if len(marks) > 1:
        logging.error("FIXME: More than 1 mark: I can't handle this yet. Council race? %s" % marks)
        
      elif len(marks) == 0:
        votes += "-1,"
      else:
        mark = marks[0]
        if mark['IsVote']:
          voteArray[candidateIndex[mark['CandidateId']]] = "1"
          votes += "%s," % mark['CandidateId']
        else:
          votes += "NOVOTE:%s," % (mark['CandidateId'])

      logging.info("%s,%s,%s,%s,%s" % (sessionInfo, mark['IsAmbiguous'], mark['MarkDensity'], mark['Rank'], mark.get('PartyId')))

      # print("%s %d" % (contest.keys(), len(contest['Marks'])))
      # votes += 

    row = ("%s,%s,%s" % (sessionInfo, ballotInfo, ','.join([v for v in voteArray])))
    if row.count(",") + 1 != columns:
      logging.error("FIXME: problem in row, %d columns, not %d. %s" % (row.count(",") + 1, columns, row) )
    else:
      print(row)

    # row = ("%s,%s,%s" % (sessionInfo, ballotInfo, votes))
    # remove trailing comma
    # print(row.strip(','))

    #if not original.get(["IsCurrent"]):
    #  print "not current: %d: %s" % (n, original["IsCurrent"])
