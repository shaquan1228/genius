package sections

import (
	"fmt"
	"strings"
)

type Git struct{}

func (Git) Render() {
	branch := run("git", "rev-parse", "--abbrev-ref", "HEAD")
	status := run("git", "status", "--short")

	dotColor := faint
	if branch != "" && status == "" {
		dotColor = green
	} else if branch != "" {
		dotColor = amber
	}

	sectionHeader("Git", dotColor)

	if branch == "" {
		faint.Println("  not a git repo")
		return
	}

	if status == "" {
		green.Print("  " + branch)
		faint.Println("  clean")
	} else {
		amber.Println("  " + branch + "  dirty")
		lines := strings.Split(status, "\n")
		for _, l := range lines[:min(len(lines), 5)] {
			fmt.Println("    " + l)
		}
	}
}
