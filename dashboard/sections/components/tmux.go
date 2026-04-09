package components

import (
	"strings"

	"github.com/me/genius-dashboard/sections/internal"
)

type TmuxData struct {
	Sessions []string
}

type TmuxSection struct {
	internal.Section
	Fetch internal.Cache[TmuxData]
}

func (t *TmuxSection) Health() string {
	if len(t.Fetch.Response().Sessions) == 0 {
		return "warn"
	}
	return "ok"
}

func (t *TmuxSection) Rows() []string {
	d := t.Fetch.Response()
	if len(d.Sessions) == 0 {
		return []string{"no sessions"}
	}
	return d.Sessions
}

var Tmux = TmuxSection{
	Section: internal.Section{Title_: "tmux"},
	Fetch: internal.Cache[TmuxData]{Fn: func() TmuxData {
		if out := internal.Run("tmux", "list-sessions"); out != "" {
			return TmuxData{Sessions: strings.Split(out, "\n")}
		}
		return TmuxData{}
	}},
}
