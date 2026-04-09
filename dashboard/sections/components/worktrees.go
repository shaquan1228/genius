package components

import (
	"strings"

	"github.com/me/genius-dashboard/sections/internal"
)

type WorktreeData struct {
	Entries []string
}

type WorktreesSection struct {
	internal.Section
	Fetch internal.Cache[WorktreeData]
}

func (w *WorktreesSection) Health() string {
	if len(w.Fetch.Response().Entries) == 0 {
		return "warn"
	}
	return "ok"
}

func (w *WorktreesSection) Rows() []string {
	d := w.Fetch.Response()
	if len(d.Entries) == 0 {
		return []string{"no worktrees"}
	}
	return d.Entries
}

var Worktrees = WorktreesSection{
	Section: internal.Section{Title_: "Worktrees"},
	Fetch: internal.Cache[WorktreeData]{Fn: func() WorktreeData {
		if out := internal.Run("git", "worktree", "list"); out != "" {
			return WorktreeData{Entries: strings.Split(strings.TrimSpace(out), "\n")}
		}
		return WorktreeData{}
	}},
}
