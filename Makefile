# Makefile for Pythonium Development and Packaging

# Package configuration
PACKAGE_NAME = pythonium
VERSION = 0.1.2
ARCHITECTURE = all
DEB_FILE = $(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE).deb
RPM_FILE = $(PACKAGE_NAME)-$(VERSION)-1.$(ARCHITECTURE).rpm
MAINTAINER = David Harvey <dwh.exis@gmail.com>
DESCRIPTION = Python Model Context Protocol server

# Directories
BUILD_DIR = build
PROJECT_ROOT = .
VENV_DIR = venv

# Python configuration - use virtual environment if available
PYTHON_BASE = python3
PIP_BASE = pip3
ifdef VIRTUAL_ENV
    PYTHON = python
    PIP = pip
else ifneq ("$(wildcard $(VENV_DIR)/bin/python)","")
    PYTHON = $(VENV_DIR)/bin/python
    PIP = $(VENV_DIR)/bin/pip
else
    PYTHON = $(PYTHON_BASE)
    PIP = $(PIP_BASE)
endif

# Default target
.PHONY: all
all: test lint

# Development targets
.PHONY: test
test:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -v

.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest tests/ --cov=pythonium --cov-report=html --cov-report=term

.PHONY: lint
lint:
	@echo "Running linter (flake8)..."
	python3 -m flake8 pythonium/ tests/ --max-line-length=88 --ignore=E203,W503

.PHONY: format
format:
	@echo "Formatting code with black..."
	python3 -m black pythonium/ tests/ --line-length=88

.PHONY: format-check
format-check:
	@echo "Checking code formatting..."
	python3 -m black --check pythonium/ tests/ --line-length=88

.PHONY: type-check
type-check:
	@echo "Running type checker (mypy)..."
	python3 -m mypy pythonium/ --ignore-missing-imports --show-error-codes

.PHONY: security-check
security-check:
	@echo "Running security checks (bandit)..."
	python3 -m bandit -r pythonium/ -f json -o security-report.json || true
	@echo "Security report generated: security-report.json"

.PHONY: import-sort
import-sort:
	@echo "Sorting imports..."
	python3 -m isort pythonium/ tests/

.PHONY: import-check
import-check:
	@echo "Checking import order..."
	python3 -m isort --check-only pythonium/ tests/

.PHONY: install-dev
install-dev:
	@echo "Installing development dependencies..."
	$(PIP) install -r requirements-dev.txt

.PHONY: quality-check
quality-check: format-check lint type-check import-check security-check
	@echo "All quality checks completed!"

.PHONY: ci
ci: test quality-check
	@echo "CI pipeline completed successfully!"

.PHONY: fix
fix: format import-sort
	@echo "Code formatting and import sorting applied!"

# Virtual environment management
.PHONY: venv
venv:
	@echo "Setting up virtual environment..."
	python3 -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -r requirements.txt
	$(VENV_DIR)/bin/pip install -r requirements-dev.txt

.PHONY: venv-clean
venv-clean:
	@echo "Removing virtual environment..."
	rm -rf $(VENV_DIR)

.PHONY: install-editable
install-editable:
	@echo "Installing package in editable mode..."
	$(PIP) install -e .

# PyPI publishing
.PHONY: build
build: clean
	@echo "Building package for PyPI..."
	$(PYTHON) -m build

.PHONY: build-wheel
build-wheel: clean
	@echo "Building wheel package..."
	$(PYTHON) -m build --wheel

.PHONY: build-sdist
build-sdist: clean
	@echo "Building source distribution..."
	$(PYTHON) -m build --sdist

