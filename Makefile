.PHONY: up up-build down ps logs restart-gateway rebuild-auth rebuild-order rebuild-frontend health validate-predeploy log-troubleshoot capacity-test scaling-proof tf-init tf-plan tf-apply tf-destroy

validate-predeploy:
	bash scripts/predeploy-validate.sh

up: validate-predeploy
	docker compose up -d

up-build: validate-predeploy
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

log-troubleshoot:
	bash scripts/log-troubleshoot.sh

capacity-test:
	bash scripts/capacity/run-capacity-test.sh

scaling-proof:
	bash scripts/capacity/run-scaling-proof.sh

tf-init:
	cd terraform && terraform init

tf-plan:
	cd terraform && terraform plan

tf-apply:
	cd terraform && terraform apply -auto-approve

tf-destroy:
	cd terraform && terraform destroy -auto-approve

