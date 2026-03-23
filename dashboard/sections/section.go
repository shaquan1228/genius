package sections

import (
	"os/exec"
	"strings"

	"github.com/me/quanbot-dashboard/util"
)

// Renderer is implemented by every section.
type Renderer interface {
	Render()
}

// Registry maps config type strings to their section renderer.
// To add a new section: create a new file, implement Render(), add it here.
var Registry = map[string]Renderer{
	"worktrees": Worktrees{},
	"git":       Git{},
	"tmux":      Tmux{},
	"logs":      Logs{},
}

// Unexported color aliases — available to all files in this package.
var (
	bold  = util.Bold
	green = util.Green
	amber = util.Amber
	faint = util.Faint
	cyan  = util.Cyan
)

// sectionHeader prints "● Label" with the dot in the given color.
func sectionHeader(label string, c *util.Color) {
	c.Print("● ")
	bold.Println(label)
}

// run executes a shell command and returns trimmed output, or "" on failure.
func run(name string, args ...string) string {
	out, err := exec.Command(name, args...).Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}
