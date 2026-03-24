package sections

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/me/quanbot-dashboard/util"
)

var Logs = Section{
	Title: "Recent Activity",
	Fetch: func() (util.Status, []string) {
		home, _ := os.UserHomeDir()
		var rows []string
		for _, name := range []string{"setup.log", "worktree.log"} {
			lines := tailFile(filepath.Join(home, ".quanbot", name), 3)
			if len(lines) == 0 {
				continue
			}
			rows = append(rows, name+":")
			rows = append(rows, lines...)
		}
		if len(rows) == 0 {
			return util.StatusDim, []string{"no recent activity"}
		}
		return util.StatusDim, rows
	},
}

func tailFile(path string, n int) []string {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	return lines[max(0, len(lines)-n):]
}
