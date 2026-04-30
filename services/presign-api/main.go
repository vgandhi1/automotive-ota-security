package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	_ "github.com/overdrive-ota/presign-api/metrics" // register OTA metrics
)

// objectKeyPattern: strict allowlist-style key inside the firmware bucket (no traversal).
var objectKeyPattern = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9/._-]{0,511}$`)

type presignRequest struct {
	ObjectKey string `json:"object_key"`
}

type presignResponse struct {
	URL       string `json:"url"`
	ExpiresIn int    `json:"expires_in_seconds"`
	ObjectKey string `json:"object_key"`
	Bucket    string `json:"bucket"`
}

func main() {
	addr := getenv("PRESIGN_API_ADDR", ":8080")
	endpoint := os.Getenv("S3_ENDPOINT")
	region := getenv("S3_REGION", "us-east-1")
	bucket := os.Getenv("S3_BUCKET")
	accessKey := os.Getenv("S3_ACCESS_KEY")
	secretKey := os.Getenv("S3_SECRET_KEY")
	usePathStyle := strings.EqualFold(os.Getenv("S3_USE_PATH_STYLE"), "true") ||
		os.Getenv("S3_USE_PATH_STYLE") == "1"
	ttlSec, _ := strconv.Atoi(getenv("PRESIGN_TTL_SECONDS", "7200"))
	if ttlSec < 60 || ttlSec > 86400 {
		ttlSec = 7200
	}
	apiKeys := parseAPIKeys(os.Getenv("PRESIGN_API_KEYS"))

	if endpoint == "" || bucket == "" || accessKey == "" || secretKey == "" {
		log.Fatal("missing required env: S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY")
	}
	if len(apiKeys) == 0 {
		log.Fatal("set PRESIGN_API_KEYS to a comma-separated list of server-side API keys")
	}

	client := s3.New(s3.Options{
		Region: region,
		Credentials: aws.NewCredentialsCache(
			credentials.NewStaticCredentialsProvider(accessKey, secretKey, ""),
		),
		BaseEndpoint: aws.String(endpoint),
		UsePathStyle: usePathStyle,
	})
	presigner := s3.NewPresignClient(client)

	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
	mux.HandleFunc("/v1/presign", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !authorize(r, apiKeys) {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		var body presignRequest
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, "invalid json", http.StatusBadRequest)
			return
		}
		key := strings.TrimSpace(body.ObjectKey)
		if !validObjectKey(key) {
			http.Error(w, "invalid object_key", http.StatusBadRequest)
			return
		}
		out, err := presigner.PresignGetObject(r.Context(), &s3.GetObjectInput{
			Bucket: aws.String(bucket),
			Key:    aws.String(key),
		}, func(opts *s3.PresignOptions) {
			opts.Expires = time.Duration(ttlSec) * time.Second
		})
		if err != nil {
			log.Printf("presign failed: %v", err)
			http.Error(w, "presign failed", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(presignResponse{
			URL:       out.URL,
			ExpiresIn: ttlSec,
			ObjectKey: key,
			Bucket:    bucket,
		})
	})

	srv := &http.Server{
		Addr:              addr,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      30 * time.Second,
	}
	log.Printf("presign-api listening on %s", addr)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}

func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func parseAPIKeys(raw string) map[string]struct{} {
	out := make(map[string]struct{})
	for _, p := range strings.Split(raw, ",") {
		k := strings.TrimSpace(p)
		if k != "" {
			out[k] = struct{}{}
		}
	}
	return out
}

func authorize(r *http.Request, keys map[string]struct{}) bool {
	if tok := strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer "); tok != "" {
		_, ok := keys[strings.TrimSpace(tok)]
		return ok
	}
	if k := r.Header.Get("X-API-Key"); k != "" {
		_, ok := keys[strings.TrimSpace(k)]
		return ok
	}
	return false
}

func validObjectKey(key string) bool {
	if key == "" || strings.Contains(key, "..") {
		return false
	}
	if key[0] == '/' || strings.Contains(key, "//") {
		return false
	}
	return objectKeyPattern.MatchString(key)
}
