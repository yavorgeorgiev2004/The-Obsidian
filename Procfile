release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn obsidian_hotel.wsgi
