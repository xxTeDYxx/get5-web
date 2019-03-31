from flask import Blueprint, request, render_template, flash, g, redirect, jsonify, Markup, json

import steamid
import get5
from get5 import app, db, BadRequestError, config_setting
from models import Season, User
from datetime import datetime
import util
import re

from wtforms import (
    Form, widgets, validators,
    StringField, DateField)


class SeasonForm(Form):
    season_title = StringField('Season Name',
                               default='NAME HERE',
                               validators=[validators.Length(min=-1, max=Season.name.type.length)])

    start_date = DateField('Start Date', format='%m/%d/%Y',
                           default=datetime.today(),
                           validators=[validators.required()])

    end_date = DateField('End Date', format='%m/%d/%Y',
                         default=datetime.date.today() + datetime.timedelta(days=1),
                         validators=[validators.required()])


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


@season_blueprint.route("/seasons/<int:userid>")
def matches_user(userid):
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

    return redirect('/seasons/' + str(g.user.id))
