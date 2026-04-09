package sections

import (
	"testing"

	"github.com/me/genius-dashboard/util"
	"github.com/stretchr/testify/assert"
)

func TestBuildReturnsEnabledSections(t *testing.T) {
	cfg := util.Config{
		RefreshSeconds: 5,
		Sections: []util.Section{
			{Type: "git", Enabled: true},
			{Type: "tmux", Enabled: false},
			{Type: "custom", Enabled: true, Label: "Test", Items: []string{"a", "b"}},
		},
	}

	assert.Len(t, Build(cfg), 2)
}

func TestBuildSkipsUnknownTypes(t *testing.T) {
	cfg := util.Config{
		RefreshSeconds: 5,
		Sections: []util.Section{
			{Type: "unknown", Enabled: true},
		},
	}

	assert.Empty(t, Build(cfg))
}

func TestCustomSectionHealthAndRows(t *testing.T) {
	cfg := util.Config{
		RefreshSeconds: 5,
		Sections: []util.Section{
			{Type: "custom", Enabled: true, Label: "My Section", Items: []string{"line1", "line2"}},
		},
	}

	secs := Build(cfg)
	assert.Len(t, secs, 1)

	sec := secs[0]
	assert.Equal(t, "My Section", sec.Title())
	assert.Equal(t, "ok", sec.Health())
	assert.Equal(t, []string{"line1", "line2"}, sec.Rows())
}

func TestEmptyCustomSectionHealthIsWarn(t *testing.T) {
	cfg := util.Config{
		RefreshSeconds: 5,
		Sections: []util.Section{
			{Type: "custom", Enabled: true, Label: "", Items: nil},
		},
	}

	sec := Build(cfg)[0]
	assert.Equal(t, "Custom", sec.Title())
	assert.Equal(t, "warn", sec.Health())
}
