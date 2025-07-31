FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y \
    binutils libproj-dev gdal-bin \
    python3-dev libpq-dev gcc postgresql-client supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy codebase
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Supervisor setup
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
