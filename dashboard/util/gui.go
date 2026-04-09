package util

import (
	"fmt"
	"strings"
	"time"
)

func HeavyBar(label string) {
	w := TermWidth()
	if label == "" {
		Bold.Println(strings.Repeat("━", w))
		return
	}
	inner := "  " + label + "  "
	pad := max(0, (w-len(inner))/2)
	right := max(0, w-pad-len(inner))
	Bold.Println(strings.Repeat("━", pad) + inner + strings.Repeat("━", right))
}

func Divider() {
	Faint.Println(strings.Repeat("─", TermWidth()))
}

//I DON'T LIKE THIS. THIS IS TEMPORARY FOR GETTING SECTIONS/ IN A SPOT THAT I LIKE.
// RenderSection prints a single section with health-colored title and rows.
func RenderSection(title, health string, rows []string) {
	c := Faint
	switch health {
	case "ok":
		c = Green
	case "warn":
		c = Amber
	}
	c.Printf("  ■ %s\n", title)
	for _, row := range rows {
		fmt.Printf("    %s\n", row)
	}
}

func Render(cfg Config, sectionFns []func()) {
	ClearScreen()

	HeavyBar("GENIUS  ·  " + cfg.Machine + "  ·  " + time.Now().Format("15:04:05"))
	fmt.Println()

	for i, fn := range sectionFns {
		fn()
		if i < len(sectionFns)-1 {
			fmt.Println()
			Divider()
			fmt.Println()
		}
	}

	fmt.Println()
	HeavyBar("")
	Faint.Printf("  refreshes every %ds  ·  Ctrl+C to quit\n", cfg.RefreshSeconds)
}
