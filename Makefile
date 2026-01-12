# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025, Unikraft GmbH.
# Licensed under the BSD-3-Clause License (the "License").
# You may not use this file except in compliance with the License.

# Prelude
WORKDIR ?= $(CURDIR)
Q       ?= @
CHANNEL ?= prod-stable

# Tools
WGET ?= wget
UV   ?= uv

.PHONY: all
all: generate

.PHONY: generate
generate: platform

.PHONY: platform
platform:
	$(Q)rm -rf $(WORKDIR)/unikraft_cloud_platform
	$(Q)$(UV) tool run openapi-python-client generate \
		--url https://raw.githubusercontent.com/unikraft-cloud/openapi/$(CHANNEL)/platform.json \
		--config $(WORKDIR)/.platform-config.yaml \
		--custom-template-path $(WORKDIR)/templates \
		--overwrite \
		--output-path $(WORKDIR) \
		--meta uv \
