package tui

import (
	"fmt"
	"io"
	"strings"

	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
)

func PickItem(prompt string, items []string) (selectedItem string, err error) {
	// Convert strings to list items
	listItems := make([]list.Item, len(items))
	for i, item := range items {
		listItems[i] = listItem(item)
	}

	// Create list with filepicker-like styles
	l := list.New(listItems, itemDelegate{}, 0, 0)
	l.SetShowTitle(false)
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(true)
	l.SetShowPagination(false)
	l.SetShowHelp(false)

	m := &model{
		list:   l,
		prompt: prompt,
	}

	p := tea.NewProgram(m, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		return "", err
	}

	return m.choice, nil
}

// Styles matching filepicker aesthetics
var (
	titleStyle        = BUBBLE_TEA_FILEPICKER_STYLE.File.Bold(true)
	itemStyle         = BUBBLE_TEA_FILEPICKER_STYLE.File
	selectedItemStyle = BUBBLE_TEA_FILEPICKER_STYLE.Selected
)

type listItem string

func (i listItem) FilterValue() string { return string(i) }

type itemDelegate struct{}

func (d itemDelegate) Height() int                             { return 1 }
func (d itemDelegate) Spacing() int                            { return 0 }
func (d itemDelegate) Update(_ tea.Msg, _ *list.Model) tea.Cmd { return nil }
func (d itemDelegate) Render(w io.Writer, m list.Model, index int, li list.Item) {
	item, ok := li.(listItem)
	if !ok {
		return
	}

	var str string
	if index == m.Index() {
		str = selectedItemStyle.Render("> " + string(item))
	} else {
		str = itemStyle.Render("  " + string(item))
	}

	fmt.Fprint(w, str)
}

type model struct {
	list   list.Model
	choice string
	prompt string
}

func (m *model) Init() tea.Cmd {
	return tea.Batch(
		tea.EnterAltScreen, // Start with alt screen
		tea.HideCursor,     // Hide cursor
		tea.ClearScreen,    // Clear the screen
	)
}

func (m *model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.list.SetWidth(msg.Width)
		m.list.SetHeight(msg.Height - 4) // Leave space for help text
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+q":
			return m, tea.Quit
		case "enter":
			if i, ok := m.list.SelectedItem().(listItem); ok {
				m.choice = string(i)
			}
			return m, tea.Quit
		}
	}

	var cmd tea.Cmd
	m.list, cmd = m.list.Update(msg)
	return m, cmd
}

func (m *model) View() string {
	var s strings.Builder
	s.WriteString("\n  " + titleStyle.Render(m.prompt) + "\n\n")
	s.WriteString(m.list.View())
	s.WriteString("\n  ↑/↓ to navigate • / to search • <enter> to select • <ctrl+q> to quit\n")
	return s.String()
}
