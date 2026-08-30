.PHONY: test install editable compile clean

test:
	python3 run_tests.py

compile:
	python3 -m compileall -q src/abi_kgb

install:
	python3 -m pip install .

editable:
	python3 -m pip install -e .

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info
