FROM golang:1.24-alpine3.21 as builder
LABEL authors="ravi.rana@cloudkeeper.com"
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o bootcamp cmd/api/main.go

FROM alpine:3.21
RUN apk --no-cache add ca-certificates tzdata
WORKDIR /app
COPY --from=builder /app/bootcamp .
COPY --from=builder /app/templates ./templates
RUN adduser -D appuser
USER appuser
EXPOSE 8080
CMD ["./bootcamp"]