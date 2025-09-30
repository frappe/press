package tui

import (
	"errors"
	"os"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/filepicker"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var BUBBLE_TEA_FILEPICKER_STYLE filepicker.Styles = filepicker.DefaultStylesWithRenderer(lipgloss.DefaultRenderer())

func PickFile(prompt string, allowedExtensions []string) (selectedFile string, err error) {
	fp := filepicker.New()
	fp.AllowedTypes = allowedExtensions
	fp.CurrentDirectory, _ = os.UserHomeDir()
	fp.Styles = BUBBLE_TEA_FILEPICKER_STYLE

	m := &pickerModel{
		filepicker: fp,
		prompt:     prompt,
	}

	p := tea.NewProgram(m)
	if _, err := p.Run(); err != nil {
		return "", err
	}

	// If we have a selected file, return it (regardless of quit status)
	if m.selectedFile != "" {
		return m.selectedFile, nil
	}

	// No file selected - return empty string
	return "", nil
}

// Internal model implementation
type pickerModel struct {
	filepicker   filepicker.Model
	selectedFile string
	quitting     bool
	err          error
	prompt       string
}

type clearErrorMsg struct{}

func clearErrorAfter(t time.Duration) tea.Cmd {
	return tea.Tick(t, func(_ time.Time) tea.Msg {
		return clearErrorMsg{}
	})
}

func (m *pickerModel) Init() tea.Cmd {
	return m.filepicker.Init()
}

func (m *pickerModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+q":
			m.quitting = true
			return m, tea.Quit
		}
	case clearErrorMsg:
		m.err = nil
	}

	var cmd tea.Cmd
	m.filepicker, cmd = m.filepicker.Update(msg)

	if didSelect, path := m.filepicker.DidSelectFile(msg); didSelect {
		m.selectedFile = path
		m.quitting = true
		return m, tea.Quit
	}

	if didSelect, path := m.filepicker.DidSelectDisabledFile(msg); didSelect {
		m.err = errors.New(path + " is not valid")
		m.selectedFile = ""
		return m, tea.Batch(cmd, clearErrorAfter(2*time.Second))
	}

	return m, cmd
}

func (m *pickerModel) View() string {
	if m.quitting {
		return ""
	}
	var s strings.Builder
	s.WriteString("\n  ")
	if m.err != nil {
		s.WriteString(titleStyle.Render(m.filepicker.Styles.DisabledFile.Render(m.err.Error())))
	} else if m.selectedFile == "" {
		s.WriteString(titleStyle.Render(m.prompt))
	} else {
		s.WriteString("Selected file: " + m.filepicker.Styles.Selected.Render(m.selectedFile))
	}
	s.WriteString("\n\n" + m.filepicker.View() + "\n")
	s.WriteString("  <arrow> to navigate • <enter> to select • <ctrl+q> to quit\n")

	return s.String()
}
