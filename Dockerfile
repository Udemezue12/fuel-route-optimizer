FROM ghcr.io/opengeospatial/ogc-python:latest

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    binutils libproj-dev gdal-bin \
    python3-dev libpq-dev gcc postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["uvicorn", "fuel_project.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
