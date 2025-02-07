# Makefile for LSP Types Generator

.PHONY: help generate-types download-schemas

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
	python -m assets.scripts.download_schemas
	echo "Done."

generate-types: ## Generate LSP type definitions
	echo "Generating LSP type definitions..."
	python -m assets.scripts.generate
	echo "Done."

generate-latest-types: download-schemas generate-types ## Download latest LSP schemas and generate type definitions
