.PHONY: up up-build down ps logs restart-gateway rebuild-auth rebuild-order rebuild-frontend health tf-init tf-plan tf-apply tf-destroy

up:
	docker compose up -d

up-build:
	docker compose up -d --build

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=120

restart-gateway:
	docker compose restart gateway

rebuild-auth:
	docker compose up -d --build auth-service && docker compose restart gateway

rebuild-order:
	docker compose up -d --build order-service && docker compose restart gateway

rebuild-frontend:
	docker compose up -d --build frontend && docker compose restart gateway

health:
	bash scripts/healthcheck.sh

tf-init:
	cd terraform && terraform init

tf-plan:
	cd terraform && terraform plan

tf-apply:
	cd terraform && terraform apply -auto-approve

tf-destroy:
	cd terraform && terraform destroy -auto-approve

