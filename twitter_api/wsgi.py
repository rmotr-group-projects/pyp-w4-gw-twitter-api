import os
from whitenoise import WhiteNoise

from twitter_api.main import app

app.debug = True
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'XYZ')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'XYZ')

application = WhiteNoise(app)
