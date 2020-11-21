.DEFAULT_GOAL := all

# NOTE: This filename is also referenced in the GitHub action.
poetry_dev_bootstrap_file = .poetry_dev_up_to_date
poetry_prod_bootstrap_file = .poetry_prod_up_to_date
npm_bootstrap_file = .node_packages_up_to_date


# Default `make` will give everything's that helpful for local development.
.PHONY: all
all: install-python-dev install-js

.PHONY: check-poetry
check-poetry:
	@which poetry > /dev/null || (echo "Poetry not found - see https://python-poetry.org/docs/#installation" && exit 1)

.PHONY: install-js
install-js: $(npm_bootstrap_file)
$(npm_bootstrap_file): package.json package-lock.json
	touch $(npm_bootstrap_file).notyet
	npm install
	mv $(npm_bootstrap_file).notyet $(npm_bootstrap_file)

.PHONY: install-python-dev
install-python-dev: check-poetry $(poetry_dev_bootstrap_file)
$(poetry_dev_bootstrap_file): poetry.lock
	touch $(poetry_dev_bootstrap_file).notyet
	poetry install --no-root
	mv $(poetry_dev_bootstrap_file).notyet $(poetry_dev_bootstrap_file)
	@# Remove the prod bootstrap file, since we now have dev deps present.
	rm -f $(poetry_prod_bootstrap_file)

# Note this will actually *remove* any dev dependencies, if present
.PHONY: install-python-prod
install-python-prod: check-poetry $(poetry_prod_bootstrap_file)
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
fix: install-python-dev install-js
	poetry run black lambda_functions
	poetry run isort lambda_functions
	@# The default `log` level will output the filename of every checked file
	npx prettier --loglevel warn --write .

.PHONY: typecheck
typecheck: install-python-dev
	@# TODO: mypy will start being able to read from pyproject.toml soon
	@# (leaving the superfluous `--config-file` argument here to make that clear)
	poetry run mypy --config-file mypy.ini lambda_functions

.PHONY: lint
lint: install-python-dev install-js
	poetry run black --fast --check lambda_functions
	poetry run isort --check lambda_functions
	npx prettier --check .
	@# '0' tells pylint to auto-detect available processors
	poetry run pylint --jobs 0 lambda_functions

.PHONY: test
test: install-python-dev
	poetry run coverage run -m pytest lambda_functions

.PHONY: check
check: lint typecheck test

.PHONY: clean
clean:
	rm -f $(poetry_dev_bootstrap_file)
	rm -f $(poetry_prod_bootstrap_file)
	rm -f $(npm_bootstrap_file)
	rm -rf .mypy_cache
	rm -rf htmlcov
	find . -name '*.pyc' -delete
