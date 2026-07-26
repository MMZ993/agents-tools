package cmd

import (
	"encoding/json"
	"fmt"

	"agents-tools-cli/internal/client"
	"github.com/spf13/cobra"
)

var healthCmd = &cobra.Command{
	Use:   "health",
	Short: "Check broker health (GET /healthz)",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		body, err := c.Health()
		if err != nil {
			fatal("%v", err)
		}
		if pretty {
			var v any
			if err := json.Unmarshal([]byte(body), &v); err == nil {
				b, _ := json.MarshalIndent(v, "", "  ")
				fmt.Println(string(b))
				return
			}
			fmt.Println(body)
			return
		}
		fmt.Println(body)
	},
}
