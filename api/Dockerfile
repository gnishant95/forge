# Forge API Dockerfile

FROM golang:1.21-alpine AS builder

WORKDIR /build

# Install dependencies
RUN apk add --no-cache git

# Copy go mod files first
COPY go.mod ./
# Download dependencies (go.sum will be generated)
RUN go mod download || true

# Copy source
COPY . .

# Tidy modules (ensures go.sum is correct)
RUN go mod tidy

# Generate proto files (if buf is available)
# RUN go install github.com/bufbuild/buf/cmd/buf@latest && buf generate

# Build
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o forge ./cmd/forge

# Final image
FROM alpine:3.19

WORKDIR /app

RUN apk add --no-cache ca-certificates curl

COPY --from=builder /build/forge .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

CMD ["./forge"]

