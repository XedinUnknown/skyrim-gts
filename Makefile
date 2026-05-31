CONFIG ?= gts-index.config.json
DEPFILE ?= cache/gts-index.d
CURRENT_GAME_DOC ?= docs/current-game.md
ROOT_CURRENT_GAME ?= current-game.md
GTS_DB ?= $(shell python3 -c 'import json,os; c=json.load(open("$(CONFIG)")); print(os.environ.get("GTS_DB", c.get("db_path", "cache/gts-index/gts.sqlite")))')
INDEX_DB := $(GTS_DB)
MOD_METADATA_DB := $(GTS_DB)
RECIPE_STAMP := cache/gts-index/recipes.stamp
MOD_METADATA_STAMP := cache/gts-index/mod-metadata.stamp

.PHONY: help deps index rebuild search recipe chain item best clean-index mod-metadata mod-metadata-enrich mod-search clean-mod-metadata mod-summarize game-readme current-game

help:
	@printf '%s\n' \
	  'make gateway-start         Start MCP gateway (logs to /tmp/skyrim-gateway.log)' \
	  'make gateway-stop          Stop MCP gateway' \
	  'make gateway-status        Check if gateway is running' \
	  'make gateway-logs          Tail gateway logs' \
	  'make poller-start          Start progress poller' \
	  'make poller-stop           Stop progress poller' \
	  'make poller-logs           Tail poller logs' \
	  'make index                 Build/update the SQLite recipe index' \
	  'make rebuild               Force rebuild the SQLite recipe index' \
	  'make search Q=backpack     Search craftable item recipes' \
	  'make recipe Q="Leather Backpack"' \
	  'make chain Q="Leather Backpack" DEPTH=4' \
	  'make item Q="Black Leather Backpack"  Show item stats, recipe, source plugin, likely mod' \
	  'make best MATERIALS="leather strips"' \
	  'make deps                  Regenerate Make dependencies from MO2 profile' \
	  'make mod-metadata          Index active mod descriptions from local meta.ini' \
	  'make mod-metadata-enrich   Also enrich central cache via Nexus API' \
	  'make mod-search Q=perks    Search active mod descriptions' \
	  'make mod-summarize         AI-summarize mod descriptions via opencode (agent: modSummary)' \
	  'make mod-summarize GLOBAL=1' \
	  '  Same but summarize all mods in central cache (not just active)' \
	  'make mod-summarize FORCE=1' \
	  '  Regenerate summaries even when ai_summary already exists' \
	  'make mod-summarize TIMEOUT=120' \
	  '  Set per-batch opencode timeout in seconds' \
	  'make mod-summarize LOG=cache/gts-index/mod-summarize.log' \
	  '  Write raw model output/debug logs to a file' \
	  'make mod-summarize BATCH=20' \
	  '  Set mods per opencode batch' \
	  'make mod-summarize MODIDS=45855,45574' \
	  '  Same but summarize only specific mods by Nexus modid' \
	  'make game-readme           Generate docs/current-game.md and ./current-game.md' \
	  'make current-game          Alias for make game-readme' \
	  'docker compose run --rm tools make help'

-include $(DEPFILE)

deps: $(DEPFILE)

$(DEPFILE): $(CONFIG) tools/gts_index_deps.py
	python3 tools/gts_index_deps.py --config "$(CONFIG)" --out "$@" --target "$(RECIPE_STAMP)"

index: $(RECIPE_STAMP)

$(RECIPE_STAMP): $(DEPFILE) $(MOD_METADATA_STAMP) tools/gts_recipes_export.py tools/GtsItemRecipeExporter/Program.cs tools/GtsItemRecipeExporter/GtsItemRecipeExporter.csproj
	python3 tools/gts_recipes_export.py --config "$(CONFIG)"
	@mkdir -p "$(dir $@)"
	@touch "$@"

rebuild:
	rm -f "$(INDEX_DB)" "$(RECIPE_STAMP)" "$(MOD_METADATA_STAMP)"
	$(MAKE) mod-metadata
	$(MAKE) index

search: index
	@test -n "$(Q)" || { printf 'Set Q, e.g. make search Q=backpack\n' >&2; exit 2; }
	python3 tools/query_item_recipes.py --db "$(INDEX_DB)" search "$(Q)"

recipe: index
	@test -n "$(Q)" || { printf 'Set Q, e.g. make recipe Q="Leather Backpack"\n' >&2; exit 2; }
	python3 tools/query_item_recipes.py --db "$(INDEX_DB)" recipe "$(Q)"

chain: index
	@test -n "$(Q)" || { printf 'Set Q, e.g. make chain Q="Leather Backpack"\n' >&2; exit 2; }
	python3 tools/query_item_recipes.py --db "$(INDEX_DB)" chain "$(Q)" --depth "$(or $(DEPTH),4)"

