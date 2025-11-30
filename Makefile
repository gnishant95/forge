# Forge Makefile
# Run 'make help' for available commands

.PHONY: help start stop restart health logs clean setup

# Colors
RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
CYAN   := \033[0;36m
BOLD   := \033[1m
DIM    := \033[2m
NC     := \033[0m

# Required ports
PORTS := 80 8080 3306 6379 3000 9090 3100 3200 4318

help:
	@echo ""
	@echo "$(BLUE)╔═══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║  $(BOLD)🔥 FORGE$(NC)$(BLUE) - Self-hosted Infrastructure Platform              ║$(NC)"
	@echo "$(BLUE)╚═══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  $(YELLOW)make setup$(NC)     First-time setup (pull images, build)"
	@echo "  $(YELLOW)make start$(NC)     Start all services"
	@echo "  $(YELLOW)make stop$(NC)      Stop all services"
	@echo ""
	@echo "$(GREEN)Profiles (enable/disable services):$(NC)"
	@echo "  $(YELLOW)make start PROFILE=full$(NC)        All services (default)"
	@echo "  $(YELLOW)make start PROFILE=db,cache$(NC)    Only database + cache"
	@echo "  $(YELLOW)make start PROFILE=db$(NC)          Only MySQL"
	@echo ""
	@echo "$(GREEN)Status:$(NC)"
	@echo "  $(YELLOW)make health$(NC)    Quick health check"
	@echo "  $(YELLOW)make status$(NC)    Detailed system status (CPU, memory, etc.)"
	@echo "  $(YELLOW)make logs$(NC)      View logs (all services)"
	@echo "  $(YELLOW)make logs-api$(NC)  View logs for specific service"
	@echo "  $(YELLOW)make ps$(NC)        Show running containers"
	@echo "  $(YELLOW)make urls$(NC)      Show service URLs"
	@echo ""
	@echo "$(GREEN)Service Control:$(NC)"
	@echo "  $(YELLOW)make restart$(NC)          Restart all services"
	@echo "  $(YELLOW)make restart-nginx$(NC)    Restart specific service"
	@echo "  $(YELLOW)make rebuild-api$(NC)      Rebuild & restart (for code changes)"
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  $(YELLOW)make shell-mysql$(NC)  Open MySQL CLI"
	@echo "  $(YELLOW)make shell-redis$(NC)  Open Redis CLI"
	@echo ""
	@echo "$(GREEN)Cleanup:$(NC)"
	@echo "  $(YELLOW)make clean$(NC)     Stop and remove all containers/volumes"
	@echo ""
	@echo "$(DIM)Services: nginx, api, mysql, redis, grafana, prometheus, loki, tempo$(NC)"
	@echo ""

# ==============================================================================
# MAIN COMMANDS
# ==============================================================================

# Default profile - runs all services. Override with: make start PROFILE=db,cache
PROFILE ?= full

setup:
	@echo ""
	@echo "$(BLUE)╔═══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║                       FORGE SETUP                             ║$(NC)"
	@echo "$(BLUE)╚═══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Downloading Go dependencies...$(NC)"
	@cd api && go mod tidy 2>/dev/null || echo "  (skipped - will build in Docker)"
	@echo ""
	@echo "$(YELLOW)→ Pulling Docker images (this may take a few minutes)...$(NC)"
	@docker-compose --profile $(PROFILE) pull
	@echo ""
	@echo "$(YELLOW)→ Building Forge API...$(NC)"
	@docker-compose --profile $(PROFILE) build
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Setup complete! Run 'make start' to begin.$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""

start: _check-ports
	@echo ""
	@echo "$(BLUE)Starting Forge (profile: $(PROFILE))...$(NC)"
	@docker-compose --profile $(PROFILE) up -d --build
	@echo ""
	@echo "$(YELLOW)Waiting for services to start...$(NC)"
	@sleep 10
	@$(MAKE) --no-print-directory _wait-ready
	@echo ""
	@$(MAKE) --no-print-directory urls
	@echo ""
	@echo "$(GREEN)Forge is running!$(NC)"
	@echo ""
	@echo "Run $(YELLOW)make health$(NC) to check service status"

stop:
	@echo "$(YELLOW)Stopping Forge...$(NC)"
	@docker-compose --profile $(PROFILE) down
	@echo "$(GREEN)Stopped.$(NC)"

restart: stop start

restart-%:
	@echo "$(YELLOW)Restarting $*...$(NC)"
	@docker-compose restart $*
	@echo "$(GREEN)$* restarted$(NC)"

rebuild-%:
	@echo "$(YELLOW)Rebuilding $*...$(NC)"
	@docker-compose up -d --build $*
	@echo "$(GREEN)$* rebuilt and restarted$(NC)"

# ==============================================================================
# STATUS COMMANDS
# ==============================================================================

health:
	@echo ""
	@echo "$(BLUE)Service Health:$(NC)"
	@echo ""
	@echo "  $(BOLD)Core:$(NC)"
	@printf "    nginx:           " && curl -sf http://localhost/ >/dev/null 2>&1 && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    API:             " && curl -sf http://localhost:8080/api/v1/health >/dev/null 2>&1 && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    MySQL:           " && docker exec forge-mysql mysqladmin ping -h localhost --silent 2>/dev/null && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    Redis:           " && docker exec forge-redis redis-cli ping 2>/dev/null | grep -q PONG && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@echo ""
	@echo "  $(BOLD)Observability:$(NC)"
	@printf "    Grafana:         " && curl -sf http://localhost:3000/api/health >/dev/null 2>&1 && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    Prometheus:      " && curl -sf http://localhost:9090/-/ready >/dev/null 2>&1 && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    Loki:            " && curl -sf http://localhost:3100/ready >/dev/null 2>&1 && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    Tempo:           " && curl -sf http://localhost:3200/ready >/dev/null 2>&1 && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    Promtail:        " && docker inspect -f '{{.State.Running}}' forge-promtail 2>/dev/null | grep -q true && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@echo ""
	@echo "  $(BOLD)Exporters:$(NC)"
	@printf "    nginx-exporter:  " && docker inspect -f '{{.State.Running}}' forge-nginx-exporter 2>/dev/null | grep -q true && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    mysql-exporter:  " && docker inspect -f '{{.State.Running}}' forge-mysql-exporter 2>/dev/null | grep -q true && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@printf "    redis-exporter:  " && docker inspect -f '{{.State.Running}}' forge-redis-exporter 2>/dev/null | grep -q true && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)✗$(NC)"
	@echo ""

status:
	@echo ""
	@echo "$(BLUE)Forge Services:$(NC)"
	@echo "───────────────────────────────────────────────────────────────────────────────────────────"
	@printf "  %-18s %-12s %-7s %-22s %s\n" "SERVICE" "UPTIME" "CPU" "MEMORY" "ENDPOINT"
	@echo "───────────────────────────────────────────────────────────────────────────────────────────"
	@docker ps -a --filter "name=forge-" --format "{{.Names}}|{{.Status}}" | sort | while IFS='|' read name status; do \
		svc=$$(echo "$$name" | sed 's/forge-//'); \
		endpoint=$$(docker port $$name 2>/dev/null | head -1 | sed 's/.*-> //' | sed 's/0.0.0.0/localhost/' | sed 's/\[::\]:/localhost:/' || echo "-"); \
		[ -z "$$endpoint" ] && endpoint="-"; \
		if echo "$$status" | grep -q "^Up"; then \
			uptime=$$(echo "$$status" | sed 's/Up //' | sed 's/ (healthy)//' | sed 's/ (unhealthy)//'); \
			icon="$(GREEN)●$(NC)"; \
			echo "$$status" | grep -q "healthy" && icon="$(GREEN)✓$(NC)"; \
			stats=$$(docker stats $$name --no-stream --format "{{.CPUPerc}}|{{.MemUsage}}" 2>/dev/null); \
			cpu=$$(echo "$$stats" | cut -d'|' -f1); \
			mem=$$(echo "$$stats" | cut -d'|' -f2 | sed 's/ //g'); \
			printf "$$icon %-18s %-12s %-7s %-22s %s\n" "$$svc" "$$uptime" "$$cpu" "$$mem" "$$endpoint"; \
		else \
			printf "$(RED)○$(NC) %-18s %-12s %-7s %-22s %s\n" "$$svc" "$$status" "-" "-" "$$endpoint"; \
		fi \
	done
	@echo "───────────────────────────────────────────────────────────────────────────────────────────"
	@echo ""
	@echo "$(BLUE)Quick Links:$(NC)  http://localhost (gateway)  |  http://localhost/docs (API docs)"
	@echo ""

urls:
	@echo "$(BLUE)URLs:$(NC)"
	@echo "  Main:       http://localhost"
	@echo "  API Docs:   http://localhost/docs"
	@echo "  Grafana:    http://localhost/services/grafana"
	@echo "  Prometheus: http://localhost/services/prometheus"
	@echo ""
	@echo "$(BLUE)Direct Access:$(NC)"
	@echo "  API:        http://localhost:8080"
	@echo "  MySQL:      localhost:3306"
	@echo "  Redis:      localhost:6379"

logs:
	@docker-compose logs -f --tail=100

logs-%:
	@docker-compose logs -f --tail=100 $*

ps:
	@docker-compose ps

# ==============================================================================
# DATABASE SHELLS
# ==============================================================================

shell-mysql:
	@docker exec -it forge-mysql mysql -u root -pforgeroot

shell-redis:
	@docker exec -it forge-redis redis-cli

# ==============================================================================
# CLEANUP
# ==============================================================================

clean:
	@echo "$(YELLOW)Cleaning up...$(NC)"
	@docker-compose down -v --remove-orphans
	@echo "$(GREEN)Cleaned.$(NC)"

# ==============================================================================
# INTERNAL (not shown in help)
# ==============================================================================

_check-ports:
	@PORTS_IN_USE=""; \
	for port in $(PORTS); do \
		if lsof -i :$$port -sTCP:LISTEN >/dev/null 2>&1; then \
			PORTS_IN_USE="$$PORTS_IN_USE $$port"; \
		fi; \
	done; \
	if [ -n "$$PORTS_IN_USE" ]; then \
		echo ""; \
		echo "$(RED)╔═══════════════════════════════════════════════════════════════╗$(NC)"; \
		echo "$(RED)║                    PORT CONFLICT DETECTED                     ║$(NC)"; \
		echo "$(RED)╚═══════════════════════════════════════════════════════════════╝$(NC)"; \
		echo ""; \
		echo "$(RED)The following ports are already in use:$(NC)"; \
		for port in $$PORTS_IN_USE; do \
			PROCESS=$$(lsof -i :$$port -sTCP:LISTEN 2>/dev/null | tail -1 | awk '{print $$1}'); \
			PID=$$(lsof -i :$$port -sTCP:LISTEN 2>/dev/null | tail -1 | awk '{print $$2}'); \
			echo "  $(YELLOW)Port $$port$(NC) - used by $(BOLD)$$PROCESS$(NC) (PID: $$PID)"; \
		done; \
		echo ""; \
		echo "$(BLUE)To fix this, either:$(NC)"; \
		echo "  1. Stop the conflicting service(s)"; \
		echo "  2. Or change ports in $(YELLOW)docker-compose.yaml$(NC)"; \
		echo ""; \
		echo "$(BLUE)Port mapping:$(NC)"; \
		echo "  80→nginx  8080→api  3306→mysql  6379→redis"; \
		echo "  3000→grafana  9090→prometheus  3100→loki  3200→tempo"; \
		echo ""; \
		exit 1; \
	fi

_wait-ready:
	@printf "  Waiting for Loki..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -sf http://localhost:3100/ready >/dev/null 2>&1; then \
			echo " $(GREEN)✓$(NC)"; \
			break; \
		fi; \
		sleep 2; \
		if [ $$i -eq 10 ]; then echo " $(YELLOW)timeout$(NC)"; fi; \
	done
	@printf "  Waiting for Tempo..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -sf http://localhost:3200/ready >/dev/null 2>&1; then \
			echo " $(GREEN)✓$(NC)"; \
			break; \
		fi; \
		sleep 2; \
		if [ $$i -eq 10 ]; then echo " $(YELLOW)timeout$(NC)"; fi; \
	done
