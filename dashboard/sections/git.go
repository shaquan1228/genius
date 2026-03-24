package sections

import (
	"strings"

	"github.com/me/quanbot-dashboard/util"
)

var Git = Section{
	Title: "Git",
	Fetch: func() (util.Status, []string) {
		branch := run("git", "rev-parse", "--abbrev-ref", "HEAD")
		status := run("git", "status", "--short")

		if branch == "" {
			return util.StatusDim, []string{"not a git repo"}
		}
		if status == "" {
			return util.StatusGreen, []string{branch + "  clean"}
		}

		rows := []string{branch + "  dirty"}
		lines := strings.Split(status, "\n")
		rows = append(rows, lines[:min(len(lines), 5)]...)
		return util.StatusAmber, rows
	},
}
