# Makefile for LSP Types Generator

.PHONY: help download-schemas generate-lsp-schema generate-types generate-latest-types

# Use bash for shell commands
SHELL := /bin/bash

# Default target
.DEFAULT_GOAL := help

# Suppress echoing of commands
.SILENT:

# Colors for help text
BLUE := \033[36m
NC := \033[0m

help: ## Show this help message
	echo -e "Usage: make [target]\n"
	echo -e "Targets:"
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2}'

download-schemas: ## Download latest LSP schemas (run this before generate-types)
	echo "Downloading latest LSP schemas..."
	uv run python -m assets.scripts.download_schemas
	echo "Done."

generate-lsp-schema:
	uv run datamodel-codegen \
		--input ./assets/lsprotocol/lsp.schema.json \
		--output ./assets/scripts/lsp_schema.py \
		--output-model-type "typing.TypedDict" \
		--target-python-version "3.12" \
		--input-file-type "jsonschema" \
		--use-field-description \
		--use-schema-description \
		--use-double-quotes

generate-pyright-schema:
	uv run datamodel-codegen \
		--input ./assets/lsps/pyright.schema.json \
		--output ./lsp_types/pyright/config_schema.py \
		--output-model-type "typing.TypedDict" \
		--target-python-version "3.12" \
		--input-file-type "jsonschema" \
		--use-field-description \
		--use-schema-description \
		--use-double-quotes

generate-types: ## Generate LSP type definitions
	echo "Generating LSP type definitions..."
	uv run python -m assets.scripts.generate
	echo "Formatting generated files..."
	uvx ruff format lsp_types/types.py lsp_types/requests.py lsp_types/methods.py
	uvx ruff check lsp_types/types.py lsp_types/requests.py lsp_types/methods.py --fix --silent || true
	echo "Done."

generate-latest-types: download-schemas generate-lsp-schema generate-pyright-schema generate-types ## Download latest LSP schemas and generate type definitions
