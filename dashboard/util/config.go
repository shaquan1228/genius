package util

import (
	"encoding/json"
	"os"
	"path/filepath"
)

type Section struct {
	Type    string   `json:"type"`
	Enabled bool     `json:"enabled"`
	Label   string   `json:"label"`
	Items   []string `json:"items"`
}

type Config struct {
	Machine        string    `json:"machine"`
	RefreshSeconds int       `json:"refresh_seconds"`
	Sections       []Section `json:"sections"`
}

func defaultConfig() Config {
	return Config{
		Machine:        "local",
		RefreshSeconds: 5,
		Sections: []Section{
			{Type: "worktrees", Enabled: true},
			{Type: "git", Enabled: true},
			{Type: "tmux", Enabled: true},
			{Type: "logs", Enabled: true},
		},
	}
}

func LoadConfig() Config {
	home, err := os.UserHomeDir()
	if err != nil {
		return defaultConfig()
	}

	data, err := os.ReadFile(filepath.Join(home, ".quanbot", "dashboard.json"))
	if err != nil {
		return defaultConfig()
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return defaultConfig()
	}

	if cfg.RefreshSeconds <= 0 {
		cfg.RefreshSeconds = 5
	}

	return cfg
}