.PHONY: check-package
check-package: build
	@echo "Checking package with twine..."
	$(PYTHON) -m twine check dist/*

.PHONY: upload-test
upload-test: build check-package
	@echo "Uploading to Test PyPI..."
	$(PYTHON) -m twine upload --repository testpypi dist/*

.PHONY: upload-pypi
upload-pypi: build check-package
	@echo "Uploading to PyPI..."
	$(PYTHON) -m twine upload dist/*

.PHONY: install-build-tools
install-build-tools:
	@echo "Installing build tools..."
	$(PIP) install build twine

# MCP Server management
.PHONY: run
run:
	@echo "Starting Pythonium MCP server..."
	$(PYTHON) -m pythonium serve

.PHONY: run-dev
run-dev:
	@echo "Starting Pythonium MCP server in development mode..."
	$(PYTHON) -m pythonium serve --transport stdio --verbose

.PHONY: analyze-path
analyze-path:
	@echo "Analyzing specific path with Pythonium..."
	@if [ -z "$(PATH_TO_ANALYZE)" ]; then \
		echo "Usage: make analyze-path PATH_TO_ANALYZE=<path>"; \
		exit 1; \
	fi
	$(PYTHON) -m pythonium analyze $(PATH_TO_ANALYZE) --exit-immediately

# Clean build artifacts
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)
	rm -f $(BUILD_DIR)/$(DEB_FILE)
	rm -f $(BUILD_DIR)/$(RPM_FILE)
	rm -rf $(BUILD_DIR)/rpm/
	rm -rf $(BUILD_DIR)/staging/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -f security-report.json
	rm -rf .pythonium_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Show package information
.PHONY: info
info:
	@echo "Package Information:"
	@echo "  Name: $(PACKAGE_NAME)"
	@echo "  Version: $(VERSION)"
	@echo "  Architecture: $(ARCHITECTURE)"
	@echo "  DEB File: $(DEB_FILE)"
	@echo "  RPM File: $(RPM_FILE)"
	@echo "  Maintainer: $(MAINTAINER)"
	@echo "  Description: $(DESCRIPTION)"
	@echo "  Build Directory: $(BUILD_DIR)"

# Help target
.PHONY: help
help:
	@echo "Pythonium Development and Packaging Makefile"
	@echo ""
	@echo "Development targets:"
	@echo "  test             - Run tests"
	@echo "  test-coverage    - Run tests with coverage"
	@echo "  lint             - Run linter (flake8)"
	@echo "  format           - Format code with black"
	@echo "  format-check     - Check code formatting"
	@echo "  type-check       - Run type checker (mypy)"
	@echo "  security-check   - Run security checks (bandit)"
	@echo "  import-sort      - Sort imports"
	@echo "  import-check     - Check import order"
	@echo "  quality-check    - Run all quality checks"
	@echo "  ci               - Run CI pipeline (tests + quality)"
	@echo "  fix              - Fix formatting and imports"
	@echo ""
	@echo "Environment targets:"
	@echo "  venv             - Set up virtual environment"
	@echo "  venv-clean       - Remove virtual environment"
	@echo "  install-dev      - Install development dependencies"
	@echo "  install-editable - Install package in editable mode"
	@echo "  install-build-tools - Install PyPI build tools"
	@echo ""
	@echo "PyPI publishing targets:"
	@echo "  build            - Build package for PyPI"
	@echo "  build-wheel      - Build wheel package"
	@echo "  build-sdist      - Build source distribution"
	@echo "  check-package    - Check package with twine"
	@echo "  upload-test      - Upload to Test PyPI"
	@echo "  upload-pypi      - Upload to PyPI"
	@echo ""
	@echo "MCP Server targets:"
	@echo "  run              - Start Pythonium MCP server"
	@echo "  run-dev          - Start server in development mode"
	@echo ""
	@echo "Utility targets:"
	@echo "  clean            - Clean all build artifacts"
	@echo "  info             - Show package information"
	@echo "  help             - Show this help message"
	@echo ""
	@echo "Debian packaging targets:"
	@echo "  deb              - Build Debian package using FPM"
	@echo "  deb-native       - Build Debian package natively"
	@echo "  install-deb      - Install the built DEB package (requires sudo)"
	@echo "  test-deb         - Test DEB package integrity without installing"
	@echo ""
	@echo "RPM packaging targets:"
	@echo "  rpm              - Build RPM package using FPM"
	@echo "  rpm-native       - Build RPM package natively"
	@echo "  install-rpm      - Install the built RPM package (requires sudo)"
	@echo "  test-rpm         - Test RPM package integrity without installing"
	@echo ""
	@echo "Package management targets:"
	@echo "  packages         - Build both DEB and RPM packages"
	@echo "  install          - Install package based on system (DEB/RPM)"
	@echo "  uninstall        - Remove the installed package (requires sudo)"
	@echo "  test-packages    - Test both package types"
	@echo "  install-packaging-tools - Install FPM and packaging tools"
	@echo ""
	@echo "Examples:"
	@echo "  make venv              # Set up development environment"
	@echo "  make ci                # Run full CI pipeline"
	@echo "  make run               # Start MCP server"
	@echo "  make deb               # Build DEB package"
	@echo "  make rpm               # Build RPM package"
	@echo "  make packages          # Build both DEB and RPM packages"

# Build Debian package
.PHONY: deb
deb: clean build-wheel
	@echo "Building Debian package..."
	@mkdir -p $(BUILD_DIR)
	@mkdir -p $(BUILD_DIR)/staging/usr/local/bin
	@mkdir -p $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)
	# Copy the wheel file to the package
	@cp dist/*.whl $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/
	@cp requirements.txt $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/
	# Create virtual environment during build
	@echo "Creating virtual environment during package build..."
	@python3 -m venv $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/venv
	@$(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/venv/bin/pip install --upgrade pip
	@$(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/venv/bin/pip install $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/*.whl
	# Create simple wrapper script
	@echo '#!/bin/bash' > $(BUILD_DIR)/staging/usr/local/bin/pythonium
	@echo 'exec /usr/share/$(PACKAGE_NAME)/venv/bin/pythonium "$$@"' >> $(BUILD_DIR)/staging/usr/local/bin/pythonium
	@chmod +x $(BUILD_DIR)/staging/usr/local/bin/pythonium
	fpm -s dir -t deb \
		--name "$(PACKAGE_NAME)" \
		--version "$(VERSION)" \
		--architecture "$(ARCHITECTURE)" \
		--maintainer "$(MAINTAINER)" \
		--description "$(DESCRIPTION)" \
		--depends "python3" \
		--depends "python3-pip" \
		--depends "python3-venv" \
		--package "$(BUILD_DIR)/$(DEB_FILE)" \
		-C $(BUILD_DIR)/staging \
		usr/

# Build RPM package  
.PHONY: rpm
rpm: clean build-wheel
	@echo "Building RPM package..."
	@mkdir -p $(BUILD_DIR)
	@mkdir -p $(BUILD_DIR)/staging/usr/local/bin
	@mkdir -p $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)
	# Copy the wheel file to the package
	@cp dist/*.whl $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/
	@cp requirements.txt $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/
	# Create virtual environment during build
	@echo "Creating virtual environment during package build..."
	@python3 -m venv $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/venv
	@$(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/venv/bin/pip install --upgrade pip
	@$(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/venv/bin/pip install $(BUILD_DIR)/staging/usr/share/$(PACKAGE_NAME)/*.whl
	# Create simple wrapper script
	@echo '#!/bin/bash' > $(BUILD_DIR)/staging/usr/local/bin/pythonium
	@echo 'exec /usr/share/$(PACKAGE_NAME)/venv/bin/pythonium "$$@"' >> $(BUILD_DIR)/staging/usr/local/bin/pythonium
	@chmod +x $(BUILD_DIR)/staging/usr/local/bin/pythonium
	fpm -s dir -t rpm \
		--name "$(PACKAGE_NAME)" \
		--version "$(VERSION)" \
		--architecture "$(ARCHITECTURE)" \
		--maintainer "$(MAINTAINER)" \
		--description "$(DESCRIPTION)" \
		--depends "python3" \
		--depends "python3-pip" \
		--package "$(BUILD_DIR)/$(RPM_FILE)" \
		-C $(BUILD_DIR)/staging \
		usr/

# Build both deb and rpm packages
.PHONY: packages
packages: deb rpm
	@echo "Built both DEB and RPM packages"

# Alternative native Debian package build
.PHONY: deb-native
deb-native: clean
	@echo "Building native Debian package..."
	@mkdir -p $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)
	@mkdir -p $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/DEBIAN
	@mkdir -p $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/usr/local/lib/python3/dist-packages
	@mkdir -p $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/usr/local/bin
	@echo "Package: $(PACKAGE_NAME)" > $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/DEBIAN/control
	@echo "Version: $(VERSION)" >> $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/DEBIAN/control
	@echo "Architecture: $(ARCHITECTURE)" >> $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/DEBIAN/control
	@echo "Maintainer: $(MAINTAINER)" >> $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/DEBIAN/control
	@echo "Description: $(DESCRIPTION)" >> $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/DEBIAN/control
	@echo "Depends: python3, python3-pip" >> $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/DEBIAN/control
	@cp -r pythonium $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/usr/local/lib/python3/dist-packages/
	@echo '#!/bin/bash' > $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/usr/local/bin/pythonium
	@echo 'python3 -m pythonium "$$@"' >> $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/usr/local/bin/pythonium
	@chmod +x $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE)/usr/local/bin/pythonium
	dpkg-deb --build $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(ARCHITECTURE) $(BUILD_DIR)/$(DEB_FILE)

# Alternative native RPM package build
.PHONY: rpm-native
rpm-native: clean
	@echo "Building native RPM package..."
	@mkdir -p $(BUILD_DIR)/rpm/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
	@mkdir -p $(BUILD_DIR)/rpm/SOURCES/$(PACKAGE_NAME)-$(VERSION)
	@cp -r . $(BUILD_DIR)/rpm/SOURCES/$(PACKAGE_NAME)-$(VERSION)/
	@cd $(BUILD_DIR)/rpm/SOURCES && tar -czf $(PACKAGE_NAME)-$(VERSION).tar.gz $(PACKAGE_NAME)-$(VERSION)
	@echo "Name: $(PACKAGE_NAME)" > $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "Version: $(VERSION)" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "Release: 1" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "Summary: $(DESCRIPTION)" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "License: MIT" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "Source0: %{name}-%{version}.tar.gz" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "BuildArch: noarch" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "Requires: python3, python3-pip" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "%description" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "$(DESCRIPTION)" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "%prep" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "%setup -q" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "%build" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "python3 setup.py build" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "%install" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "python3 setup.py install --root=%{buildroot}" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "%files" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "/usr/local/lib/python*/site-packages/$(PACKAGE_NAME)*" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@echo "/usr/local/bin/pythonium" >> $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	rpmbuild --define "_topdir $(PWD)/$(BUILD_DIR)/rpm" -bb $(BUILD_DIR)/rpm/SPECS/$(PACKAGE_NAME).spec
	@cp $(BUILD_DIR)/rpm/RPMS/noarch/$(PACKAGE_NAME)-$(VERSION)-1.noarch.rpm $(BUILD_DIR)/$(RPM_FILE)

