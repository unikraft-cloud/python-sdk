# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH.

# Release channel to generate against (maps to a branch of the openapi repo).
CHANNEL           ?= prod-staging
SPEC_BASE         ?= https://raw.githubusercontent.com/unikraft-cloud/openapi/refs/heads/$(CHANNEL)
PLATFORM_SPEC     ?= $(SPEC_BASE)/platform.json
CONTROLPLANE_SPEC ?= $(SPEC_BASE)/controlplane.json

# Both specs also live in the proto repository, which is where the changes land
# first. Generate against a local checkout of it with:
#   make generate \
#     PLATFORM_SPEC=../proto/gen/openapi/platform/openapi.yaml \
#     CONTROLPLANE_SPEC=../proto/gen/openapi/controlplane/openapi.yaml

# The openapi-gen code generator. While the Python template functions are
# unreleased, build it from a local checkout and point OPENAPI_GEN at the
# binary (this repository is not a Go module, so `go run <path>` won't work,
# and `go -C` would break the relative -t/-o paths below):
#   (cd ../x/tools/openapi-gen && go build -o /tmp/openapi-gen .)
#   make generate OPENAPI_GEN=/tmp/openapi-gen
GO            ?= go
UV            ?= uv
OPENAPI_GEN   ?= $(GO) run unikraft.com/x/tools/openapi-gen@latest

TEMPLATES     ?= ./templates
OUTPUT        ?= ./src/unikraft_cloud/api

.PHONY: all
all: generate test

.PHONY: generate
generate: ## Regenerate both plumbing clients from the OpenAPI specs.
	$(OPENAPI_GEN) \
		-i $(PLATFORM_SPEC) \
		-o $(OUTPUT)/platform \
		-t $(TEMPLATES) \
		-v package=api
	$(OPENAPI_GEN) \
		-i $(CONTROLPLANE_SPEC) \
		-o $(OUTPUT)/controlplane \
		-t $(TEMPLATES) \
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
