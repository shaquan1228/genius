package components

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/me/genius-dashboard/sections/internal"
)

type LogEntry struct {
	Name  string
	Lines []string
}

type LogsData struct {
	Entries []LogEntry
}

type LogsSection struct {
	internal.Section
	Fetch internal.Cache[LogsData]
}

func (l *LogsSection) Health() string {
	if len(l.Fetch.Response().Entries) == 0 {
		return "warn"
	}
	return "ok"
}

func (l *LogsSection) Rows() []string {
	d := l.Fetch.Response()
	if len(d.Entries) == 0 {
		return []string{"no recent activity"}
	}
	var rows []string
	for _, e := range d.Entries {
		rows = append(rows, e.Name+":")
		rows = append(rows, e.Lines...)
	}
	return rows
}

var Logs = LogsSection{
	Section: internal.Section{Title_: "Recent Activity"},
	Fetch: internal.Cache[LogsData]{Fn: func() LogsData {
		home, _ := os.UserHomeDir()
		var entries []LogEntry
		for _, name := range []string{"setup.log", "worktree.log"} {
			if lines := tailFile(filepath.Join(home, ".genius", name), 3); len(lines) > 0 {
				entries = append(entries, LogEntry{Name: name, Lines: lines})
			}
		}
		return LogsData{Entries: entries}
	}},
}

func tailFile(path string, n int) []string {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	return lines[max(0, len(lines)-n):]
}
