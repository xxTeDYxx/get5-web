from flask import Blueprint, request, render_template, flash, g, redirect, jsonify, Markup, json

import steamid
import get5
from get5 import app, db, BadRequestError, config_setting
from models import User, Team, Match, GameServer, MapStats, PlayerStats, Season
from collections import OrderedDict, defaultdict
from datetime import datetime
from statistics import mean
import util
import re
from copy import deepcopy

# Since we use the same logic for getting a leaderboard based on total
# and on season, just wrap it in one function to avoid code reuse.


def getLeaderboard(seasonid=None):
    if seasonid is None:
        totalMatches = Match.query.order_by(-Match.id).filter(
            Match.cancelled == False, Match.end_time.isnot(None), Match.winner.isnot(None))
        seasonsBoard = False
    else:
        totalMatches = Match.query.order_by(-Match.id).filter(
            Match.cancelled == False, Match.end_time.isnot(None),
            Match.season_id == seasonid, Match.winner.isnot(None))
        seasonsBoard = True
        season = Season.query.get_or_404(seasonid)
    allTeams = Team.query.order_by(-Team.id)
    # Shoutouts to n3rds.
    dTeamStandings = defaultdict(
        lambda: {'teamid': 0, 'wins': 0, 'losses': 0, 'rounddiff': 0})
    # Build our own object with team and links, rank, and round diff?
    # Building our own object requires matches, map_stats for each match.
    # Just build a dictionary with each match and stats?
    for match in totalMatches:
        map_stats = MapStats.query.filter(
            MapStats.match_id==match.id, MapStats.winner != None)
        # Get the losing team, and scores for round difference.
        for all_stats in map_stats:
            winningRounds = 0
            losingRounds = 0
            # Get each winner ID and create a list that returns the Team Name,
            # amount of wins for now.
            winningTeam = Team.query.filter_by(id=all_stats.winner).first()
            if all_stats.winner == match.team1_id:
                losingTeam = Team.query.filter_by(id=match.team2_id).first()
                winningRounds = winningRounds + all_stats.team1_score
                losingRounds = losingRounds + all_stats.team2_score
            else:
                losingTeam = Team.query.filter_by(id=match.team1_id).first()
                losingRounds = losingRounds + all_stats.team1_score
                winningRounds = winningRounds + all_stats.team2_score

            # Update winning and losing teams.
            dTeamStandings[winningTeam.name]['teamid'] = winningTeam.id
            dTeamStandings[winningTeam.name]['wins'] += 1
            dTeamStandings[winningTeam.name][
                'rounddiff'] += (winningRounds - losingRounds)
            dTeamStandings[losingTeam.name]['teamid'] = losingTeam.id
            dTeamStandings[losingTeam.name]['losses'] += 1
            dTeamStandings[losingTeam.name][
                'rounddiff'] += (losingRounds - winningRounds)

    # Sort teams via lexigraphical sort, very inefficient but it works for now.
    dTeamStandings = OrderedDict(
        sorted(dTeamStandings.items(), key=lambda x: (x[1].get('wins'), x[1].get('losses'), x[1].get('rounddiff')), reverse=True))
    # app.logger.info('Currently in dTeamStandings: \n{}'.format(dTeamStandings))
    if seasonsBoard:
        return render_template('leaderboard.html', standings=dTeamStandings, user=g.user, seasonsBoard=seasonsBoard, seasonName=season.name)
    else:
        return render_template('leaderboard.html', standings=dTeamStandings, user=g.user, seasonsBoard=seasonsBoard)


def getPlayerLeaderboard(seasonid=None):
    dctPlayer = {'steamid': '', 'steamurl': '', 'name': '', 'kills': 0, 'deaths': 0, 'kdr': 0.0, 'assists': 0, 'adr': 0.0,
                 '3k': 0, '4k': 0, '5k': 0, '1v1': 0, '1v2': 0, '1v3': 0, '1v4': 0, '1v5': 0, 'rating': 0.0, 'hsp': 0.0, 'trp': 0, 'fba': 0}
    lstAllPlayerDict = []
    playerValues = PlayerStats.query.all()
    matchQuery = Match.query.filter(
        Match.season_id == seasonid,
        Match.cancelled == False).with_entities(Match.id)
    res = [int(r[0]) for r in matchQuery]
    # Filter through every steam ID
    for player in playerValues:
        if any(d.get('steamid', None) == player.get_steam_id() for d in lstAllPlayerDict):
            continue
        if seasonid is not None:
            totalStats = PlayerStats.query.filter(
                PlayerStats.steam_id == player.get_steam_id()).filter(PlayerStats.match_id.in_(res))
            # Odd result set sometimes returning 0?
            if totalStats.count() < 1:
                continue
        else:
            totalStats = PlayerStats.query.filter_by(
                steam_id=player.get_steam_id())
        dctPlayer['steamid'] = (player.get_steam_id())
        dctPlayer['steamurl'] = (player.get_steam_url())
        dctPlayer['name'] = (player.get_player_name())
        dctPlayer['kills'] = (sum(c.kills for c in totalStats))
        dctPlayer['deaths'] = (sum(c.deaths for c in totalStats))
        dctPlayer['kdr'] = (mean(c.get_kdr() for c in totalStats))
        dctPlayer['assists'] = (sum(c.assists for c in totalStats))
        dctPlayer['adr'] = (mean(c.get_adr() for c in totalStats))
        dctPlayer['3k'] = (sum(c.k3 for c in totalStats))
        dctPlayer['4k'] = (sum(c.k4 for c in totalStats))
        dctPlayer['5k'] = (sum(c.k5 for c in totalStats))
        dctPlayer['1v1'] = (sum(c.v1 for c in totalStats))
        dctPlayer['1v2'] = (sum(c.v2 for c in totalStats))
        dctPlayer['1v3'] = (sum(c.v3 for c in totalStats))
        dctPlayer['1v4'] = (sum(c.v4 for c in totalStats))
        dctPlayer['1v5'] = (sum(c.v5 for c in totalStats))
        dctPlayer['rating'] = (mean(c.get_rating() for c in totalStats))
        dctPlayer['hsp'] = (mean(c.get_hsp() for c in totalStats))
        dctPlayer['trp'] = (sum(c.roundsplayed for c in totalStats))
        dctPlayer['fba'] = (sum(c.flashbang_assists for c in totalStats))
        lstAllPlayerDict.append(dctPlayer)
        dctPlayer = {}
    return lstAllPlayerDict

leaderboard_blueprint = Blueprint('leaderboard', __name__)


@leaderboard_blueprint.route('/leaderboard')
def leaderboard():
    return getLeaderboard()


@leaderboard_blueprint.route('/leaderboard/season/<int:seasonid>')
def seasonal_leaderboard(seasonid):
    return getLeaderboard(seasonid)


@leaderboard_blueprint.route('/leaderboard/season/<int:seasonid>/players')
def seasonal_player_leaderboard(seasonid):
    season = Season.query.get_or_404(seasonid)
    playerValues = getPlayerLeaderboard(seasonid)
    return render_template('statleaderboard.html', user=g.user, board=playerValues, season=season.name)


@leaderboard_blueprint.route('/leaderboard/players')
def player_leaderboard():
    playerValues = getPlayerLeaderboard()
    return render_template('statleaderboard.html', user=g.user, board=playerValues)
