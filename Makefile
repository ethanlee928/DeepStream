build:
	docker-compose build

start:
	docker-compose up -d

attach:
	docker exec -it deepstream bash

clean:
	docker-compose down --remove-orphans
