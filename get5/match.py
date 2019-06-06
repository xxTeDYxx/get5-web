from flask import Blueprint, request, render_template, flash, g, redirect, jsonify, Markup, json

import steamid
import get5
from get5 import app, db, BadRequestError, config_setting
from models import User, Team, Match, GameServer, Season, Veto, match_audit
from collections import OrderedDict
from datetime import datetime
import util
import re
from copy import deepcopy

from wtforms import (
    Form, widgets, validators,
    StringField, RadioField,
    SelectField, ValidationError, SelectMultipleField)

match_blueprint = Blueprint('match', __name__)
dbKey = app.config['DATABASE_KEY']

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


def different_teams_validator(form, field):
    if form.team1_id.data == form.team2_id.data:
        raise ValidationError('Teams cannot be equal')


def mappool_validator(form, field):
    if 'preset' in form.series_type.data and len(form.veto_mappool.data) != 1:
        raise ValidationError(
            'You must have exactly 1 map selected to do a bo1 with a preset map')

    max_maps = 1
    try:
        max_maps = int(form.series_type.data[2])
    except ValueError:
        max_maps = 1

    if len(form.veto_mappool.data) < max_maps:
        raise ValidationError(
            'You must have at least {} maps selected to do a Bo{}'.format(max_maps, max_maps))


class MatchForm(Form):
    server_id = SelectField('Server', coerce=int,
                            validators=[validators.required()])

    match_title = StringField('Match title text',
                              default='Map {MAPNUMBER} of {MAXMAPS}',
                              validators=[validators.Length(min=-1, max=Match.title.type.length)])

    series_type = RadioField('Series type',
                             validators=[validators.required()],
                             default='bo1',
                             choices=[
                                 ('bo1-preset', 'Bo1 with preset map'),
                                 ('bo1', 'Bo1 with map vetoes'),
                                 ('bo2', 'Bo2 with map vetoes'),
                                 ('bo3', 'Bo3 with map vetoes'),
                                 ('bo5', 'Bo5 with map vetoes'),
                                 ('bo7', 'Bo7 with map vetoes'),
                             ])
    side_type = RadioField('Side type',
                             validators=[validators.required()],
                             default='standard',
                             choices=[
                                ('standard', 'Standard: Team that doesn\'t pick map gets side choice'),
                                ('never_knife', 'Never Knife: Team 1 is CT and Team 2 is T.'),
                                ('always_knife', 'Always Knife: Always have knife round.'),
                             ])
    team1_id = SelectField('Team 1', coerce=int,
                           validators=[validators.required()])

    team1_string = StringField('Team 1 title text',
                               default='',
                               validators=[validators.Length(min=-1,
                                                             max=Match.team1_string.type.length)])

    team2_id = SelectField('Team 2', coerce=int,
                           validators=[validators.required(), different_teams_validator])

    team2_string = StringField('Team 2 title text',
                               default='',
                               validators=[validators.Length(min=-1,
                                                             max=Match.team2_string.type.length)])

    mapchoices = config_setting('MAPLIST')
    default_mapchoices = config_setting('DEFAULT_MAPLIST')
    veto_mappool = MultiCheckboxField('Map pool',
                                      choices=map(lambda name: (
                                          name, util.format_mapname(
                                              name)), mapchoices),
                                      default=default_mapchoices,
                                      validators=[mappool_validator],
                                      )
    veto_first = RadioField('Veto',
                             default='CT',
                             choices=[
                                 ('CT', 'CT gets first veto'),
                                 ('T', 'T get first veto'),
                             ])

    season_selection = SelectField('Season', coerce=int,
                                   validators=[validators.optional()])

    def add_teams(self, user):
        if self.team1_id.choices is None:
            self.team1_id.choices = []

        if self.team2_id.choices is None:
            self.team2_id.choices = []

        team_ids = [team.id for team in user.teams]
        for team in Team.query.filter_by(public_team=True):
            if team.id not in team_ids:
                team_ids.append(team.id)

        team_tuples = []
        for teamid in team_ids:
            team_tuples.append((teamid, Team.query.get(teamid).name))

        self.team1_id.choices += team_tuples
        self.team2_id.choices += team_tuples

    def add_servers(self, user):
        if self.server_id.choices is None:
            self.server_id.choices = []

        server_ids = []
        for s in user.servers:
            if not s.in_use:
                server_ids.append(s.id)

        for s in GameServer.query.filter_by(public_server=True):
            if not s.in_use and s.id not in server_ids:
                server_ids.append(s.id)

        server_tuples = []
        for server_id in server_ids:
            server_tuples.append(
                (server_id, GameServer.query.get(server_id).get_display()))

        self.server_id.choices += server_tuples

    def add_seasons(self):
        if self.season_selection.choices is None:
            self.season_selection.choices = []
        season_tuples = []
        season_tuples.append((0, 'No Season'))
        for seasons in Season.query.filter(Season.end_date >= datetime.now()).order_by(-Season.id):
            season_tuples.append((seasons.id, seasons.name))
        self.season_selection.choices += season_tuples


