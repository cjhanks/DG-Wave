VIRTUAL_ENV=${PWD}/venv

virtualenv:
	python3 -m venv ${VIRTUAL_ENV}

.ONESHELL:
deps:
	. ${VIRTUAL_ENV}/bin/activate
	pip3 install -r requirements.txt
