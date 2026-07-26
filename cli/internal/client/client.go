package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"time"
)

const (
	defaultBaseURL  = "https://agents-tools.mmz.sh"
	protocolVersion = "2025-06-18"
	acceptHeader    = "application/json, text/event-stream"
	clientName      = "agents-tools-cli"
	clientVersion   = "0.1.0"
)

// Client is the MCP streamable-HTTP client for the agents-tools broker.
type Client struct {
	baseURL    string
	token      string
	httpClient *http.Client
	sessionID  string
	nextID     int64
}

// New creates a Client from environment variables.
// AGENTS_TOOLS_MCP_ADMIN_TOKEN is required for MCP operations.
// AGENTS_TOOLS_URL and AGENTS_TOOLS_TIMEOUT are optional.
func New() (*Client, error) {
	baseURL := os.Getenv("AGENTS_TOOLS_URL")
	if baseURL == "" {
		baseURL = defaultBaseURL
	}

	timeout := 30 * time.Second
	if s := os.Getenv("AGENTS_TOOLS_TIMEOUT"); s != "" {
		secs, err := strconv.Atoi(s)
		if err != nil {
			return nil, fmt.Errorf("AGENTS_TOOLS_TIMEOUT must be an integer: %w", err)
		}
		timeout = time.Duration(secs) * time.Second
	}

	return &Client{
		baseURL: baseURL,
		token:   os.Getenv("AGENTS_TOOLS_MCP_ADMIN_TOKEN"),
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}, nil
}

// APIError represents a non-2xx HTTP response from the broker.
type APIError struct {
	StatusCode int
	Body       string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("API error %d: %s", e.StatusCode, e.Body)
}

// rpcRequest is a JSON-RPC 2.0 request. ID is nil for notifications.
type rpcRequest struct {
	JSONRPC string `json:"jsonrpc"`
	ID      *int64 `json:"id,omitempty"`
	Method  string `json:"method"`
	Params  any    `json:"params,omitempty"`
}

// rpcResponse is the JSON-RPC 2.0 response envelope.
type rpcResponse struct {
	Result json.RawMessage `json:"result,omitempty"`
	Error  *RPCError       `json:"error,omitempty"`
}

// RPCError is a JSON-RPC error.
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func (e *RPCError) Error() string {
	return fmt.Sprintf("JSON-RPC error %d: %s", e.Code, e.Message)
}

// post sends a JSON-RPC payload to /mcp/ and returns the raw body and headers.
// It applies auth, protocol version, and session headers.
func (c *Client) post(req rpcRequest) (json.RawMessage, http.Header, error) {
	b, err := json.Marshal(req)
	if err != nil {
		return nil, nil, fmt.Errorf("marshal request: %w", err)
	}

	httpReq, err := http.NewRequest(http.MethodPost, c.baseURL+"/mcp/", bytes.NewReader(b))
	if err != nil {
		return nil, nil, fmt.Errorf("build request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", acceptHeader)
	httpReq.Header.Set("MCP-Protocol-Version", protocolVersion)
	if c.token != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.token)
	}
	if c.sessionID != "" {
		httpReq.Header.Set("Mcp-Session-Id", c.sessionID)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, resp.Header, &APIError{StatusCode: resp.StatusCode, Body: string(body)}
	}

	return body, resp.Header, nil
}

// call sends a JSON-RPC request (with id) and decodes the result.
func (c *Client) call(method string, params any) (json.RawMessage, error) {
	id := c.nextID
	c.nextID++
	body, _, err := c.post(rpcRequest{JSONRPC: "2.0", ID: &id, Method: method, Params: params})
	if err != nil {
		return nil, err
	}

	var rpc rpcResponse
	if len(body) > 0 {
		if err := json.Unmarshal(body, &rpc); err != nil {
			return nil, fmt.Errorf("decode response: %w", err)
		}
	}
	if rpc.Error != nil {
		return nil, rpc.Error
	}
	return rpc.Result, nil
}

// notify sends a JSON-RPC notification (no id); the broker replies 202 with no body.
func (c *Client) notify(method string) error {
	_, _, err := c.post(rpcRequest{JSONRPC: "2.0", Method: method})
	return err
}

// initSession performs the MCP initialize handshake and stores the session id.
// It must run before any tools/list or tools/call request.
func (c *Client) initSession() error {
	if c.token == "" {
		return fmt.Errorf("AGENTS_TOOLS_MCP_ADMIN_TOKEN is required")
	}
	// Fresh id sequence per invocation.
	c.nextID = 1
	id := c.nextID
	c.nextID++

	body, hdr, err := c.post(rpcRequest{
		JSONRPC: "2.0",
		ID:      &id,
		Method:  "initialize",
		Params: map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{},
			"clientInfo": map[string]any{
				"name":    clientName,
				"version": clientVersion,
			},
		},
	})
	if err != nil {
		return err
	}

	var initResp rpcResponse
	if len(body) > 0 {
		if err := json.Unmarshal(body, &initResp); err != nil {
			return fmt.Errorf("decode initialize response: %w", err)
		}
	}
	if initResp.Error != nil {
		return initResp.Error
	}

	if sid := hdr.Get("Mcp-Session-Id"); sid != "" {
		c.sessionID = sid
	}

	if err := c.notify("notifications/initialized"); err != nil {
		return fmt.Errorf("send initialized notification: %w", err)
	}
	return nil
}

// Tool is one tool returned by tools/list.
type Tool struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"inputSchema"`
}

// ListTools discovers the tools available to the authenticated principal.
func (c *Client) ListTools() ([]Tool, error) {
	if err := c.initSession(); err != nil {
		return nil, err
	}
	result, err := c.call("tools/list", map[string]any{})
	if err != nil {
		return nil, err
	}
	var resp struct {
		Tools []Tool `json:"tools"`
	}
	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, fmt.Errorf("decode tools: %w", err)
	}
	return resp.Tools, nil
}

// GetTool returns the tool with the given name. The broker exposes no per-tool
// fetch, so this lists and matches client-side.
func (c *Client) GetTool(name string) (*Tool, error) {
	tools, err := c.ListTools()
	if err != nil {
		return nil, err
	}
	for i := range tools {
		if tools[i].Name == name {
			return &tools[i], nil
		}
	}
	return nil, fmt.Errorf("tool %q not found", name)
}

// CallToolResult is the MCP result of a tools/call invocation.
type CallToolResult struct {
	Content []Content `json:"content"`
	IsError bool      `json:"isError"`
}

// Content is one content item in a tool result.
type Content struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// CallTool invokes a tool by name with the given arguments.
func (c *Client) CallTool(name string, args map[string]any) (*CallToolResult, error) {
	if err := c.initSession(); err != nil {
		return nil, err
	}
	result, err := c.call("tools/call", map[string]any{
		"name":      name,
		"arguments": args,
	})
	if err != nil {
		return nil, err
	}
	var out CallToolResult
	if err := json.Unmarshal(result, &out); err != nil {
		return nil, fmt.Errorf("decode tool result: %w", err)
	}
	return &out, nil
}

// Health calls GET /healthz (unauthenticated, no MCP session).
func (c *Client) Health() (string, error) {
	httpReq, err := http.NewRequest(http.MethodGet, c.baseURL+"/healthz", nil)
	if err != nil {
		return "", fmt.Errorf("build request: %w", err)
	}
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return "", fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read response: %w", err)
	}
	if resp.StatusCode >= 400 {
		return "", &APIError{StatusCode: resp.StatusCode, Body: string(body)}
	}
	return string(body), nil
}
