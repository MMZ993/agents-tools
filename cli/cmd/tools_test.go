package cmd

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

func TestToolsListDefaultsToGroupDiscovery(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var request struct {
			Method string `json:"method"`
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Error(err)
			return
		}
		switch request.Method {
		case "initialize":
			_, _ = io.WriteString(w, `{"jsonrpc":"2.0","id":1,"result":{}}`)
		case "notifications/initialized":
			w.WriteHeader(http.StatusAccepted)
		case "tools/list":
			_, _ = io.WriteString(w, `{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}`)
		case "tools/call":
			_, _ = io.WriteString(w, `{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{\"version\":1,\"groups\":[{\"name\":\"mail\",\"count\":2}]}"}]}}`)
		}
	}))
	defer server.Close()
	t.Setenv("AGENTS_TOOLS_URL", server.URL)
	t.Setenv("AGENTS_TOOLS_MCP_ADMIN_TOKEN", "test")
	old := os.Stdout
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	os.Stdout = w
	defer func() { os.Stdout = old }()
	toolsListCmd.Run(toolsListCmd, nil)
	_ = w.Close()
	output, err := io.ReadAll(r)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(output), `"name":"mail"`) {
		t.Fatalf("output = %s, want discovered group", output)
	}
}

func TestToolsListGroupAndAll(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var request struct {
			Method string `json:"method"`
			Params struct {
				Name      string         `json:"name"`
				Arguments map[string]any `json:"arguments"`
			} `json:"params"`
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Error(err)
			return
		}
		switch request.Method {
		case "initialize":
			_, _ = io.WriteString(w, `{"jsonrpc":"2.0","id":1,"result":{}}`)
		case "notifications/initialized":
			w.WriteHeader(http.StatusAccepted)
		case "tools/list":
			_, _ = io.WriteString(w, `{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"mail_read","inputSchema":{"type":"object"},"x-extra":true}]}}`)
		case "tools/call":
			if request.Params.Name != "broker_discover" || request.Params.Arguments["operation"] != "tools" || request.Params.Arguments["group"] != "mail" {
				t.Errorf("unexpected discovery request: %+v", request.Params)
			}
			_, _ = io.WriteString(w, `{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{\"version\":1,\"group\":\"mail\",\"tools\":[{\"name\":\"mail_read\",\"description\":\"Read\"}]}"}]}}`)
		default:
			t.Errorf("unexpected method %s", request.Method)
		}
	}))
	defer server.Close()
	t.Setenv("AGENTS_TOOLS_URL", server.URL)
	t.Setenv("AGENTS_TOOLS_MCP_ADMIN_TOKEN", "test")
	for _, tc := range []struct {
		name, group string
		all         bool
		want        string
	}{
		{"group", "mail", false, `{"version":1,"group":"mail","tools":[{"name":"mail_read","description":"Read"}]}`},
		{"all", "", true, `[{"name":"mail_read","inputSchema":{"type":"object"},"x-extra":true}]`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			listGroup, listAll = tc.group, tc.all
			defer func() { listGroup, listAll = "", false }()
			old := os.Stdout
			r, w, err := os.Pipe()
			if err != nil {
				t.Fatal(err)
			}
			os.Stdout = w
			defer func() { os.Stdout = old }()
			toolsListCmd.Run(toolsListCmd, nil)
			_ = w.Close()
			output, err := io.ReadAll(r)
			if err != nil {
				t.Fatal(err)
			}
			if strings.TrimSpace(string(output)) != tc.want {
				t.Fatalf("output = %s, want %s", output, tc.want)
			}
		})
	}
}

func TestBuildArgumentsRejectsJSONNull(t *testing.T) {
	_, err := buildArguments("null", nil)
	if err == nil || !strings.Contains(err.Error(), "JSON object") {
		t.Fatalf("buildArguments(\"null\") error = %v, want JSON object validation error", err)
	}
}