item: mod-metadata index
	@test -n "$(Q)" || { printf 'Set Q, e.g. make item Q="Black Leather Backpack"\n' >&2; exit 2; }
	python3 tools/query_item_recipes.py --db "$(INDEX_DB)" lookup "$(Q)" --metadata-db "$(MOD_METADATA_DB)"

best: index
	@test -n "$(MATERIALS)" || { printf 'Set MATERIALS, e.g. make best MATERIALS="leather strips"\n' >&2; exit 2; }
	python3 tools/query_item_recipes.py --db "$(INDEX_DB)" best $(MATERIALS)

clean-index:
	rm -rf "$(dir $(INDEX_DB))" "$(DEPFILE)"

mod-metadata: $(MOD_METADATA_STAMP)

$(MOD_METADATA_STAMP): $(CONFIG) tools/index_mod_metadata.py
	python3 tools/index_mod_metadata.py --config "$(CONFIG)" index
	@mkdir -p "$(dir $@)"
	@touch "$@"

mod-metadata-enrich:
	python3 tools/index_mod_metadata.py --config "$(CONFIG)" index --enrich
	@mkdir -p "$(dir $(MOD_METADATA_STAMP))"
	@touch "$(MOD_METADATA_STAMP)"

mod-search: mod-metadata
	@test -n "$(Q)" || { printf 'Set Q, e.g. make mod-search Q=perks\n' >&2; exit 2; }
	python3 tools/index_mod_metadata.py --config "$(CONFIG)" search "$(Q)"

clean-mod-metadata:
	rm -f "$(MOD_METADATA_STAMP)"

mod-summarize: mod-metadata
	PYTHONUNBUFFERED=1 $(if $(BATCH),MOD_SUMMARY_BATCH_SIZE=$(BATCH)) python3 tools/summarize_mods.py --config "$(CONFIG)" \
	  $(if $(LIMIT),--limit $(LIMIT)) \
	  run \
	  $(if $(GLOBAL),--global) \
	  $(if $(MODIDS),--modids $(MODIDS)) \
	  $(if $(FORCE),--force) \
	  $(if $(TIMEOUT),--timeout $(TIMEOUT)) \
	  $(if $(LOG),--log-file $(LOG)) \
	  $(if $(MODEL),--model $(MODEL))

game-readme: mod-metadata
	python3 tools/generate_current_game_readme.py --config "$(CONFIG)" --out "$(CURRENT_GAME_DOC)"
	cp "$(CURRENT_GAME_DOC)" "$(ROOT_CURRENT_GAME)"

current-game: game-readme

# ---------------------------------------------------------------------------
# Skyrim MCP Gateway + Progress Poller
# ---------------------------------------------------------------------------

GATEWAY_HOST ?= 127.0.0.1
GATEWAY_PORT ?= 8765
GATEWAY_PID_FILE := .gateway.pid
GATEWAY_LOG ?= /tmp/skyrim-gateway.log

.PHONY: gateway-start gateway-stop gateway-status gateway-logs poller-start poller-stop poller-logs

gateway-start:
	@echo "Starting MCP gateway on $(GATEWAY_HOST):$(GATEWAY_PORT)..."
	@setsid python3 scripts/mcp-gateway/gateway.py --host $(GATEWAY_HOST) --port $(GATEWAY_PORT) > "$(GATEWAY_LOG)" 2>&1 &
	@echo $$! > "$(GATEWAY_PID_FILE)"
	@echo "Gateway started (PID $$!). Logs: make gateway-logs"

gateway-stop:
	@if [ -f "$(GATEWAY_PID_FILE)" ]; then \
	  kill $$(cat "$(GATEWAY_PID_FILE)") 2>/dev/null && echo "Gateway stopped." || echo "Gateway not running."; \
	  rm -f "$(GATEWAY_PID_FILE)"; \
	else \
	  echo "No gateway PID file found."; \
	fi

gateway-status:
	@if [ -f "$(GATEWAY_PID_FILE)" ] && kill -0 $$(cat "$(GATEWAY_PID_FILE)") 2>/dev/null; then \
	  echo "Gateway running (PID $$(cat "$(GATEWAY_PID_FILE)"))"; \
	else \
	  echo "Gateway not running."; \
	fi

gateway-logs:
	@tail -f "$(GATEWAY_LOG)"

poller-start:
	@echo "Starting progress poller..."
	@docker compose up -d progress-poller
	@echo "Poller started. View logs: make poller-logs"

poller-stop:
	@docker compose stop progress-poller
	@echo "Poller stopped."

poller-logs:
	@docker compose logs -f progress-poller
