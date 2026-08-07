# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.

# Release channel to generate against (maps to a branch of the openapi repo).
CHANNEL           ?= prod-staging
SPEC_BASE         ?= https://raw.githubusercontent.com/unikraft-cloud/openapi/refs/heads/$(CHANNEL)
PLATFORM_SPEC     ?= $(SPEC_BASE)/platform.json
CONTROLPLANE_SPEC ?= $(SPEC_BASE)/controlplane.json

# The openapi-gen code generator, pinned so a regeneration is reproducible.
# Raise OPENAPI_GEN_VERSION to take a newer one.
GO                   ?= go
UV                   ?= uv
OPENAPI_GEN_VERSION  ?= v0.0.0-20260915145300-fef7701a6874
OPENAPI_GEN          ?= $(GO) run unikraft.com/x/tools/openapi-gen@$(OPENAPI_GEN_VERSION)

TEMPLATES     ?= ./templates
OUTPUT        ?= ./src/unikraft_cloud/api

.PHONY: all
all: generate test

.PHONY: generate
generate: ## Regenerate both plumbing clients from the OpenAPI specs.
	# Generated modules are cleared first, so a tag the spec drops leaves no
	# stale client behind. The hand-written `__init__.py` files stay.
	rm -f $(OUTPUT)/platform/*_gen.py $(OUTPUT)/controlplane/*_gen.py
	# Namespaced schema names (`Instances.Instance`) are not Python identifiers,
	# so the namespace is stripped from them.
	$(OPENAPI_GEN) \
		-i $(PLATFORM_SPEC) \
		-o $(OUTPUT)/platform \
		-t $(TEMPLATES) \
		--namespace-flatten strip \
		-v package=api
	$(OPENAPI_GEN) \
		-i $(CONTROLPLANE_SPEC) \
		-o $(OUTPUT)/controlplane \
		-t $(TEMPLATES) \
		--namespace-flatten strip \
		-v package=api
	$(MAKE) fmt

.PHONY: fmt
fmt: ## Format the generated (and all) sources.
	$(UV) run ruff check --select I --fix $(OUTPUT)
	$(UV) run ruff format $(OUTPUT)

.PHONY: typecheck
typecheck: ## Type-check the whole project.
	$(UV) run mypy

.PHONY: lint
lint: ## Lint and format-check with Ruff.
	$(UV) run ruff check .
	$(UV) run ruff format --check .

.PHONY: test
test: ## Run the test suite.
	$(UV) run pytest

.PHONY: build
build: ## Build the sdist and wheel.
	$(UV) build

.PHONY: clean
clean: ## Remove build output.
	rm -rf dist

.PHONY: help
help: ## Show this help.
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
