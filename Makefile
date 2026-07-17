PYTHON ?= python3
WHEELHOUSE ?= dist
SHELLCHECK ?= shellcheck
RUFF ?= ruff
PRE_COMMIT ?= pre-commit
SHELLCHECK_FILES := $(shell find benchmarks reproducibility -type f -name '*.sh' | sort)

.PHONY: help discovery unit test live-cluster-test compile ruff shellcheck codespell links lint pre-commit build check artifact-smoke artifact-all artifact-validate clean

help:
	@printf '%s\n' \
		'Targets:' \
		'  make discovery  Check setuptools package discovery' \
		'  make unit       Run offline tests' \
		'  make test       Run pytest without live-cluster tests' \
		'  make live-cluster-test  Run or skip Kubernetes/live-cluster pytest markers' \
		'  make lint       Run ruff, compileall, shellcheck, codespell, and Markdown-link checks' \
		'  make build      Build an sdist and wheel with python -m build' \
		'  make check      Run discovery, lint, tests, and package build' \
		'  make artifact-smoke     Regenerate a representative artifact subset' \
		'  make artifact-all       Regenerate all artifact outputs from curated data' \
		'  make artifact-validate  Validate artifact structure, checksums, and outputs' \
		'  make clean      Remove local build and test artifacts'

discovery:
	@$(PYTHON) -c "from setuptools import find_namespace_packages; pkgs=find_namespace_packages('src', include=['idynamics*','iDynamicsPackagesModules*']); print('\n'.join(pkgs)); assert 'idynamics' in pkgs; assert 'iDynamicsPackagesModules' in pkgs"

unit:
	$(PYTHON) -m pytest -m "not integration and not live_cluster"

test:
	$(PYTHON) -m pytest -m "not live_cluster"

live-cluster-test:
	IDYNAMICS_RUN_LIVE_CLUSTER=1 $(PYTHON) -m pytest -m live_cluster; status=$$?; \
	if [ $$status -eq 5 ]; then \
		printf '%s\n' 'No live_cluster tests are shipped in this public release; skipping.'; \
		exit 0; \
	fi; \
	exit $$status

compile:
	$(PYTHON) -m compileall -q src tests scripts

ruff:
	@if command -v $(RUFF) >/dev/null 2>&1; then \
		$(RUFF) check src tests scripts reproducibility; \
	else \
		printf '%s\n' 'ruff is not installed; running Python syntax validation fallback.'; \
		$(PYTHON) -m compileall -q src tests scripts reproducibility; \
	fi

shellcheck:
	$(SHELLCHECK) $(SHELLCHECK_FILES)

codespell:
	codespell --toml pyproject.toml

links:
	$(PYTHON) scripts/check_markdown_links.py

lint: ruff compile shellcheck codespell links

pre-commit:
	@if command -v $(PRE_COMMIT) >/dev/null 2>&1; then \
		$(PRE_COMMIT) run --all-files; \
	else \
		printf '%s\n' 'pre-commit is not installed; running local hook targets directly.'; \
		$(MAKE) ruff codespell shellcheck links; \
	fi

build:
	@if $(PYTHON) -m build --version >/dev/null 2>&1; then \
		$(PYTHON) -m build --outdir $(WHEELHOUSE); \
	else \
		printf '%s\n' 'python -m build is not installed; using setuptools build backend directly.'; \
		$(PYTHON) scripts/build_package.py --outdir $(WHEELHOUSE); \
	fi

check: discovery lint test build

ARTIFACT_OUT ?= reproducibility/generated

artifact-smoke:
	$(PYTHON) reproducibility/reproduce_all.py --artifact table-ii --artifact figure-07 --output-root $(ARTIFACT_OUT)/smoke
	$(PYTHON) reproducibility/validate_artifacts.py --skip-regenerate

artifact-all:
	$(PYTHON) reproducibility/reproduce_all.py --output-root $(ARTIFACT_OUT)/all

artifact-validate:
	$(PYTHON) reproducibility/validate_artifacts.py

clean:
	rm -rf build dist .pytest_cache .ruff_cache .mypy_cache htmlcov src/*.egg-info
	rm -rf reproducibility/generated
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
