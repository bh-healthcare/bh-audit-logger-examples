.PHONY: install lint format test examples all

install:
	pip install -e "../bh-audit-logger[jsonschema]"
	pip install pytest ruff

lint:
	ruff check examples/ tests/
	ruff format --check examples/ tests/

format:
	ruff check --fix examples/ tests/
	ruff format examples/ tests/

test:
	python3.11 -m pytest tests/ -v

examples:
	@for dir in examples/*/; do \
		echo "=== Running $$dir ==="; \
		python3.11 "$$dir/main.py" || exit 1; \
	done

all: lint test examples
