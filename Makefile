.DEFAULT_GOAL := all

poetry_dev_bootstrap_file = .poetry_dev_up_to_date
poetry_prod_bootstrap_file = .poetry_prod_up_to_date


# Default `make` will give everything's that helpful for local development.
.PHONY: all
all: install-dev

.PHONY: check-poetry
check-poetry:
	@which poetry > /dev/null || (echo "Poetry not found - see https://python-poetry.org/docs/#installation" && exit 1)

.PHONY: install-dev
install-dev: check-poetry $(poetry_dev_bootstrap_file)
$(poetry_dev_bootstrap_file): poetry.lock
	touch $(poetry_dev_bootstrap_file).notyet
	poetry install --no-root
	mv $(poetry_dev_bootstrap_file).notyet $(poetry_dev_bootstrap_file)
	@# Remove the prod bootstrap file, since we now have dev deps present.
	rm -f $(poetry_prod_bootstrap_file)

# Note this will actually *remove* any dev dependencies, if present
.PHONY: install-prod
install-prod: check-poetry $(poetry_prod_bootstrap_file)
$(poetry_prod_bootstrap_file): poetry.lock
	touch $(poetry_prod_bootstrap_file).notyet
	poetry install --no-root --no-dev
	mv $(poetry_prod_bootstrap_file).notyet $(poetry_prod_bootstrap_file)
	@# Remove the dev bootstrap file, since the `--no-dev` removed any present dev deps
	rm -f $(poetry_dev_bootstrap_file)

.PHONY: check
check: lint test

# Run automatic code formatters/linters that don't require human input
# (might fix a broken `make check`)
.PHONY: fix
fix: install-dev
	black lambda_functions
	isort lambda_functions

.PHONY: typecheck
typecheck: install-dev
	@# TODO: mypy will start being able to read from pyproject.toml soon
	@# (leaving the superfluous `--config-file` argument here to make that clear)
	poetry run mypy --config-file mypy.ini lambda_functions

.PHONY: lint
lint: install-dev
	black --fast --check lambda_functions
	isort --check lambda_functions
	@# '0' tells pylint to auto-detect available processors
	pylint --jobs 0 lambda_functions

.PHONY: test
test: install-dev
	poetry run coverage run -m pytest lambda_functions

.PHONY: check
check: lint typecheck test

.PHONY: clean
clean:
	rm -f $(poetry_dev_bootstrap_file)
	rm -f $(poetry_prod_bootstrap_file)
	rm -rf .mypy_cache
	rm -rf htmlcov
	find . -name '*.pyc' -delete
