import os

from twitter_api.main import app


if __name__ == '__main__':
    app.debug = True

    app.config['DEBUG'] = True
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'XYZ')
    app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'XYZ')

    host = os.environ.get('IP', '127.0.0.1')
    port = int(os.environ.get('PORT', 8000))
    app.run(host=host, port=port)
