"""Non-waiting shared MySQL capacity slots for opt-in consumer inference."""
from functools import wraps
import os
import pymysql
from flask import current_app, jsonify


def bounded_inference(database):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not current_app.config.get('CONSUMER_ENABLED'):
                return function(*args, **kwargs)
            try:
                slots = min(4, max(1, int(os.getenv('DERMAMATRIX_INFERENCE_SLOTS', '1'))))
            except ValueError:
                slots = 1
            connection = None; lock = None
            try:
                connection = database()
                with connection.cursor() as cursor:
                    for number in range(slots):
                        name = f'dmx-inference-capacity:{number}'
                        cursor.execute('SELECT GET_LOCK(%s,0) AS acquired', (name,))
                        if cursor.fetchone()['acquired']:
                            lock = name; break
                if lock is None:
                    response = jsonify(error='Assessment capacity is busy. Your input has not been processed. Retry shortly.', code='ASSESSMENT_CAPACITY_BUSY')
                    response.headers['Retry-After'] = '5'
                    return response, 503
                return function(*args, **kwargs)
            except pymysql.MySQLError:
                return jsonify(error='Assessment capacity could not be confirmed. Retry shortly.', code='CAPACITY_UNAVAILABLE'), 503
            finally:
                if connection is not None:
                    try:
                        if lock:
                            try:
                                with connection.cursor() as cursor:
                                    cursor.execute('SELECT RELEASE_LOCK(%s)', (lock,))
                            except pymysql.MySQLError:
                                current_app.logger.warning('Inference capacity cleanup requires connection closure.')
                    finally:
                        connection.close()
        return wrapped
    return decorate
