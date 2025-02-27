#!/bin/sh

while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
    echo "Waiting for the DB..."
    sleep 3
done

python manage.py makemigrations account authentication follow log
python manage.py migrate

python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
username = '$POSTGRES_SUPER_USER';
email = '$POSTGRES_SUPER_EMAIL';
password = '$POSTGRES_SUPER_PASSWORD';
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password);
    print(f'Superuser \"{username}\" created.');
"

exec "$@"
