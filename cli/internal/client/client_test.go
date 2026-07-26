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
