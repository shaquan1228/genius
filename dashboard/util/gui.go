package util

import (
	"fmt"
	"strings"
	"time"

	box "github.com/box-cli-maker/box-cli-maker/v3"
)

type Status int

const (
	StatusDim   Status = iota
	StatusGreen
	StatusAmber
	StatusInfo
)

var headerBox = box.NewBox().Style(box.Bold).ContentAlign(box.Center)

func Header(machine string) {
	label := machine + "  ·  " + time.Now().Format("15:04:05")
	fmt.Println(headerBox.MustRender("QUANBOT", label))
}

func Divider() {
	fmt.Println(strings.Repeat("─", TermWidth()))
}

func DrawSection(title string, status Status, rows []string) {
	fmt.Println()
	c := map[Status]*Color{
		StatusDim: Faint, StatusGreen: Green, StatusAmber: Amber, StatusInfo: Cyan,
	}[status]
	c.Print("● ")
	Bold.Println(title)
	for _, row := range rows {
		fmt.Println("  " + row)
	}
}

func Footer(refreshSeconds int) {
	fmt.Println()
	Faint.Printf("  refreshes every %ds  ·  Ctrl+C to quit\n", refreshSeconds)
}