@match_blueprint.route('/match/create', methods=['GET', 'POST'])
def match_create():
    if not g.user:
        return redirect('/login')

    form = MatchForm(request.form)
    form.add_teams(g.user)
    form.add_servers(g.user)
    form.add_seasons()

    if request.method == 'POST':
        num_matches = g.user.matches.count()
        max_matches = config_setting('USER_MAX_MATCHES')
        season_id = None

        if max_matches >= 0 and num_matches >= max_matches and not g.user.admin:
            flash('You already have the maximum number of matches ({}) created'.format(
                num_matches))

        elif form.validate():
            mock = config_setting('TESTING')

            server = GameServer.query.get_or_404(form.data['server_id'])

            match_on_server = g.user.matches.filter_by(
                server_id=server.id, end_time=None, cancelled=False).first()

            server_available = False
            json_reply = None

            if g.user.id != server.user_id and not server.public_server:
                server_available = False
                message = 'This is not your server!'
            elif match_on_server is not None:
                server_available = False
                message = 'Match {} is already using this server'.format(
                    match_on_server.id)
            elif mock:
                server_available = True
                message = 'Success'
            else:
                json_reply, message = util.check_server_avaliability(
                    server,dbKey)
                server_available = (json_reply is not None)

            if server_available:
                skip_veto = 'preset' in form.data['series_type']
                try:
                    max_maps = int(form.data['series_type'][2])
                except ValueError:
                    max_maps = 1

                if form.data['season_selection'] != 0:
                    season_id = form.data['season_selection']

                match = Match.create(
                    g.user, form.data['team1_id'], form.data['team2_id'],
                    form.data['team1_string'], form.data['team2_string'],
                    max_maps, skip_veto,
                    form.data['match_title'], form.data['veto_mappool'], season_id, 
                    form.data['side_type'], form.data['veto_first'], 
                    form.data['server_id'])

                # Save plugin version data if we have it
                if json_reply and 'plugin_version' in json_reply:
                    match.plugin_version = json_reply['plugin_version']
                else:
                    match.plugin_version = 'unknown'
                # ADD FORM DATA FOR EXTRA GOODIES HERE LIKE CLAN TAG ETC.
                # Essentially stuff that doesn't need to be stored in DB.
                # Force Get5 to auth on official matches. Don't raise errors
                # if we cannot do this.
                if server_available and not mock:
                    server.send_rcon_command('get5_check_auths 1', num_retries=2, timeout=0.75)

                server.in_use = True

                db.session.commit()
                app.logger.info('User {} created match {}, assigned to server {}'
                                .format(g.user.id, match.id, server.id))

                if mock or match.send_to_server():
                    return redirect('/mymatches')
                else:
                    flash('Failed to load match configs on server')
            else:
                flash(message)

        else:
            get5.flash_errors(form)

    return render_template(
        'match_create.html', form=form, user=g.user, teams=g.user.teams,
        match_text_option=config_setting('CREATE_MATCH_TITLE_TEXT'))


@match_blueprint.route('/match/<int:matchid>')
def match(matchid):
    match = Match.query.get_or_404(matchid)
    vetoes = Veto.query.filter_by(match_id=matchid)
    if match.server_id:
        server = GameServer.query.get_or_404(match.server_id)
    else:
        server = None
    team1 = Team.query.get_or_404(match.team1_id)
    team2 = Team.query.get_or_404(match.team2_id)
    map_stat_list = match.map_stats.all()
    completed = match.winner
    try:
        if server is not None and completed is None:
            password = server.receive_rcon_value('sv_password')
            connect_string = str("steam://connect/") + str(server.ip_string) + str(":") + \
                str(server.port) + str("/") + str(password)
            gotv_port = server.receive_rcon_value('tv_port')
            gotv_string = str("steam://connect/") + str(server.ip_string) + str(":") + \
                str(gotv_port)
        else:
            connect_string = None
            gotv_string = None
    except util.RconError as e:
        connect_string = None
        gotv_string = None
        app.logger.info('Attempted to connect to server {}, but it is offline'
                        .format(server.ip_string))

    is_owner = False
    has_admin_access = False
    if g.user:
        is_owner = (g.user.id == match.user_id)
        has_admin_access = is_owner or (config_setting(
            'ADMINS_ACCESS_ALL_MATCHES') and g.user.admin)
    return render_template(
        'match.html', user=g.user, admin_access=has_admin_access,
        match=match, team1=team1, team2=team2,
        map_stat_list=map_stat_list, completed=completed, connect_string=connect_string,
        gotv_string=gotv_string, vetoes=vetoes)


