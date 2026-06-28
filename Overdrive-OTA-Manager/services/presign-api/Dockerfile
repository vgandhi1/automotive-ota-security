FROM golang:1.22-alpine AS build
WORKDIR /src
RUN apk add --no-cache ca-certificates
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /presign-api .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /presign-api /usr/local/bin/presign-api
USER nobody:nobody
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/presign-api"]
