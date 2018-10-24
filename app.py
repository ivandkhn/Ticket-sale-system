from flask import Flask, request, jsonify
from sqlalchemy import *
from sqlalchemy.exc import DataError
import re
import json_text_constants as j_const
import generate_test_db_data

app = Flask(__name__)

POSTGRES = {
    'user': 'postgres',
    'pw': '1234',
    'db': 'postgres',
    'host': 'localhost',
    'port': '5432',
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = create_engine(
    'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
    )


@app.route('/api/user/add', methods=['POST'])
def user_add():
    """
    sequence diagram # todo
    """
    content = dict(request.get_json())
    username, password, level = get_user_data(content)

    db.execute(
        "INSERT INTO Users "
        "(login, password, accessLevel) "
        "VALUES (\'%s\', \'%s\', %s);"
        % (username, password, level)
        )
    return 'ok'


@app.route('/api/user/modify', methods=['GET', 'POST'])
def user_modify():
    """
    sequence diagram # todo
    # todo check if the user is in the database
    """

    content = dict(request.get_json())
    username, password, level = get_user_data(content)
    data_to_change = content.get(j_const.change_data_type)

    if data_to_change == j_const.level:
        db.execute(
            f'UPDATE users SET accesslevel = {level} '
            f'WHERE login LIKE \'{username}\''
            )
        return 'ok'
    if data_to_change == j_const.password:
        db.execute(
            f'UPDATE users SET password = {password} '
            f'WHERE login LIKE \'{username}\''
            )
        return 'ok'
    if data_to_change == j_const.username:
        # todo username change
        pass
    return j_const.json_change_value_error % data_to_change


@app.route('/api/ticket/view/all', methods=['GET'])
def ticket_view_all():
    """
    sequence diagram # 8
    """
    result = db.execute(
        'SELECT * FROM tickets'
        )
    return jsonify({'result': [dict(row) for row in result]})


@app.route('/api/ticket/view', methods=['GET'])
def ticket_view_specific():
    """
    sequence diagram #8 (inherited)
    """
    if len(request.args) == 0:
        return ticket_view_all()

    # probably a good idea to iterate request.args.keys()
    # instead of j_const.all_properties

    sql_statement = 'SELECT * FROM tickets WHERE '
    multiple_parameters = False
    at_least_one_argument = False
    for json_key in j_const.all_properties:
        argument = request.args.get(json_key)
        if argument is not None:
            at_least_one_argument = True
            equal_operator = '=' if argument.isdigit() else 'LIKE'
            if multiple_parameters:
                sql_statement += ' AND '
            sql_statement += f'{json_key} {equal_operator} {argument}'
            multiple_parameters = True
    if at_least_one_argument:
        result = db.execute(sql_statement)
        return jsonify({'result': [dict(row) for row in result]})
    else:
        return 'no one correct json key found'


@app.route('/api/ticket/add', methods=['GET', 'POST'])
def ticket_add():
    """
    sequence diagram # 2
    """
    # todo use organizerID to fill place, orgName (i.e. multiple SQL query)
    i = dict(request.get_json())
    try:
        sql_statement = f'INSERT INTO tickets ' \
                        f'(OpenedForSelling, EventDate, EventTime, ' \
                        f'EventPlace, EventOrganizerName, SellPrice, ' \
                        f'Comment, OrganizerID, SerialNumber, isSold) ' \
                        f'VALUES (' \
                        f'{i[j_const.opened]}, ' \
                        f'\'{i[j_const.date]}\', ' \
                        f'\'{i[j_const.time]}\', ' \
                        f'\'{i[j_const.place]}\', ' \
                        f'\'{i[j_const.organizer]}\', ' \
                        f'{i[j_const.price]}, ' \
                        f'\'{i[j_const.comment]}\', ' \
                        f'\'{i[j_const.organizerid]}\', ' \
                        f'\'{i[j_const.serial]}\', {False}' \
                        f');'
    except KeyError as e:
        return f'invalid json key has been received, check: {e}'
    try:
        db.execute(sql_statement)
    except DataError as e:
        return f'invalid type! Details: {e}'
    return 'successful'


@app.route('/api/ticket/sell/id/<ticket_id>')
def ticket_sell(ticket_id):
    sql_statement = f'UPDATE tickets ' \
                    f'SET issold = {True} ' \
                    f'WHERE id = {ticket_id}'
    db.execute(sql_statement)
    return 'ok'


@app.route('/api/system/db/init_tables')
def initialize_all_tables():
    content = read_file('create_tables.sql')
    return execute_sql_commands(content)


@app.route('/api/system/db/drop_tables')
def drop_all_tables():
    # todo: a good permission check is vital for this action
    content = read_file('drop_all_tables.sql')
    return execute_sql_commands(content)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/api/json_example', methods=['POST'])
def example():
    content = request.json
    return jsonify(content)


def get_user_data(content):
    username = content.get(j_const.username)
    password = content.get(j_const.password)
    level = content.get(j_const.level)
    return username, password, level


def read_file(filename):
    file = open(filename, 'r')
    content = file.read()
    file.close()
    return content


def execute_sql_commands(content):
    sql_commands = content.split(';')
    for i in sql_commands:
        # as the given string could be received from a file,
        # newline characters must be deleted
        i = re.sub('[\n]', '', i)
        if len(i) != 0:
            # we don't want to execute empty command at the end of the file
            # (as a result of a possible semicolon after the last statement)
            db.execute(i)
    return 'ok'


drop_all_tables()
initialize_all_tables()
generate_test_db_data.generate(db, clear_existing=true)

if __name__ == '__main__':
    app.run()
