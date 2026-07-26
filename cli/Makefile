BINARY   := agents-tools
DIST     := dist

.PHONY: build build-all test clean

build:
	go build -o $(DIST)/$(BINARY) .

build-all:
	GOOS=linux GOARCH=amd64 go build -o $(DIST)/$(BINARY)-linux-amd64 .
	GOOS=linux GOARCH=arm64 go build -o $(DIST)/$(BINARY)-linux-arm64 .

test:
	go test ./...

clean:
	rm -rf $(DIST)
