package util

import "github.com/fatih/color"

// Color is an alias so callers don't need to import fatih/color directly.
type Color = color.Color

var (
	Bold  = color.New(color.Bold)
	Green = color.New(color.Bold, color.FgGreen)
	Amber = color.New(color.Bold, color.FgYellow)
	Faint = color.New(color.Faint)
	Cyan  = color.New(color.Bold, color.FgCyan)
)
