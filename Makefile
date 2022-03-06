# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
# 
# SPDX-License-Identifier: GPL-3.0-or-later

# virtualenv environment.
VENV?=.venv
ifeq ($(OS), Windows_NT)
	BIN?=$(VENV)\Scripts
else
	BIN?=$(VENV)/bin
endif
PYTHON?=$(BIN)/python
PIP?=$(BIN)/pip
PYTEST?=$(BIN)/pytest

ifeq ($(OS), Windows_NT)
define delete_dir
	if exist $(1) rmdir /Q /s $(1)
endef
else
define delete_dir
	rm -fr $(1)
endef
endif

ifeq ($(OS), Windows_NT)
define activate
	$(BIN)\activate
endef
else
define activate
	. $(BIN)/activate
endef
endif

.PHONY: default
default: install
	$(PYTEST) tests/

.PHONY: venv
venv:
	pip install virtualenv
ifeq ($(OS), Windows_NT)
	if NOT exist $(VENV) virtualenv $(VENV)
else
	[ -d $(VENV) ] || virtualenv $(VENV)
endif
	$(PIP) install -r requirements.txt
	make install

.PHONY: clean
clean:
	python setup.py clean
	$(call delete_dir,build)
	$(call delete_dir,dist)
	$(call delete_dir,.venv)

.PHONY: install
install:
	$(PYTHON) setup.py install
	$(PYTHON) setup.py install_scripts
