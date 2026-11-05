package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestDiscover(t *testing.T) {
	cases := []struct {
		name, group, result, rpcError string
		wantError                     bool
	}{
		{name: "groups", result: `{"content":[{"type":"text","text":"{\"version\":1,\"groups\":[{\"name\":\"mail\",\"count\":2}]}"}]}`},
		{name: "group tools", group: "mail", result: `{"content":[{"type":"text","text":"{\"version\":1,\"group\":\"mail\",\"tools\":[{\"name\":\"mail_read\",\"description\":\"Read\"}]}"}]}`},
		{name: "legacy tool without separator", group: "mail", result: `{"content":[{"type":"text","text":"{\"version\":1,\"group\":\"mail\",\"tools\":[{\"name\":\"mail\",\"description\":\"Read\"}]}"}]}`},
		{name: "empty groups", result: `{"content":[{"type":"text","text":"{\"version\":1,\"groups\":[]}"}]}`},
		{name: "unknown group", group: "missing", result: `{"isError":true,"content":[{"type":"text","text":"unknown group"}]}`, wantError: true},
		{name: "unavailable", rpcError: `{"code":-32601,"message":"unknown tool"}`, wantError: true},
		{name: "missing content", result: `{}`, wantError: true},
		{name: "bad json", result: `{"content":[{"type":"text","text":"bad"}]}`, wantError: true},
		{name: "wrong version", result: `{"content":[{"type":"text","text":"{\"version\":2,\"groups\":[]}"}]}`, wantError: true},
		{name: "missing count", result: `{"content":[{"type":"text","text":"{\"version\":1,\"groups\":[{\"name\":\"mail\"}]}"}]}`, wantError: true},
		{name: "null groups", result: `{"content":[{"type":"text","text":"{\"version\":1,\"groups\":null}"}]}`, wantError: true},
		{name: "wrong group", group: "mail", result: `{"content":[{"type":"text","text":"{\"version\":1,\"group\":\"other\",\"tools\":[]}"}]}`, wantError: true},
		{name: "empty tools", group: "mail", result: `{"content":[{"type":"text","text":"{\"version\":1,\"group\":\"mail\",\"tools\":[]}"}]}`, wantError: true},
		{name: "wrong tool prefix", group: "mail", result: `{"content":[{"type":"text","text":"{\"version\":1,\"group\":\"mail\",\"tools\":[{\"name\":\"other_read\",\"description\":\"Read\"}]}"}]}`, wantError: true},
		{name: "missing description", group: "mail", result: `{"content":[{"type":"text","text":"{\"version\":1,\"group\":\"mail\",\"tools\":[{\"name\":\"mail_read\"}]}"}]}`, wantError: true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				var req struct {
					Method string `json:"method"`
					Params struct {
						Name      string         `json:"name"`
						Arguments map[string]any `json:"arguments"`
					} `json:"params"`
				}
				if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
					t.Error(err)
					return
				}
				switch req.Method {
				case "initialize":
					fmt.Fprint(w, `{"jsonrpc":"2.0","id":1,"result":{}}`)
				case "notifications/initialized":
					w.WriteHeader(http.StatusAccepted)
				case "tools/call":
					operation := "groups"
					if tc.group != "" {
						operation = "tools"
					}
					if req.Params.Name != "broker_discover" || req.Params.Arguments["operation"] != operation || (tc.group != "" && req.Params.Arguments["group"] != tc.group) {
						t.Errorf("unexpected request: %+v", req.Params)
					}
					if tc.rpcError != "" {
						fmt.Fprintf(w, `{"jsonrpc":"2.0","id":2,"error":%s}`, tc.rpcError)
					} else {
						fmt.Fprintf(w, `{"jsonrpc":"2.0","id":2,"result":%s}`, tc.result)
					}
				default:
					t.Errorf("unexpected method %s", req.Method)
				}
			}))
			defer server.Close()
			c := &Client{baseURL: server.URL, token: "test", httpClient: server.Client()}
			got, err := c.Discover(tc.group)
			if (err != nil) != tc.wantError {
				t.Fatalf("Discover() = %s, %v", got, err)
			}
			if err != nil && !strings.Contains(err.Error(), "discovery") {
				t.Fatalf("unclear error: %v", err)
			}
		})
	}
}
