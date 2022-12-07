REGISTRY=docker.io
BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
export VERSION=$(shell git rev-parse --short=7 HEAD)
VERBOSE?=
PROJECT=haifa-tree-felling-permits
REPOSITORY=tomersha/$(PROJECT)
DOCKER_BUILD_ARGS=--pull
BUILD_DIR=$(shell pwd)/build

.PHONY: all
all: ci_build build lint

.PHONY: clean
clean:
	@rm -fr $(BUILD_DIR) *.tmp
	@find -name "*.pyc" -delete

.PHONY: login
login:
	@/bin/bash -c 'source .env && docker login --username $$DOCKERHUB_USERNAME --password $$DOCKERHUB_TOKEN'

.PHONY: verify_clean
verify_clean:
	@git diff-index --quiet HEAD || (echo "git repo must be clean!" && exit 1)

.PHONY: build
build:
	@docker build $(DOCKER_BUILD_ARGS) -t $(REPOSITORY):$(VERSION) -f Dockerfile .
	@docker tag $(REPOSITORY):$(VERSION) $(REPOSITORY):latest
	@docker tag $(REPOSITORY):$(VERSION) $(REGISTRY)/$(REPOSITORY):latest
	@docker tag $(REPOSITORY):$(VERSION) $(REGISTRY)/$(REPOSITORY):$(VERSION)
	@docker tag $(REPOSITORY):$(VERSION) $(REGISTRY)/$(REPOSITORY):$(BRANCH)

.PHONY: submit
submit: verify_clean
	@docker push $(REGISTRY)/$(REPOSITORY):latest
	@docker push $(REGISTRY)/$(REPOSITORY):$(VERSION)
	@docker push $(REGISTRY)/$(REPOSITORY):$(BRANCH)

.PHONY: lint
lint: pycodestyle pylint

.PHONY: pycodestyle
pycodestyle: ci_build
	@docker run --rm -v $(PWD)/src:/code -v $(PWD)/conf:/conf $(PROJECT)-ci \
		pycodestyle /code \
		--show-source --config=/conf/pycodestyle.cfg $(if $(VERBOSE),-v)

.PHONY: pylint
pylint: ci_build
	@docker run --rm -v $(PWD)/src:/code -v $(PWD)/conf:/conf $(PROJECT)-ci \
		pylint --rcfile=/conf/pylint.cfg /code

.PHONY: ci_build
ci_build:
	@docker build $(DOCKER_BUILD_ARGS) -t $(PROJECT)-ci -f Dockerfile.ci .
