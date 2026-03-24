package sections

import (
	"strings"

	"github.com/me/quanbot-dashboard/util"
)

var Tmux = Section{
	Title: "tmux",
	Fetch: func() (util.Status, []string) {
		sessions := run("tmux", "list-sessions")
		if sessions == "" {
			return util.StatusDim, []string{"no sessions"}
		}
		return util.StatusGreen, strings.Split(sessions, "\n")
	},
}
