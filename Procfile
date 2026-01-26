web: python manage.py migrate && gunicorn smartbet.wsgi:application --bind 0.0.0.0:$PORT --access-logfile - --log-file -
worker: python manage.py run_scheduler --interval 60 --run-now
