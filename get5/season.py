from flask import Blueprint, request, render_template, flash, g, redirect, jsonify, Markup, json

import steamid
import get5
from get5 import app, db, BadRequestError, config_setting
from models import Season, User, Match
from datetime import datetime
import util
import re

from wtforms import (
    Form, widgets, validators,
    StringField, DateField,
    ValidationError)


def start_greater_than_end_validator(form, field):
    if form.end_date.data <= form.start_date.data:
        raise ValidationError('End date must be greater than start date.')


def name_validator(form, field):
    if form.season_title.data == '' or form.season_title.data == None:
        raise ValidationError('Title must not be null.')


class SeasonForm(Form):
    season_title = StringField('Season Name',
                               default='',
                               validators=[validators.Length(min=0, max=Season.name.type.length)])

    start_date = DateField('Start Date', format='%m/%d/%Y',
                           default=datetime.today(),
                           validators=[[validators.required()]])

    end_date = DateField('End Date', format='%m/%d/%Y',
                         default=datetime.today(),
                         validators=[start_greater_than_end_validator])


season_blueprint = Blueprint('season', __name__)


@season_blueprint.route('/seasons')
def seasons():
    page = util.as_int(request.values.get('page'), on_fail=1)
    seasons = Season.query.order_by(-Season.id).paginate(page, 20)
    return render_template('seasons.html', user=g.user, seasons=seasons,
                           my_seasons=False, all_seasons=True, page=page)


@season_blueprint.route('/season/create', methods=['GET', 'POST'])
def season_create():
    if not g.user:
        return redirect('/login')

    form = SeasonForm(request.form)

    if request.method == 'POST':
        if form.validate():
            mock = config_setting('TESTING')

            season = Season.create(
                g.user, form.data['season_title'],
                form.data['start_date'], form.data['end_date'])

            db.session.commit()
            app.logger.info('User {} created season {}'
                            .format(g.user.id, season.id))

            return redirect('/myseasons')

        else:
            get5.flash_errors(form)

    return render_template(
        'season_create.html', form=form, user=g.user)


@season_blueprint.route("/season/<int:userid>/<int:seasonid>")
def season_matches(userid, seasonid):
    user = User.query.get_or_404(userid)
    season_info = Season.query.get_or_404(seasonid)
    page = util.as_int(request.values.get('page'), on_fail=1)
    matches = user.matches.order_by(-Match.id).filter_by(season_id=seasonid,
                                                         cancelled=False).paginate(page, 20)

    return render_template('matches.html', user=g.user, matches=matches,
                           season_matches=True, all_matches=False, season_user=user,
                           page=page, season=season_info)


@season_blueprint.route("/season/<int:userid>")
def seasons_user(userid):
    user = User.query.get_or_404(userid)
    page = util.as_int(request.values.get('page'), on_fail=1)
    seasons = user.seasons.order_by(-Season.id).paginate(page, 20)
    is_owner = (g.user is not None) and (userid == g.user.id)
    app.logger.info('User is {}'.format(g.user))
    return render_template('seasons.html', user=g.user, seasons=seasons,
                           my_seasons=is_owner, all_matches=False, season_owner=user, page=page)


@season_blueprint.route("/myseasons")
def myseasons():
    if not g.user:
        return redirect('/login')

    return redirect('/season/' + str(g.user.id))
