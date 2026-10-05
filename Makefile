.PHONY: test test-sim test-go bench proto proto-py proto-go dev-sim dev-server dev-client

test: test-sim test-go
test-sim:
	python3 -m unittest discover -s simulation/tests -t .
test-go: proto-go
	cd server && go mod tidy && go test ./...
bench:
	python3 -m simulation.benchmark 100 500 1000

proto: proto-py proto-go
proto-py:
	python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. simulation/grpc/sim.proto
proto-go:
	protoc -I simulation/grpc --go_out=server/internal/simpb --go_opt=paths=source_relative \
	  --go-grpc_out=server/internal/simpb --go-grpc_opt=paths=source_relative simulation/grpc/sim.proto

# local development without Docker (three terminals)
dev-sim: proto-py
	python3 -m simulation.main
dev-server: proto-go
	cd server && go mod tidy && SIM_ADDR=localhost:50051 go run ./cmd/server
dev-client:
	cd client && npm install && npm run dev
