.DEFAULT_GOAL := help
.DELETE_ON_ERROR:
# Targets share generated output; serialize aggregate invocations even with -j.
.NOTPARALLEL:
ifeq ($(OS),Windows_NT)
PYTHON ?= python
NPM ?= npm.cmd
COMPOSER ?= composer.cmd
else
PYTHON ?= python3
NPM ?= npm
COMPOSER ?= composer
endif
# COMPOSER names an executable here; Composer reserves its environment value for a manifest.
unexport COMPOSER
NODE ?= node
PHP ?= php
DOTNET ?= dotnet


.PHONY: help install install-build dev test lint check build package clean security

help: ## Show commands; defaults never install, build, bump or deploy
	@echo "Python-Script-Runner - local development commands"
	@echo "  install                 Install editable runner, development and dashboard extras"
	@echo "  install-build           Install the standard Python build frontend"
	@echo "  dev                     Run the local dashboard API using the selected interpreter"
	@echo "  test                    Run focused unit tests with the selected interpreter"
	@echo "  lint                    Compile-check owned Python application modules"
	@echo "  check                   Run compile checks and unit tests"
	@echo "  build                   Build wheel and source distribution (requires make install-build)"
	@echo "  package                 Build the Python distributable archives"
	@echo "  clean                   Remove only untracked Python build/distribution outputs"
	@echo "  security                Audit declared Python runtime requirements"
	@echo "Override executable paths with PYTHON, NODE, NPM, PHP, COMPOSER or DOTNET. Run from the repository root."

install: ## Install editable runner, development and dashboard extras
	"$(PYTHON)" -m pip install -e ".[dev,dashboard]"

install-build: ## Install the standard Python build frontend
	"$(PYTHON)" -m pip install build

dev: ## Run the local dashboard API using the selected interpreter
	"$(PYTHON)" WEBAPI/api.py

test: ## Run focused unit tests with the selected interpreter
	"$(PYTHON)" -m pytest tests/unit -q

lint: ## Compile-check owned Python application modules
	"$(PYTHON)" -m compileall -q runner.py runners WEBAPI

check: ## Run compile checks and unit tests
	"$(MAKE)" lint
	"$(MAKE)" test

build: lint ## Build wheel and source distribution (requires make install-build)
	"$(PYTHON)" -m build

package: build ## Build the Python distributable archives

clean: ## Remove only untracked Python build/distribution outputs
	"$(PYTHON)" tools/make_support.py clean "build" "dist"

security: ## Audit declared Python runtime requirements
	"$(PYTHON)" -m pip_audit -r requirements.txt
