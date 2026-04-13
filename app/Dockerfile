FROM python:3.13 AS base

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installing additional linux packages
RUN apt-get update && \
    apt-get install -y telnet make curl && \
    rm -rf /var/lib/apt/lists/*

# Installing python dependencies
RUN python3 -m pip --no-cache-dir install --upgrade pip

# Create Folder for service logs
RUN mkdir /service-logs

WORKDIR /app

COPY ./Pipfile ./Pipfile.lock ./Makefile ./commit.txt ./
COPY ./app /app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir pipenv==2024.4.1 \
    && pipenv sync --system \
    && rm -rf Pipfile.lock Pipfile

RUN test -s /app/alembic.ini && grep -q "script_location" /app/alembic.ini

FROM base AS backend

EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM base AS worker

CMD ["python", "-m", "app.broker.outbox_publisher"]