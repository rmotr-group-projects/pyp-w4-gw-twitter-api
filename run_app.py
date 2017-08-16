import os

from twitter_api.main import app
from twitter_api import settings


if __name__ == '__main__':
    app.debug = True
    app.config['SECRET_KEY'] = "kljasdno9asud89uy981uoaisjdoiajsdm89uas980d"
    app.config['DATABASE'] = settings.DATABASE_NAME

    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    app.run(host=host, port=port)
