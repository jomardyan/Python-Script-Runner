.DEFAULT_GOAL := help

# Local quality and source packaging commands.
.PHONY: help install dev test lint build clean package security

help:
	@echo "Targets: install dev test lint build clean package security"

install:
	python -m pip install -e ".[dev,dashboard]"

dev:
	python WEBAPI/api.py

test:
	python -m pytest tests/unit -q

lint:
	python -m compileall -q runner.py runners WEBAPI

build:
	python -m build

clean:
	rm -rf build dist

package:
	python -m build

security:
	python -m pip_audit -r requirements.txt
