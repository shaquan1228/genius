package components

import (
	"fmt"
	"strings"

	"github.com/me/quanbot-dashboard/sections/internal"
)

type GitData struct {
	Branch string
	Clean  bool
	Files  []string
}

type GitSection struct {
	internal.Section
	Fetch internal.Cache[GitData]
}

func (g *GitSection) Health() string {
	d := g.Fetch.Response()
	switch {
	case d.Branch == "":
		return "error"
	case d.Clean:
		return "ok"
	default:
		return "warn"
	}
}

func (g *GitSection) Rows() []string {
	d := g.Fetch.Response()
	if d.Branch == "" {
		return []string{"not a git repo"}
	}
	if d.Clean {
		return []string{d.Branch + "  clean"}
	}
	return append(
		[]string{fmt.Sprintf("%s  dirty (%d files)", d.Branch, len(d.Files))},
		d.Files...,
	)
}

var Git = GitSection{
	Section: internal.Section{Title_: "Git"},
	Fetch: internal.Cache[GitData]{Fn: func() GitData {
		branch := internal.Run("git", "rev-parse", "--abbrev-ref", "HEAD")
		if branch == "" {
			return GitData{}
		}
		status := internal.Run("git", "status", "--short")
		if status == "" {
			return GitData{Branch: branch, Clean: true}
		}
		lines := strings.Split(status, "\n")
		return GitData{Branch: branch, Files: lines[:min(len(lines), 5)]}
	}},
}
