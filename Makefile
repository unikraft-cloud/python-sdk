# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025, Unikraft GmbH.
# Licensed under the BSD-3-Clause License (the "License").
# You may not use this file except in compliance with the License.

# Prelude
WORKDIR             ?= $(CURDIR)
Q                   ?= @
CHANNEL             ?= prod-stable

# Tools
WGET                ?= wget
DOCKER              ?= docker
OPENAPI_GEN_VERSION ?= v7.17.0
UV                  ?= uv

.PHONY: all
all: generate

.PHONY: generate
generate: platform

.PHONY: platform
platform: platform.json
	$(Q)rm -rf $(WORKDIR)/unikraft_cloud_platform/
	$(Q)$(DOCKER) run \
		--rm \
		--volume "$(WORKDIR):/local" \
		--user="$(shell id -u):$(shell id -g)" \
		openapitools/openapi-generator-cli:$(OPENAPI_GEN_VERSION) generate \
			--generator-name python \
			--input-spec     /local/platform.json \
			--config         /local/config.yaml \
			--template-dir   /local/templates \
			--output         /local \
			--git-repo-id    unikraft-cloud \
			--git-user-id    python-sdk \
			$(OPENAPI_GENERATOR_EXTRA_OPTIONS)

platform.json:
	$(Q)$(WGET) -O $@ https://raw.githubusercontent.com/unikraft-cloud/openapi/$(CHANNEL)/platform.json

.PHONY: fmt
fmt:
	$(Q)$(UV) format