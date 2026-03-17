from flask import Blueprint

tweets_bp = Blueprint('tweets', __name__)
users_bp = Blueprint('users', __name__)
notifications_bp = Blueprint('notifications', __name__)
bots_bp = Blueprint('bots', __name__)

from routes import tweets, users, notifications, bots
from routes.dm import dm_bp