@match_blueprint.route('/match/<int:matchid>/scoreboard')
def match_scoreboard(matchid):
    def merge(a, b):
        if isinstance(b, dict) and isinstance(a, dict):
            a_and_b = a.viewkeys() & b.viewkeys()
            every_key = a.viewkeys() | b.viewkeys()
            return {k: merge(a[k], b[k]) if k in a_and_b else
                    deepcopy(a[k] if k in a else b[k]) for k in every_key}
        return deepcopy(b)

    match = Match.query.get_or_404(matchid)
    team1 = Team.query.get_or_404(match.team1_id)
    team2 = Team.query.get_or_404(match.team2_id)
    map_num = 0
    map_stat_list = match.map_stats.all()
    player_dict = {}
    matches = OrderedDict()
    match_num = 0
    sorted_player_dict = OrderedDict()
    app.logger.info('{}'.format(map_stat_list))
    for map_stats in map_stat_list:
        for player in map_stats.player_stats:
            player_dict = merge(player_dict, player.get_ind_scoreboard(map_stats.map_number))
        # Sort teams based on kills.
        sorted_player_dict[team1.name] = OrderedDict(
            sorted(player_dict[team1.name].items(), key=lambda x: x[1].get('kills'), reverse=True))
        sorted_player_dict[team2.name] = OrderedDict(
            sorted(player_dict[team2.name].items(), key=lambda x: x[1].get('kills'), reverse=True))
        
        t1score = map_stats.team1_score
        t2score = map_stats.team2_score
        curMap = map_stats.map_name
        sorted_player_dict[team1.name]['TeamName'] = team1.name
        sorted_player_dict[team2.name]['TeamName'] = team2.name
        sorted_player_dict[team1.name]['TeamScore'] = t1score
        sorted_player_dict[team2.name]['TeamScore'] = t2score
        sorted_player_dict['map'] = curMap
        matches['map_'+str(match_num)]=sorted_player_dict
        match_num+=1
        sorted_player_dict = OrderedDict()
        player_dict = {}

    response = app.response_class(
        json.dumps(matches, sort_keys=False),
        mimetype='application/json')
    return response


@match_blueprint.route('/match/<int:matchid>/config')
def match_config(matchid):
    match = Match.query.get_or_404(matchid)
    dict = match.build_match_dict()
    json_text = jsonify(dict)
    return json_text


def admintools_check(user, match):
    if user is None:
        raise BadRequestError('You do not have access to this page')

    grant_admin_access = user.admin and get5.config_setting(
        'ADMINS_ACCESS_ALL_MATCHES')
    if user.id != match.user_id and not grant_admin_access:
        raise BadRequestError('You do not have access to this page')

    if match.finished():
        raise BadRequestError('Match already finished')

    if match.cancelled:
        raise BadRequestError('Match is cancelled')


@match_blueprint.route('/match/<int:matchid>/cancel')
def match_cancel(matchid):
    app.logger.info("Match server id is: {}".format(matchid))
    match = Match.query.get_or_404(matchid)
    admintools_check(g.user, match)
    
    match.cancelled = True
    server = GameServer.query.get(match.server_id)
    if server:
        server.in_use = False

    db.session.commit()

    try:
        server.send_rcon_command('get5_endmatch', raise_errors=True)
    except util.RconError as e:
        flash('Failed to cancel match: ' + str(e))

    return redirect('/mymatches')


