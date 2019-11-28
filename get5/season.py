from flask import Blueprint, request, render_template, flash, g, redirect

import get5
from get5 import app, db, BadRequestError, config_setting
from models import Season, User, Match
from datetime import datetime
import util

from wtforms import (
    Form, widgets, validators,
    StringField, DateField,
    ValidationError)


def start_greater_than_end_validator(form, field):
    # We are allowed to have null end dates, as a continuing season.
    if (form.start_date.data and form.end_date.data) and form.end_date.data <= form.start_date.data:
        raise ValidationError('End date must be greater than start date.')


def name_validator(form, field):
    if form.season_title.data == '' or form.season_title.data == None:
        raise ValidationError('Title must not be null.')


class SeasonForm(Form):
    season_title = StringField('Season Name',
                               default='',
                               validators=[validators.Length(min=5, max=Season.name.type.length)])

    start_date = DateField('Start Date', format='%m/%d/%Y',
                           default=datetime.today(),
                           validators=[validators.required(), start_greater_than_end_validator])

    end_date = DateField('End Date', format='%m/%d/%Y',
                         default=datetime.today(),
                         validators=[validators.optional()])


season_blueprint = Blueprint('season', __name__)


@season_blueprint.route('/seasons')
def seasons():
    seasons = Season.query.order_by(-Season.id)
    seasoned_matches = Match.query.filter(Match.season_id.isnot(None), Match.cancelled==False)
    return render_template('seasons.html', user=g.user, seasons=seasons,
                           my_seasons=False, matches=seasoned_matches, all_seasons=True)


@season_blueprint.route('/season/create', methods=['GET', 'POST'])
def season_create():
    if not g.user:
        return redirect('/login')

    form = SeasonForm(request.form)

    if request.method == 'POST':
        num_seasons = g.user.seasons.count()
        max_seasons = config_setting('USER_MAX_SEASONS')
        if max_seasons >= 0 and num_seasons >= max_seasons and not (g.user.admin or g.user.super_admin):
            flash('You already have the maximum number of seasons ({}) created'.format(
                num_seasons))

        elif form.validate():
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


@season_blueprint.route("/season/<int:seasonid>")
def season_matches(seasonid):
    season_info = Season.query.get_or_404(seasonid)
    matches = Match.query.order_by(-Match.id).filter_by(season_id=seasonid,
                                                        cancelled=False)
    return render_template('matches.html', user=g.user, matches=matches,
                           season_matches=True, all_matches=False,
                           season=season_info)


@season_blueprint.route("/season/user/<int:userid>")
def seasons_user(userid):
    user = User.query.get_or_404(userid)
    seasons = user.seasons.order_by(-Season.id)
    seasoned_matches = Match.query.filter(Match.season_id.isnot(None), Match.cancelled==False)
    is_owner = (g.user is not None) and (userid == g.user.id)
    return render_template('seasons.html', user=g.user, seasons=seasons,
                           my_seasons=is_owner, all_matches=False, matches=seasoned_matches,
                           season_owner=user)


@season_blueprint.route('/season/<int:seasonid>/edit', methods=['GET', 'POST'])
def season_edit(seasonid):
    season = Season.query.get_or_404(seasonid)
    if not season.can_edit(g.user):
        return 'Not your season', 400

    form = SeasonForm(
        request.form,
        user_id=season.user_id,
        season_title=season.name,
        start_date=season.start_date,
        end_date=season.end_date)

    if request.method == 'GET':
        return render_template('season_create.html', user=g.user, form=form,
                               edit=True)

    elif request.method == 'POST':
        if form.validate():
            data = form.data
            season.set_data(g.user, data['season_title'], data['start_date'],
                            data['end_date'])
            db.session.commit()
            return redirect('/season/{}'.format(season.id))
        else:
            flash_errors(form)

    return render_template(
        'season_create.html', user=g.user, form=form, edit=True)


@season_blueprint.route('/season/<int:seasonid>/delete')
def season_delete(seasonid):
    season = Season.query.get_or_404(seasonid)
    if not season.can_delete(g.user):
        return 'Cannot delete this team', 400

    if Season.query.filter_by(id=season.id).delete():
        db.session.commit()

    return redirect('/myseasons')


@season_blueprint.route("/myseasons")
def myseasons():
    if not g.user:
        return redirect('/login')

    return redirect('/season/user/' + str(g.user.id))
