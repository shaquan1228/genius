package util

import (
	"fmt"
	"os"

	"golang.org/x/term"
)

func TermWidth() int {
	w, _, _ := term.GetSize(int(os.Stdout.Fd()))
	if w > 0 {
		return w
	}
	return 80
}

func ClearScreen() {
	fmt.Print("\033[2J\033[H")
}
