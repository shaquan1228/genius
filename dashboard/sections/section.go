package sections

import (
	"os/exec"
	"strings"

	"github.com/me/quanbot-dashboard/util"
)

// Section is the base type for all dashboard sections.
// Compose behavior by providing a Fetch function.
type Section struct {
	Title string
	Fetch func() (util.Status, []string)
}

// Registry maps config type strings to their section.
// To add a new section: create a new file, define a Section var, add it here.
var Registry = map[string]Section{
	"worktrees": Worktrees,
	"git":       Git,
	"tmux":      Tmux,
	"logs":      Logs,
}

// Resolve converts a Config into the ordered list of enabled Sections.
func Resolve(cfg util.Config) []Section {
	var out []Section
	for _, s := range cfg.Sections {
		if !s.Enabled {
			continue
		}
		if s.Type == "custom" {
			out = append(out, NewCustom(s.Label, s.Items))
		} else if sec, ok := Registry[s.Type]; ok {
			out = append(out, sec)
		}
	}
	return out
}

// run executes a shell command and returns trimmed output, or "" on failure.
func run(name string, args ...string) string {
	out, err := exec.Command(name, args...).Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}
