package client

import (
	"strings"
	"testing"
)

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
