
set -e

echo "▶️ Running Django migrations..."
python manage.py makemigrations
python manage.py migrate

echo "✅ Migrations complete."


exec "$@"
