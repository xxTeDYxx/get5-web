from get5 import app, db, flash_errors, config_setting, BadRequestError
from models import GameServer
import util

from flask import Blueprint, request, render_template, flash, g, redirect

from wtforms import Form, validators, StringField, IntegerField, BooleanField


server_blueprint = Blueprint('server', __name__)
dbKey = app.config['DATABASE_KEY']


class ServerForm(Form):
    display_name = StringField('Display Name',
                               validators=[
                                   validators.Length(min=-1,
                                                     max=GameServer.display_name.type.length)])

    ip_string = StringField('Server IP',
                            validators=[
                                validators.required(),
                                validators.IPAddress()])

    port = IntegerField('Server port', default=27015,
                        validators=[validators.required()])

    rcon_password = StringField('RCON password',
                                validators=[
                                    validators.required(),
                                    validators.Length(min=-1,
                                                      max=GameServer.rcon_password.type.length)])

    public_server = BooleanField('Publicly usable server')


@server_blueprint.route('/server/create', methods=['GET', 'POST'])
def server_create():
    if not g.user:
        return redirect('/login')

    form = ServerForm(request.form)
    if request.method == 'POST':
        num_servers = g.user.servers.count()
        max_servers = config_setting('USER_MAX_SERVERS')
        if max_servers >= 0 and num_servers >= max_servers and not (util.is_admin(g.user) or util.is_super_admin(g.user)):
            flash('You already have the maximum number of servers ({}) stored'.format(
                num_servers))

        elif form.validate():
            mock = config_setting('TESTING')
            data = form.data
            if not mock:
                encRcon = util.encrypt(dbKey, str(data['rcon_password']))
            else:
                encRcon = data['rcon_password']

            server = GameServer.create(g.user,
                                       data['display_name'],
                                       data['ip_string'], data['port'],
                                       encRcon,
                                       data['public_server'] and util.is_admin(g.user))

            if mock or util.check_server_connection(server, dbKey):
                db.session.commit()
                app.logger.info(
                    'User {} created server {}'.format(g.user.id, server.id))
                return redirect('/myservers')
            else:
                db.session.remove()
                flash('Failed to connect to server')

        else:
            flash_errors(form)

    return render_template('server_create.html', user=g.user, form=form,
                           edit=False, is_admin=util.is_admin(g.user))


@server_blueprint.route('/server/<int:serverid>/edit', methods=['GET', 'POST'])
def server_edit(serverid):
    server = GameServer.query.get_or_404(serverid)
    is_owner = (g.user and (util.is_server_owner(g.user, server)))
    is_sadmin = (g.user and util.is_super_admin(g.user))
    app.logger.info("Owner: {} Sadmin: {}".format(is_owner, is_sadmin))
    if not is_owner:
        if not is_sadmin:
            raise BadRequestError('You do not have access to this server.')

    # Attempt encryption/decryption
    rconDecrypt = util.decrypt(dbKey, server.rcon_password)
    form = ServerForm(request.form,
                      display_name=server.display_name,
                      ip_string=server.ip_string,
                      port=server.port,
                      rcon_password=server.rcon_password if rconDecrypt is None else rconDecrypt,
                      public_server=server.public_server)

    if request.method == 'POST':
        if form.validate():
            mock = app.config['TESTING']
            data = form.data
            if not mock:
                encRcon = util.encrypt(dbKey, str(data['rcon_password']))
            else:
                encRcon = data['rcon_password']
            server.display_name = data['display_name']
            server.ip_string = data['ip_string']
            server.port = data['port']
            server.rcon_password = encRcon
            server.public_server = (data['public_server'] and (util.is_admin(g.user) or util.is_super_admin(g.user)))

            if mock or util.check_server_connection(server, dbKey):
                db.session.commit()
                return redirect('/myservers')
            else:
                db.session.remove()
                flash('Failed to connect to server')

        else:
            flash_errors(form)

    return render_template('server_create.html', user=g.user, form=form,
                           edit=True, is_admin=util.is_admin(g.user), is_sadmin=util.is_super_admin(g.user))


@server_blueprint.route('/server/<int:serverid>/delete', methods=['GET'])
def server_delete(serverid):
    server = GameServer.query.get_or_404(serverid)
    is_owner = g.user and (g.user.id == server.user_id)
    is_sadmin = g.user and util.is_super_admin(g.user)
    if not is_owner:
        if not is_sadmin:
            raise BadRequestError('You do not have access to this server.')

    if server.in_use:
        raise BadRequestError('Cannot delete server when in use.')

    matches = g.user.matches.filter_by(server_id=serverid)
    for m in matches:
        m.server_id = None

    GameServer.query.filter_by(id=serverid).delete()
    db.session.commit()
    return redirect('/myservers')


@server_blueprint.route("/myservers")
def myservers():
    if not g.user:
        return redirect('/login')

    servers = GameServer.query.filter_by(
        user_id=g.user.id).order_by(-GameServer.id).limit(50)
    if util.is_super_admin(g.user):
        servers = GameServer.query.order_by(-GameServer.id)

    return render_template('servers.html', user=g.user, servers=servers)
