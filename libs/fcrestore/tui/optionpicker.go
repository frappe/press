package tui

import (
	"errors"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

func PickMultipleOptions(prompt string, choices []string) (selectedItems []string, err error) {
	m := &multiSelectModel{
		choices:       choices,
		selected:      make(map[int]bool),
		prompt:        prompt,
		cursor:        0,
		selectedItems: []string{},
	}

	p := tea.NewProgram(m)
	if _, err := p.Run(); err != nil {
		return nil, err
	}

	return m.selectedItems, nil
}

// Internal model implementation
type multiSelectModel struct {
	choices       []string
	selected      map[int]bool
	cursor        int
	selectedItems []string
	quitting      bool
	err           error
	prompt        string
}

func (m *multiSelectModel) Init() tea.Cmd {
	return tea.Batch(
		tea.EnterAltScreen,
		tea.HideCursor,
		clearErrorAfter(0),
	)
}

func (m *multiSelectModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+q":
			m.quitting = true
			return m, tea.Quit
		case "enter":
			// Check if any items are selected
			if len(m.selected) == 0 {
				m.err = errors.New("Please select at least one option")
				return m, clearErrorAfter(2 * time.Second)
			}

			// Collect selected items
			m.selectedItems = make([]string, 0, len(m.selected))
			for i := range m.selected {
				m.selectedItems = append(m.selectedItems, m.choices[i])
			}
			m.quitting = true
			return m, tea.Quit
		case " ":
			// Toggle selection
			if m.selected[m.cursor] {
				delete(m.selected, m.cursor)
			} else {
				m.selected[m.cursor] = true
			}
		case "down", "j":
			m.cursor++
			if m.cursor >= len(m.choices) {
				m.cursor = 0
			}
		case "up", "k":
			m.cursor--
			if m.cursor < 0 {
				m.cursor = len(m.choices) - 1
			}
		}
	case clearErrorMsg:
		m.err = nil
	}

	return m, nil
}

func (m *multiSelectModel) View() string {
	if m.quitting {
		return ""
	}

	var s strings.Builder
	s.WriteString("\n  ")

	// Show error or prompt
	if m.err != nil {
		s.WriteString(titleStyle.Render(BUBBLE_TEA_FILEPICKER_STYLE.DisabledFile.Render(m.err.Error())))
	} else {
		s.WriteString(titleStyle.Render(m.prompt))
	}

	s.WriteString("\n\n")

	// Show choices
	for i, choice := range m.choices {
		cursor := "  "
		if m.cursor == i {
			cursor = "> "
		}

		checkbox := "[ ]"
		if m.selected[i] {
			checkbox = "[✓]"
		}

		line := cursor + checkbox + " " + choice

		if m.cursor == i {
			s.WriteString(selectedItemStyle.Render(line))
		} else {
			s.WriteString(itemStyle.Render(line))
		}
		s.WriteString("\n")
	}

	s.WriteString("\n  ↑/↓ to navigate • <space> to select • <enter> to submit • <ctrl+q> to quit\n")

	return s.String()
}
