#!/bin/bash

python manage.py migrate --run-syncdb
python manage.py loaddata onem_events.json
