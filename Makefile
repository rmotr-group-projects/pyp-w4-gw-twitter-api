.PHONY: test test-cov

TAG="\n\n\033[0;32m\#\#\# "
END=" \#\#\# \033[0m\n"

test:
	@echo $(TAG)Running tests$(END)
	PYTHONPATH=. py.test -s tests -vv --tb=no

test-verbose:
	@echo $(TAG)Running tests$(END)
	PYTHONPATH=. py.test -s tests -vv

test-cov:
	@echo $(TAG)Running tests with coverage$(END)
	PYTHONPATH=. py.test --cov=twitter_api tests

coverage:
	@echo $(TAG)Coverage report$(END)
	@PYTHONPATH=. coverage run --source=twitter_api $(shell which py.test) ./tests -q --tb=no >/dev/null; true
	@coverage report
