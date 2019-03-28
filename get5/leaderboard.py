from flask import Blueprint, request, render_template, flash, g, redirect, jsonify, Markup, json

import steamid
import get5
from get5 import app, db, BadRequestError, config_setting
from models import User, Team, Match, GameServer, MapStats
from collections import OrderedDict, defaultdict
import util
import re
from copy import deepcopy


leaderboard_blueprint = Blueprint('leaderboard', __name__)


def fuckLambdas():
    return MatchRes()


class MatchRes():
    def init(self):
        self.wins = 0
        self.losses = 0


@leaderboard_blueprint.route("/leaderboard")
def leaderboard():
    app.logger.info('Made it to leaderboard route.')
    page = util.as_int(request.values.get('page'), on_fail=1)
    totalMatches = Match.query.order_by(-Match.id).filter_by(
        cancelled=False)
    allTeams = Team.query.order_by(-Team.id)
    # Shoutouts to n3rds.
    dTeamStandings = defaultdict(lambda: {'wins': 0, 'losses': 0, 'rounddiff': 0})
    # Build our own object with team and links, rank, and round diff?
    # Building our own object requires matches, map_stats for each match.
    # Just build a dictionary with each match and stats?
    for match in totalMatches:
        map_stats = MapStats.query.filter_by(
            match_id=match.id).first()
        # Get each winner ID and create a list that returns the Team Name, amount of wins for now.
        winningTeam = Team.query.filter_by(id=map_stats.winner).first()
        # Get the losing team.
        if map_stats.winner == match.team1_id:
            losingTeam = Team.query.filter_by(id=match.team2_id).first()
            winningRounds = map_stats.team1_score
            losingRounds = map_stats.team2_score
        else:
            losingTeam = Team.query.filter_by(id=match.team1_id).first()
            losingRounds = map_stats.team1_score
            winningRounds = map_stats.team2_score

        dTeamStandings[winningTeam.name]['wins'] += 1
        # Get which team they were on and subtract the rounds won from lost.
        dTeamStandings[winningTeam.name]['rounddiff'] += (winningRounds - losingRounds)
        dTeamStandings[losingTeam.name]['losses'] += 1
        dTeamStandings[losingTeam.name]['rounddiff'] += (losingRounds - winningRounds)
    # Sort team standings by wins. Next will be wins plus round diff.
    dTeamStandings = OrderedDict(
        sorted(dTeamStandings.items(), key=lambda x: (x[1].get('wins'), x[1].get('losses'), x[1].get('rounddiff')), reverse=True))
    app.logger.info('Currently in dTeamStandings: \n{}'.format(dTeamStandings))

    return render_template('leaderboard.html', standings=dTeamStandings, page=page)
