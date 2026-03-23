package sections

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Logs struct{}

func (Logs) Render() {
	sectionHeader("Recent Activity", faint)
	home, _ := os.UserHomeDir()

	found := false
	for _, name := range []string{"setup.log", "worktree.log"} {
		lines := tailFile(filepath.Join(home, ".quanbot", name), 3)
		if len(lines) == 0 {
			continue
		}
		found = true
		faint.Println("  " + name)
		for _, l := range lines {
			fmt.Println("    " + l)
		}
	}
	if !found {
		faint.Println("  no recent activity")
	}
}

func tailFile(path string, n int) []string {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	return lines[max(0, len(lines)-n):]
}
