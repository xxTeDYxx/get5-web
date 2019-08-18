from flask import Blueprint, render_template, redirect, abort, g
from models import PlayerStats
from statistics import mean


stats_blueprint = Blueprint('stats', __name__)


# For each users steam ID in a match, get their kills, deaths, etc.
# and output a table with all their stats.
@stats_blueprint.route('/stats/<int:steamid>')
def get_user_stats(steamid):
    all_stats = PlayerStats.query.filter_by(steam_id=steamid)
    if all_stats.count() == 0:
        abort(404)
    steam_url = all_stats.first().get_steam_url()
    kills = sum(c.kills for c in all_stats)
    deaths = sum(c.deaths for c in all_stats)
    kdr = mean(c.get_kdr() for c in all_stats)
    assists = sum(c.assists for c in all_stats)
    adr = mean(c.get_adr() for c in all_stats)
    k3 = sum(c.k3 for c in all_stats)
    k4 = sum(c.k4 for c in all_stats)
    k5 = sum(c.k5 for c in all_stats)
    v1 = sum(c.v1 for c in all_stats)
    v2 = sum(c.v2 for c in all_stats)
    v3 = sum(c.v3 for c in all_stats)
    v4 = sum(c.v4 for c in all_stats)
    v5 = sum(c.v5 for c in all_stats)
    hltvrating = mean(c.get_rating() for c in all_stats)
    hsp = mean(c.get_hsp() for c in all_stats)
    total_rounds = sum(c.roundsplayed for c in all_stats)
    flashbang_assists = sum(c.flashbang_assists for c in all_stats)

    name = all_stats.first().get_player_name()
    return render_template('stats.html', user_kills=kills, user_deaths=deaths,
                           user_kdr=kdr, user_assists=assists, user_adr=adr,
                           user_3k=k3, user_4k=k4, user_5k=k5,
                           user_1v1=v1, user_1v2=v2, user_1v3=v3,
                           user_1v4=v4, user_1v5=v5, user_rating=hltvrating,
                           user_headshot=hsp, user_totalrounds=total_rounds, user_fbAssists=flashbang_assists,
                           user_name=name, steam_url=steam_url, user=g.user)
