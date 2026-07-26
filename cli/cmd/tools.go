package cmd

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"agents-tools-cli/internal/client"
	"github.com/spf13/cobra"
)

var toolsCmd = &cobra.Command{
	Use:   "tools",
	Short: "List and call MCP tools",
}

// ---------- list ----------

var toolsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List tools available to the authenticated principal",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		tools, err := c.ListTools()
		if err != nil {
			fatal("%v", err)
		}
		printJSON(tools)
	},
}

// ---------- call ----------

var (
	callArgsFlags []string
	callJSON      string
)

var toolsCallCmd = &cobra.Command{
	Use:   "call <name>",
	Short: "Call a tool by name",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		arguments, err := buildArguments(callJSON, callArgsFlags)
		if err != nil {
			fatal("%v", err)
		}
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		result, err := c.CallTool(args[0], arguments)
		if err != nil {
			fatal("%v", err)
		}
		printCallResult(result)
		if result.IsError {
			exitFn(1)
		}
	},
}

// buildArguments merges --json and repeated --arg flags into one arguments map.
// --json is applied first, then --arg overrides on top.
func buildArguments(jsonStr string, argFlags []string) (map[string]any, error) {
	args := map[string]any{}
	if jsonStr != "" {
		if err := json.Unmarshal([]byte(jsonStr), &args); err != nil || args == nil {
			if err != nil {
				return nil, fmt.Errorf("--json must be a JSON object: %w", err)
			}
			return nil, fmt.Errorf("--json must be a JSON object")
		}
	}
	for _, kv := range argFlags {
		idx := strings.IndexByte(kv, '=')
		if idx < 0 {
			return nil, fmt.Errorf("--arg expects key=value, got %q", kv)
		}
		key := kv[:idx]
		if key == "" {
			return nil, fmt.Errorf("--arg key is empty in %q", kv)
		}
		args[key] = coerceArg(kv[idx+1:])
	}
	return args, nil
}

// coerceArg parses a CLI string into a JSON-typed value:
// "true"/"false" → bool, integers → int, everything else → string.
func coerceArg(v string) any {
	if v == "true" {
		return true
	}
	if v == "false" {
		return false
	}
	if i, err := strconv.Atoi(v); err == nil {
		return i
	}
	return v
}

// printCallResult writes the complete MCP result without dropping content types
// or extension fields.
func printCallResult(r *client.CallToolResult) {
	printRawJSON(r.JSON())
}

var toolsSchemaCmd = &cobra.Command{
	Use:   "schema <name>",
	Short: "Print a tool's input schema (how to call it)",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		tool, err := c.GetTool(args[0])
		if err != nil {
			fatal("%v", err)
		}
		printRawJSON(tool.InputSchema)
	},
}

func init() {
	toolsCallCmd.Flags().StringSliceVar(&callArgsFlags, "arg", nil, "key=value argument (repeatable; coerced to bool/int/string)")
	toolsCallCmd.Flags().StringVar(&callJSON, "json", "", "JSON object of arguments (applied before --arg overrides)")

	toolsCmd.AddCommand(toolsListCmd, toolsCallCmd, toolsSchemaCmd)
}
