.PHONY: setup run test clean

setup:   ## create a virtual environment and install dependencies
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run:     ## download the NHS files (first run only), check them and build the outputs
	python run_pipeline.py

test:    ## run the tests (no internet needed)
	pytest -q

clean:
	rm -f data/*.duckdb
