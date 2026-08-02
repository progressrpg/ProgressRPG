.PHONY: t

ddu: ddown dup
ddub: ddown dbuild
drub: dreset dbuild

dr:
	docker compose restart

ddown:
	docker compose down
dup:
	docker compose up
dbuild:
	docker compose up --build
dreset:
	docker compose down -v

ps:
	docker compose exec web python manage.py shell
ds:
	docker compose exec db psql -U progress -d progress

t:
	docker compose exec web python manage.py test $(t) --keepdb

stripelistener:
	stripe listen --forward-to localhost:8000/api/v1/payments/webhook/
