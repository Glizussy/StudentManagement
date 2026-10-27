.PHONY: dev prod down clean traffic config

COMPOSE = docker compose

dev:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d --build

prod:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml up -d --build

down:
	$(COMPOSE) down

clean:
	$(COMPOSE) down -v

traffic:
	bash scripts/traffic.sh

config:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml config
