.PHONY: install lint format test examples all

install:
	pip install -e "../bh-audit-logger[all]"
	pip install "pytest>=7.0.0,<9" "ruff>=0.1.0,<1" "moto[dynamodb]>=5.0,<6"

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
