FROM python:3.13


# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Installing additional linux packages
RUN apt-get update && \
    apt-get install -y telnet make curl && \
    rm -rf /var/lib/apt/lists/*

# Installing python dependencies
RUN python3 -m pip --no-cache-dir install --upgrade pip && \
    python3 --version && \
    pip3 --version

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
