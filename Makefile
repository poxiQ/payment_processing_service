# run autotests inside container
test-entrypoint:
	echo "Tests are running ..."
	python -m pytest -x
	echo "Tests - OK"


# start service
up-entrypoint:
	uvicorn main:app --host 0.0.0.0 --port 8081 --forwarded-allow-ips="*" --proxy-headers


# build services in compose file for local development
build:
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev build --no-cache


# start services in compose file for local development
up:
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev up --remove-orphans --force-recreate -d


# stop services in compose file for local development
down:
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev down

# create migration
migrate-create:
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev \
	  exec backend alembic revision --autogenerate -m "${MSG:-auto_migration}"

# upgrade database
migrate-up:
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev \
	  exec backend alembic upgrade head

# downgrade migration
migrate-down:
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev \
	  exec backend alembic downgrade -1

# check history of migrations
migrate-history:
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev \
	  exec backend alembic history



# start services in compose file for local development and run tests
test:
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev up --remove-orphans --force-recreate -d
	docker compose -f docker-compose.yaml --env-file .env -p payments_service_dev exec backend /bin/bash -c "python -m pytest -x"


# test if service is working in the Docker container
healthcheck:
	echo "Healthcheck are running ..."
	curl --request GET --url http://127.0.0.1:8081/api/v1/general/check
	echo "Healthcheck - OK"


# check if current commit was deployed successfully
check:
	chmod +x ./check.sh
	./check.sh ${CHECK_URL} ${CHECK_TRIES_COUNT} ${CHECK_TRY_DELAY}
