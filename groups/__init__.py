# from flask_jwt import JWT, jwt_required, current_identity
from werkzeug.security import safe_str_cmp
from functools import wraps


import os
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from . import db

from .shared.middleware.jwt import check_jwt
from .shared.configs.serviceConsts import SECRET
from .shared.utils import jwt

JWT_SECRET = SECRET

# http://flask.pocoo.org/docs/1.0/tutorial/database/
def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY=JWT_SECRET,
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, '../../instance/records.sqlite'),
    )
    # app.debug = True
    # app.config['SECRET_KEY'] = 'super-secret'
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.update(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # register the database commands
    db.init_app(app)
    # Cors stuff
    cors = CORS(app, origins='*',
                headers=['Content-Type', 'Authorization'],
                expose_headers=['Content-Type', 'Authorization'])

    @app.route('/groups', methods=['POST'])
    @check_jwt(app.config['SECRET_KEY'])
    def create_group(jwt_body):
        req_data = request.get_json()

        try:
            ## @todo add an http level encryption thing so that password can be transmitted safely.
            groupName = req_data['groupName']  # string
        except KeyError:
            return jsonify({'error_detail': 'Missing required field'}), 400

        try:
            cursor = db.get_db().cursor()

            cursor.execute(
                'INSERT INTO recordSetPermissionGroups (name) '
                'Values(?)',
                ## @todo add salt encryption here.
                (groupName,)
            )
            id = cursor.lastrowid
            cursor.close()
            db.get_db().commit()
        except Exception as e:
            return jsonify({'error_detail': str(e)}), 400

        data = {'ID': groupName}
        return jsonify(data), 200

    @app.route('/groups/<string:groupName>', methods=['DELETE'])
    @check_jwt(app.config['SECRET_KEY'])
    def delete_group(jwt_body, groupName):
        try:
            cursor = db.get_db().cursor()

            result = cursor.execute(
                'DELETE from recordSetPermissionGroups '
                'WHERE name = ?',
                (groupName,)
            )
            db.get_db().commit()
            cursor.close()
        except Exception as e:
            return jsonify({'error_detail': str(e)}), 400

        if result.rowcount == 0:
            return jsonify({'error_detail': 'Failed to delete point.'}), 404

        return jsonify({}), 200

    @app.route('/groups/<string:groupName>/users', methods=['POST'])
    @check_jwt(app.config['SECRET_KEY'])
    def add_user_to_group(jwt_body, groupName):
        req_data = request.get_json()

        try:
            userID = req_data['userID']  # string
        except KeyError:
            return jsonify({'error_detail': 'Missing required field'}), 400

        try:
            cursor = db.get_db().cursor()

            result = cursor.execute(
                'INSERT INTO recordSetPermissionGroups (name, userID) '
                'Values(?, ?)',
                (groupName, userID,)
            )
            cursor.close()
            db.get_db().commit()
        except Exception as e:
            return jsonify({'error_detail': str(e)}), 400

        if result.rowcount == 0:
            return jsonify({'error_detail': 'Failed to add user to group.'}), 504

        return jsonify({}), 200

    @app.route('/groups/<string:groupName>/users/<int:userID>', methods=['DELETE'])
    @check_jwt(app.config['SECRET_KEY'])
    def remove_user_from_group(jwt_body, groupName, userID):
        try:
            cursor = db.get_db().cursor()

            result = cursor.execute(
                'DELETE from recordSetPermissionGroups '
                'WHERE name = ? AND userID = ?',
                (groupName, userID,)
            )
            db.get_db().commit()
            cursor.close()
        except Exception as e:
            return jsonify({'error_detail': str(e)}), 400

        if result.rowcount == 0:
            return jsonify({'error_detail': 'Failed to remove user from group.'}), 404

        return jsonify({}), 200

    ## I've been playing around with the idea of fitting all data for UI within a single api endpoint.
    ## Any option lists or anything like that...
    @app.route('/UI-conf/groups', methods=['GET'])
    @check_jwt(app.config['SECRET_KEY'])
    def get_ui_config(jwt_body):
        ## grab group stuff
        try:
            cursor = db.get_db().cursor()

            result = cursor.execute(
                'SELECT name, userID FROM recordSetPermissionGroups'
            ).fetchall()
            cursor.close()
        except Exception as e:
            return jsonify({'error_detail': str(e)}), 400

        data = [dict(zip([key[0] for key in cursor.description], row)) for row in result]
        if len(data) == 0:
            return jsonify({'error_detail': 'No points found'}), 404

        formatted_groups = {}
        for d in data:
            if not d['name'] in formatted_groups:
                formatted_groups[d['name']] = []

            formatted_groups[d['name']].append(d['userID'])

        ## grab user stuff
        try:
            cursor = db.get_db().cursor()

            result = cursor.execute(
                'SELECT ID, username, rspg.name as groupName FROM users u '
                'join recordSetPermissionGroups rspg ON u.ID = rspg.userID'
            ).fetchall()
            cursor.close()
        except Exception as e:
            return jsonify({'error_detail': str(e)}), 400

        data = [dict(zip([key[0] for key in cursor.description], row)) for row in result]
        if len(data) == 0:
            return jsonify({'error_detail': 'No points found'}), 404

        formatted_users = {}
        formatted_user_group_associations = {}
        for d in data:
            formatted_users[d['ID']] = d['username']

            if not d['ID'] in formatted_user_group_associations:
                formatted_user_group_associations[d['ID']] = []

            formatted_user_group_associations[d['ID']].append(d['groupName'])




        return jsonify({'groups': formatted_groups, 'users': formatted_users, 'userGroupAssoc': formatted_user_group_associations}), 200

    return app

