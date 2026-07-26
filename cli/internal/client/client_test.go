package client

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestCallToolPreservesAllMCPResultContent(t *testing.T) {
	const toolResult = `{"content":[{"type":"image","data":"aGVsbG8=","mimeType":"text/plain"},{"type":"resource_link","uri":"https://example.test/attachment","name":"attachment.txt","mimeType":"text/plain"}],"structuredContent":{"attachmentCount":2},"isError":false}`

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var request struct {
			Method string `json:"method"`
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Fatalf("decode request: %v", err)
		}
		switch request.Method {
		case "initialize":
			w.Header().Set("Mcp-Session-Id", "test-session")
			_, _ = w.Write([]byte(`{"jsonrpc":"2.0","id":1,"result":{}}`))
		case "notifications/initialized":
			w.WriteHeader(http.StatusAccepted)
		case "tools/call":
			_, _ = w.Write([]byte(`{"jsonrpc":"2.0","id":2,"result":` + toolResult + `}`))
		default:
			t.Fatalf("unexpected MCP method %q", request.Method)
		}
	}))
	defer server.Close()

	c := &Client{baseURL: server.URL, token: "test-token", httpClient: server.Client()}
	result, err := c.CallTool("mail_read_attachment", map[string]any{})
	if err != nil {
		t.Fatalf("CallTool() error = %v", err)
	}

	got, err := json.Marshal(result)
	if err != nil {
		t.Fatalf("marshal result: %v", err)
	}
	if string(got) != toolResult {
		t.Fatalf("CallTool() result = %s, want %s", got, toolResult)
	}
}

func TestPostRejectsNon2xxResponse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Location", "/redirected")
		w.WriteHeader(http.StatusFound)
	}))
	defer server.Close()

	c := &Client{
		baseURL: server.URL,
		httpClient: &http.Client{
			CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
				return http.ErrUseLastResponse
			},
		},
	}

	_, _, err := c.post(rpcRequest{JSONRPC: "2.0", Method: "tools/list"})
	apiErr, ok := err.(*APIError)
	if !ok || apiErr.StatusCode != http.StatusFound {
		t.Fatalf("post() error = %v, want API error with status %d", err, http.StatusFound)
	}
}

func TestHealthRejectsNon2xxResponse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Location", "/redirected")
		w.WriteHeader(http.StatusFound)
	}))
	defer server.Close()

	c := &Client{
		baseURL: server.URL,
		httpClient: &http.Client{
			CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
				return http.ErrUseLastResponse
			},
		},
	}

	_, err := c.Health()
	apiErr, ok := err.(*APIError)
	if !ok || apiErr.StatusCode != http.StatusFound {
		t.Fatalf("Health() error = %v, want API error with status %d", err, http.StatusFound)
	}
}

func TestNewNormalizesTrailingSlashInBaseURL(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/healthz" {
			t.Fatalf("request path = %q, want /healthz", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	}))
	defer server.Close()

	t.Setenv("AGENTS_TOOLS_URL", server.URL+"/")
	client, err := New()
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}
	if _, err := client.Health(); err != nil {
		t.Fatalf("Health() error = %v", err)
	}
}

func TestNewRejectsNonPositiveTimeout(t *testing.T) {
	for _, value := range []string{"0", "-1"} {
		t.Run(value, func(t *testing.T) {
			t.Setenv("AGENTS_TOOLS_TIMEOUT", value)

			_, err := New()
			if err == nil || !strings.Contains(err.Error(), "positive integer") {
				t.Fatalf("New() error = %v, want positive integer validation error", err)
			}
		})
	}
}
