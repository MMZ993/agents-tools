BINARY   := agents-tools
DIST     := dist

.PHONY: build build-all test clean

build:
	CGO_ENABLED=0 go build -o $(DIST)/$(BINARY) .

build-all:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o $(DIST)/$(BINARY)-linux-amd64 .
	CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o $(DIST)/$(BINARY)-linux-arm64 .

test:
	go test ./...

clean:
	rm -rf $(DIST)
