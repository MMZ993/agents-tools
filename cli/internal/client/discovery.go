package client

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

var groupName = regexp.MustCompile(`^[a-z][a-z0-9]*$`)

// Discover returns the versioned, principal-filtered discovery payload.
func (c *Client) Discover(group string) (json.RawMessage, error) {
	args := map[string]any{"operation": "groups"}
	if group != "" {
		args["operation"] = "tools"
		args["group"] = group
	}
	result, err := c.CallTool("broker_discover", args)
	if err != nil {
		return nil, fmt.Errorf("broker discovery unavailable or unauthorized: %w", err)
	}
	var envelope struct {
		Content []struct {
			Type string  `json:"type"`
			Text *string `json:"text"`
		} `json:"content"`
	}
	if err := json.Unmarshal(result.JSON(), &envelope); err != nil {
		return nil, fmt.Errorf("malformed broker discovery response: %w", err)
	}
	if result.IsError {
		if len(envelope.Content) > 0 && envelope.Content[0].Text != nil {
			return nil, fmt.Errorf("broker discovery failed: %s", *envelope.Content[0].Text)
		}
		return nil, fmt.Errorf("broker discovery failed or is unauthorized")
	}
	if len(envelope.Content) != 1 || envelope.Content[0].Type != "text" || envelope.Content[0].Text == nil {
		return nil, fmt.Errorf("malformed broker discovery response: expected one text item")
	}
	raw := json.RawMessage(*envelope.Content[0].Text)
	var payload struct {
		Version *int            `json:"version"`
		Group   *string         `json:"group"`
		Groups  json.RawMessage `json:"groups"`
		Tools   json.RawMessage `json:"tools"`
	}
	if err := json.Unmarshal(raw, &payload); err != nil || payload.Version == nil || *payload.Version != 1 {
		return nil, fmt.Errorf("malformed broker discovery response: invalid version or JSON")
	}
	if group == "" {
		var entries []struct {
			Name  *string `json:"name"`
			Count *int    `json:"count"`
		}
		if string(payload.Groups) == "null" || json.Unmarshal(payload.Groups, &entries) != nil || entries == nil {
			return nil, fmt.Errorf("malformed broker discovery response: invalid groups")
		}
		for _, entry := range entries {
			if entry.Name == nil || !groupName.MatchString(*entry.Name) || entry.Count == nil || *entry.Count <= 0 {
				return nil, fmt.Errorf("malformed broker discovery response: invalid group entry")
			}
		}
	} else {
		var entries []struct {
			Name        *string `json:"name"`
			Description *string `json:"description"`
		}
		if payload.Group == nil || *payload.Group != group || string(payload.Tools) == "null" || json.Unmarshal(payload.Tools, &entries) != nil || len(entries) == 0 {
			return nil, fmt.Errorf("malformed broker discovery response: invalid tools or group")
		}
		for _, entry := range entries {
			if entry.Name == nil || (*entry.Name != group && (!strings.HasPrefix(*entry.Name, group+"_") || len(*entry.Name) == len(group)+1)) || entry.Description == nil {
				return nil, fmt.Errorf("malformed broker discovery response: invalid tool entry")
			}
		}
	}
	return raw, nil
}
