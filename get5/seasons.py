from flask import Blueprint, request, render_template, flash, g, redirect, jsonify, Markup, json

import steamid
import get5
from get5 import app, db, BadRequestError, config_setting
from models import User, Team, Match, GameServer, MapStats, TeamLeaderboard
from collections import OrderedDict, defaultdict
from datetime import datetime
import util
import re
from copy import deepcopy


seasons_blueprint = Blueprint('seasons', __name__)


@seasons_blueprint.route('/seasons')
def seasons():

    return render_template('seasons.html')
