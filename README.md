# django-events-onem
Events service app written in Django/Python using ONEmSDK.

### Quickstart


Works with Python 3.6. Preferably to work in a virtual environment,
use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io) to create a virtual environment.

1. `mkvirtualenv -p python3 events`
2. `git clone git@github.com:onem-developer/events.git`
3. `pip install -r requirements.txt`
4. `python manage.py makemigrations events`
5. `python manage.py migrate --run-syncdb`
6. `python manage.py loaddata onem_events.json`
7. `python manage.py runserver`
8. `ngrok http 8000`


### Testing the app

Register the app on the ONEm developer portal (https://testtool.dhq.onem:6060/);
Set the callback URL to the forwarding address obtained from ngrok's output;
Go to https://testtool.dhq.onem/ or in the "Test Client" option on sidenav and
send the registered name with # in front

### Important

1. Please access the app in admin mode first.(the request headers should contain
the `is_admin=True` flag) This will enable you to add/edit/delete events;

### Deploy to Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)
