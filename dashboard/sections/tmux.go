package sections

import (
	"fmt"
	"strings"
)

type Tmux struct{}

func (Tmux) Render() {
	sessions := run("tmux", "list-sessions")

	dotColor := faint
	if sessions != "" {
		dotColor = green
	}

	sectionHeader("tmux", dotColor)

	if sessions == "" {
		faint.Println("  no sessions")
		return
	}
	for _, line := range strings.Split(sessions, "\n") {
		fmt.Println("  " + line)
	}
}
