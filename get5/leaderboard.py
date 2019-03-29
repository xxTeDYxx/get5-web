from flask import Blueprint, request, render_template, flash, g, redirect, jsonify, Markup, json

import steamid
import get5
from get5 import app, db, BadRequestError, config_setting
from models import User, Team, Match, GameServer, MapStats, TeamLeaderboard
from collections import OrderedDict, defaultdict
import util
import re
from copy import deepcopy


leaderboard_blueprint = Blueprint('leaderboard', __name__)


@leaderboard_blueprint.route("/leaderboard")
def leaderboard():
    app.logger.info('Made it to leaderboard route.')
    page = util.as_int(request.values.get('page'), on_fail=1)
    totalMatches = Match.query.order_by(-Match.id).filter_by(
        cancelled=False)
    allTeams = Team.query.order_by(-Team.id)
    # Shoutouts to n3rds.
    dTeamStandings = defaultdict(lambda: {'teamid': 0, 'wins': 0, 'losses': 0, 'rounddiff': 0})
    # Build our own object with team and links, rank, and round diff?
    # Building our own object requires matches, map_stats for each match.
    # Just build a dictionary with each match and stats?
    for match in totalMatches:
        map_stats = MapStats.query.filter_by(
            match_id=match.id).first()
        # Get each winner ID and create a list that returns the Team Name, amount of wins for now.
        winningTeam = Team.query.filter_by(id=map_stats.winner).first()
        # Get the losing team, and scores for round difference.
        if map_stats.winner == match.team1_id:
            losingTeam = Team.query.filter_by(id=match.team2_id).first()
            winningRounds = map_stats.team1_score
            losingRounds = map_stats.team2_score
        else:
            losingTeam = Team.query.filter_by(id=match.team1_id).first()
            losingRounds = map_stats.team1_score
            winningRounds = map_stats.team2_score

        # Update winning and losing teams.
        dTeamStandings[winningTeam.name]['teamid'] = winningTeam.id
        dTeamStandings[winningTeam.name]['wins'] += 1
        dTeamStandings[winningTeam.name]['rounddiff'] += (winningRounds - losingRounds)

        dTeamStandings[losingTeam.name]['teamid'] = losingTeam.id
        dTeamStandings[losingTeam.name]['losses'] += 1
        dTeamStandings[losingTeam.name]['rounddiff'] += (losingRounds - winningRounds)
    # Sort teams via lexigraphical sort, very inefficient but it works for now.
    # TODO: Create a class for this instead of using dicts, and make list of class.
    dTeamStandings = OrderedDict(
        sorted(dTeamStandings.items(), key=lambda x: (x[1].get('wins'), x[1].get('losses'), x[1].get('rounddiff')), reverse=True))
    # app.logger.info('Currently in dTeamStandings: \n{}'.format(dTeamStandings))

    return render_template('leaderboard.html', standings=dTeamStandings, page=page)
