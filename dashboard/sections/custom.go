package sections

type Custom struct {
	Label string
	Items []string
}

func (c Custom) Render() {
	label := c.Label
	if label == "" {
		label = "Custom"
	}
	sectionHeader(label, cyan)
	for _, item := range c.Items {
		amber.Println("  " + item)
	}
}
