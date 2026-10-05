# build context is the repository root (the .proto lives in simulation/grpc)
FROM golang:1.22-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends protobuf-compiler && rm -rf /var/lib/apt/lists/*
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.34.2 && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.4.0
ENV PATH="$PATH:/go/bin"
WORKDIR /src/server
COPY simulation/grpc/sim.proto /src/simulation/grpc/sim.proto
COPY server/ .
RUN protoc -I /src/simulation/grpc --go_out=internal/simpb --go_opt=paths=source_relative \
    --go-grpc_out=internal/simpb --go-grpc_opt=paths=source_relative /src/simulation/grpc/sim.proto
RUN go mod tidy && go vet ./... && go test ./... && CGO_ENABLED=0 go build -o /out/server ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=build /out/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