@match_blueprint.route('/match/<int:matchid>/rcon')
def match_rcon(matchid):
    match = Match.query.get_or_404(matchid)
    admintools_check(g.user, match)

    command = request.values.get('command')
    server = GameServer.query.get_or_404(match.server_id)

    if command:
        try:
            rcon_response = server.send_rcon_command(
                command, raise_errors=True)
            if rcon_response:
                rcon_response = Markup(rcon_response.replace('\n', '<br>'))
            else:
                rcon_response = 'No output'
            flash(rcon_response)
            # Store the command.
            match_audit.create(g.user.id, matchid, datetime.now(), command)
            db.session.commit()
        except util.RconError as e:
            print(e)
            flash('Failed to send command: ' + str(e))

    return redirect('/match/{}'.format(matchid))


@match_blueprint.route('/match/<int:matchid>/pause')
def match_pause(matchid):
    match = Match.query.get_or_404(matchid)
    admintools_check(g.user, match)
    server = GameServer.query.get_or_404(match.server_id)

    try:
        server.send_rcon_command('sm_pause', raise_errors=True)
        flash('Paused match')
    except util.RconError as e:
        flash('Failed to send pause command: ' + str(e))

    return redirect('/match/{}'.format(matchid))


@match_blueprint.route('/match/<int:matchid>/unpause')
def match_unpause(matchid):
    match = Match.query.get_or_404(matchid)
    admintools_check(g.user, match)
    server = GameServer.query.get_or_404(match.server_id)

    try:
        server.send_rcon_command('sm_unpause', raise_errors=True)
        flash('Unpaused match')
    except util.RconError as e:
        flash('Failed to send unpause command: ' + str(e))

    return redirect('/match/{}'.format(matchid))


@match_blueprint.route('/match/<int:matchid>/adduser')
def match_adduser(matchid):
    match = Match.query.get_or_404(matchid)
    admintools_check(g.user, match)
    server = GameServer.query.get_or_404(match.server_id)
    team = request.values.get('team')
    if not team:
        raise BadRequestError('No team specified')

    auth = request.values.get('auth')
    suc, new_auth = steamid.auth_to_steam64(auth)
    if suc:
        try:
            command = 'get5_addplayer {} {}'.format(new_auth, team)
            response = server.send_rcon_command(command, raise_errors=True)
            match_audit.create(g.user.id, matchid, datetime.now(), command)
            db.session.commit()
            flash(response)
        except util.RconError as e:
            flash('Failed to send command: ' + str(e))

    else:
        flash('Invalid steamid: {}'.format(auth))

    return redirect('/match/{}'.format(matchid))

@match_blueprint.route('/match/<int:matchid>/backup', methods=['GET'])
def match_backup(matchid):
    match = Match.query.get_or_404(matchid)
    admintools_check(g.user, match)
    server = GameServer.query.get_or_404(match.server_id)
    file = request.values.get('file')

    if not file:
        # List backup files
        backup_response = server.send_rcon_command(
            'get5_listbackups ' + str(matchid))
        if backup_response:
            backup_files = sorted(backup_response.split('\n'))
        else:
            backup_files = []

        return render_template('match_backup.html', user=g.user,
                               match=match, backup_files=backup_files)

    else:
        # Restore the backup file
        command = 'get5_loadbackup {}'.format(file)
        response = server.send_rcon_command(command)
        # Make sure auths get enabled, silently.
        try:
            server.send_rcon_command('get5_check_auths 1')
        except:
            pass
          
        if response:
            flash('Restored backup file {}'.format(file))
        else:
            flash('Failed to restore backup file {}'.format(file))
            return redirect('match/{}/backup'.format(matchid))

        return redirect('match/{}'.format(matchid))


@match_blueprint.route("/matches")
def matches():
    page = util.as_int(request.values.get('page'), on_fail=1)
    matches = Match.query.order_by(-Match.id).filter_by(
        cancelled=False).paginate(page, 20)
    return render_template('matches.html', user=g.user, matches=matches,
                           my_matches=False, all_matches=True, page=page)


@match_blueprint.route("/matches/<int:userid>")
def matches_user(userid):
    user = User.query.get_or_404(userid)
    page = util.as_int(request.values.get('page'), on_fail=1)
    matches = user.matches.order_by(-Match.id).paginate(page, 20)
    is_owner = (g.user is not None) and (userid == g.user.id)
    return render_template('matches.html', user=g.user, matches=matches,
                           my_matches=is_owner, all_matches=False, match_owner=user, page=page)


@match_blueprint.route("/mymatches")
def mymatches():
    if not g.user:
        return redirect('/login')

    return redirect('/matches/' + str(g.user.id))