# Install packaging tools
.PHONY: install-packaging-tools
install-packaging-tools:
	@echo "Installing packaging tools..."
	sudo apt-get update
	sudo apt-get install -y ruby ruby-dev rubygems build-essential rpm
	sudo gem install --no-document fpm

# Install the built package (requires sudo)
.PHONY: install-deb
install-deb: deb
	@echo "Installing Debian package..."
	sudo dpkg -i $(BUILD_DIR)/$(DEB_FILE)
	sudo apt-get install -f

# Install RPM package (requires sudo)
.PHONY: install-rpm
install-rpm: rpm
	@echo "Installing RPM package..."
	sudo rpm -i $(BUILD_DIR)/$(RPM_FILE)

# Install package based on system
.PHONY: install
install:
	@if command -v dpkg >/dev/null 2>&1; then \
		$(MAKE) install-deb; \
	elif command -v rpm >/dev/null 2>&1; then \
		$(MAKE) install-rpm; \
	else \
		echo "No supported package manager found (dpkg or rpm)"; \
		exit 1; \
	fi

# Remove the installed package
.PHONY: uninstall
uninstall:
	@if command -v dpkg >/dev/null 2>&1; then \
		echo "Removing Debian package..."; \
		sudo dpkg -r $(PACKAGE_NAME); \
	elif command -v rpm >/dev/null 2>&1; then \
		echo "Removing RPM package..."; \
		sudo rpm -e $(PACKAGE_NAME); \
	else \
		echo "No supported package manager found (dpkg or rpm)"; \
		exit 1; \
	fi

# Test the packages without installing
.PHONY: test-deb
test-deb: deb
	@echo "Testing DEB package integrity..."
	dpkg-deb --info $(BUILD_DIR)/$(DEB_FILE)
	dpkg-deb --contents $(BUILD_DIR)/$(DEB_FILE)
	dpkg-deb --verify $(BUILD_DIR)/$(DEB_FILE)

.PHONY: test-rpm
test-rpm: rpm
	@echo "Testing RPM package integrity..."
	rpm -qip $(BUILD_DIR)/$(RPM_FILE)
	rpm -qlp $(BUILD_DIR)/$(RPM_FILE)

.PHONY: test-packages
test-packages: test-deb test-rpm
	@echo "All package tests completed"
