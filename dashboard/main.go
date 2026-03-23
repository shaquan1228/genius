package main

import (
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/me/quanbot-dashboard/sections"
	"github.com/me/quanbot-dashboard/util"
)

func sectionFns(cfg util.Config) []func() {
	var fns []func()
	for _, s := range cfg.Sections {
		if !s.Enabled {
			continue
		}
		if s.Type == "custom" {
			cs := sections.Custom{Label: s.Label, Items: s.Items}
			fns = append(fns, cs.Render)
		} else if r, ok := sections.Registry[s.Type]; ok {
			fns = append(fns, r.Render)
		}
	}
	return fns
}

func main() {
	cfg := util.LoadConfig()

	// Catch Ctrl+C so we can exit cleanly.
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)

	util.Render(cfg, sectionFns(cfg))

	// Re-render on every tick, or exit on signal — whichever fires first.
	ticker := time.NewTicker(time.Duration(cfg.RefreshSeconds) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			cfg = util.LoadConfig()
			util.Render(cfg, sectionFns(cfg))
		case <-sig:
			util.ClearScreen()
			os.Exit(0)
		}
	}
}
