package components

import "github.com/me/quanbot-dashboard/sections/internal"

type CustomData struct {
	Items []string
}

type CustomSection struct {
	internal.Section
	Fetch internal.Cache[CustomData]
}

func (c *CustomSection) Health() string {
	if len(c.Fetch.Response().Items) == 0 {
		return "warn"
	}
	return "ok"
}

func (c *CustomSection) Rows() []string {
	d := c.Fetch.Response()
	if len(d.Items) == 0 {
		return []string{"(empty)"}
	}
	return d.Items
}

func NewCustom(label string, items []string) *CustomSection {
	if label == "" {
		label = "Custom"
	}
	return &CustomSection{
		Section: internal.Section{Title_: label},
		Fetch: internal.Cache[CustomData]{Fn: func() CustomData {
			return CustomData{Items: items}
		}},
	}
}
