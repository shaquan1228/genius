package internal

import (
	"os/exec"
	"strings"
)

// Section holds shared state. Embedded by each concrete section.
type Section struct {
	Title_ string
}

func (s *Section) Title() string { return s.Title_ }

// Run executes a shell command and returns trimmed output, or "" on failure.
func Run(name string, args ...string) string {
	out, err := exec.Command(name, args...).Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}
