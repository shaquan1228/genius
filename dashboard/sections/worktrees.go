package sections

import (
	"fmt"
	"strings"
)

type Worktrees struct{}

func (Worktrees) Render() {
	worktrees := run("git", "worktree", "list")
	lines := strings.Split(strings.TrimSpace(worktrees), "\n")

	dotColor := faint
	if worktrees != "" && len(lines) > 1 {
		dotColor = green
	}

	sectionHeader("Worktrees", dotColor)

	if worktrees == "" {
		faint.Println("  no worktrees")
		return
	}
	for _, line := range lines {
		fmt.Println("  " + line)
	}
}
