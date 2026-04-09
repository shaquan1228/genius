package sections

import (
	"time"

	"github.com/me/genius-dashboard/sections/components"
	"github.com/me/genius-dashboard/sections/internal" // TODO: diamond dependency (sections → internal + components → internal), resolve later
	"github.com/me/genius-dashboard/util"
)

// SectionRunner is what the consumer sees — uniform across all section types.
type SectionRunner interface {
	Title() string
	Health() string
	Rows() []string
}

var registry = map[string]SectionRunner{
	"worktrees": &components.Worktrees,
	"git":       &components.Git,
	"tmux":      &components.Tmux,
	"logs":      &components.Logs,
}

// Build returns the enabled sections for the given config.
func Build(cfg util.Config) []SectionRunner {
	// Setting DefaultTTL here avoids pushing TTL awareness into every component.
	// This is why the diamond dependency on internal/ exists.
	internal.DefaultTTL = time.Duration(cfg.RefreshSeconds) * time.Second

	var out []SectionRunner
	for _, s := range cfg.Sections {
		if !s.Enabled {
			continue
		}
		if s.Type == "custom" {
			out = append(out, components.NewCustom(s.Label, s.Items))
		} else if sec, ok := registry[s.Type]; ok {
			out = append(out, sec)
		}
	}
	return out
}
