package main

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/me/quanbot-dashboard/sections"
	"github.com/me/quanbot-dashboard/util"
)

type result struct{ status util.Status; rows []string }

func fanOut(resolved []sections.Section) []chan result {
	chs := make([]chan result, len(resolved))
	for i, sec := range resolved {
		ch := make(chan result, 1)
		chs[i] = ch
		go func() { s, r := sec.Fetch(); ch <- result{s, r} }()
	}
	return chs
}

func render() {
	cfg := util.LoadConfig()
	resolved := sections.Resolve(cfg)
	chs := fanOut(resolved)
	util.ClearScreen()
	util.Header(cfg.Machine)
	for i, ch := range chs {
		select {
		case res := <-ch:
			util.DrawSection(resolved[i].Title, res.status, res.rows)
		case <-time.After(3 * time.Second):
			util.DrawSection(resolved[i].Title, util.StatusAmber, []string{"timed out"})
		}
		if i < len(chs)-1 {
			fmt.Println()
			util.Divider()
		}
	}
	util.Footer(cfg.RefreshSeconds)
}

func main() {
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	ticker := time.NewTicker(time.Duration(util.LoadConfig().RefreshSeconds) * time.Second)
	defer ticker.Stop()
	for {
		render()
		select {
		case <-ticker.C:
		case <-sig:
			util.ClearScreen()
			os.Exit(0)
		}
	}
}
