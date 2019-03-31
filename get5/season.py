from flask import Blueprint, request, render_template, flash, g, redirect, jsonify, Markup, json

import steamid
import get5
from get5 import app, db, BadRequestError, config_setting
from models import User, Team, Match, GameServer, MapStats, TeamLeaderboard, Season
from collections import OrderedDict, defaultdict
from datetime import datetime
import util
import re
from copy import deepcopy


season_blueprint = Blueprint('season', __name__)


@season_blueprint.route('/seasons')
def seasons():
    page = util.as_int(request.values.get('page'), on_fail=1)
    seasons = Season.query.order_by(-Season.id).paginate(page, 20)
    return render_template('seasons.html', user=g.user, seasons=seasons,
                           page=page)
