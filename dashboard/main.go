package main

import (
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/me/genius-dashboard/sections"
	"github.com/me/genius-dashboard/util"
)

var (
	cfg  util.Config
	secs []sections.SectionRunner
)

func render() {
	fns := make([]func(), len(secs))
	for i, sec := range secs {
		sec := sec
		fns[i] = func() {
			util.RenderSection(sec.Title(), sec.Health(), sec.Rows())
		}
	}
	util.Render(cfg, fns)
}

func main() {
	cfg = util.LoadConfig()
	secs = sections.Build(cfg)

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)

	ticker := time.NewTicker(time.Duration(cfg.RefreshSeconds) * time.Second)
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
