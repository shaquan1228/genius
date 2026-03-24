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

func render() {
	cfg := util.LoadConfig()
	util.ClearScreen()
	util.Header(cfg.Machine)
	resolved := sections.Resolve(cfg)
	for i, sec := range resolved {
		fmt.Println()
		status, rows := sec.Fetch()
		util.RenderSection(sec.Title, status, rows)
		if i < len(resolved)-1 {
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
