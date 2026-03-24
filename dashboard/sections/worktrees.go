package sections

import (
	"strings"

	"github.com/me/quanbot-dashboard/util"
)

var Worktrees = Section{
	Title: "Worktrees",
	Fetch: func() (util.Status, []string) {
		out := run("git", "worktree", "list")
		if out == "" {
			return util.StatusDim, []string{"no worktrees"}
		}
		lines := strings.Split(strings.TrimSpace(out), "\n")
		if len(lines) <= 1 {
			return util.StatusDim, lines
		}
		return util.StatusGreen, lines
	},
}
