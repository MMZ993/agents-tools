package cmd

import (
	"strings"
	"testing"
)

func TestBuildArgumentsRejectsJSONNull(t *testing.T) {
	_, err := buildArguments("null", nil)
	if err == nil || !strings.Contains(err.Error(), "JSON object") {
		t.Fatalf("buildArguments(\"null\") error = %v, want JSON object validation error", err)
	}
}
