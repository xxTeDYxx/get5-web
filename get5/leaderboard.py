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


@leaderboard_blueprint.route("/leaderboard")
def leaderboard():
    app.logger.info('Made it to leaderboard route.')
    page = util.as_int(request.values.get('page'), on_fail=1)
    totalMatches = Match.query.order_by(-Match.id).filter_by(
        cancelled=False)
    allTeams = Team.query.order_by(-Team.id)
    dTeamStandings = defaultdict(int)
    # Build our own object with team and links, rank, and round diff?
    # Building our own object requires matches, map_stats for each match.
    # Just build a dictionary with each match and stats?
    for match in totalMatches:
        map_stats = MapStats.query.filter_by(
            match_id=match.id).first()
        # Get each winner ID and create a list that returns the Team Name, amount of wins for now.
        winningTeam = Team.query.filter_by(id=map_stats.winner).first()
        dTeamStandings[winningTeam.name] += 1

    # Sort team standings by wins. Next will be wins plus round diff.
    dTeamStandings = OrderedDict(
        sorted(dTeamStandings.items(), key=lambda x: x[1], reverse=True))

    #dMapStats[match.id] = map_stats.winner
    app.logger.info('Currently in dTeamStandings: \n{}'.format(dTeamStandings))

    return render_template('leaderboard.html', standings=dTeamStandings, page=page)
