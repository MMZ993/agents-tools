package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	"github.com/spf13/cobra"
)

var pretty bool
var stderrWriter io.Writer = os.Stderr
var exitFn = os.Exit

var rootCmd = &cobra.Command{
	Use:   "agents-tools",
	Short: "CLI for the agents-tools MCP broker",
}

// Execute runs the root command.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}

func init() {
	rootCmd.PersistentFlags().BoolVarP(&pretty, "pretty", "p", false, "Human-readable output")

	rootCmd.AddCommand(toolsCmd)
	rootCmd.AddCommand(healthCmd)
}

// printJSON writes v as compact JSON to stdout, or pretty if --pretty is set.
func printJSON(v any) {
	b, err := renderJSON(v, pretty)
	if err != nil {
		fatal("encode output: %v", err)
	}
	fmt.Println(string(b))
}

// printRawJSON writes a json.RawMessage to stdout, pretty-printing if --pretty.
func printRawJSON(raw []byte) {
	b, err := renderRawJSON(raw, pretty)
	if err != nil {
		fatal("%v", err)
	}
	fmt.Println(string(b))
}

// fatal writes msg to stderr and exits 1.
func fatal(format string, args ...any) {
	fmt.Fprint(stderrWriter, formatFatalMessage(format, args...))
	exitFn(1)
}

func formatFatalMessage(format string, args ...any) string {
	return fmt.Sprintf("error: "+format+"\n", args...)
}

func renderJSON(v any, pretty bool) ([]byte, error) {
	if pretty {
		return json.MarshalIndent(v, "", "  ")
	}
	return json.Marshal(v)
}

func renderRawJSON(raw []byte, pretty bool) ([]byte, error) {
	if !pretty {
		return raw, nil
	}
	var v any
	if err := json.Unmarshal(raw, &v); err != nil {
		return nil, fmt.Errorf("decode output: %w", err)
	}
	return json.MarshalIndent(v, "", "  ")
}
