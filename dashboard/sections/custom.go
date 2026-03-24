package sections

import "github.com/me/quanbot-dashboard/util"

func NewCustom(label string, items []string) Section {
	if label == "" {
		label = "Custom"
	}
	return Section{
		Title: label,
		Fetch: func() (util.Status, []string) {
			return util.StatusInfo, items
		},
	}
}
