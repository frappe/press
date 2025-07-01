package tui

import (
	"fmt"
	"os"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type spinnerModel struct {
	spinner  spinner.Model
	message  string
	quitting bool
	err      error
	onQuit   func()
}

func ShowSpinner(message string, onQuit func()) *SpinnerUI {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	m := spinnerModel{
		spinner: s,
		message: message,
		onQuit:  onQuit,
	}

	// Create program without alt screen
	p := tea.NewProgram(m, tea.WithOutput(os.Stderr)) // Output to stderr to avoid mixing with stdout

	doneChan := make(chan struct{})

	go func() {
		if _, err := p.Run(); err != nil {
			fmt.Fprint(os.Stderr, "\033[?25h")
		}
		close(doneChan)
	}()

	return &SpinnerUI{
		program:  p,
		doneChan: doneChan,
	}
}

type SpinnerUI struct {
	program  *tea.Program
	doneChan chan struct{}
}

func (s *SpinnerUI) Done() {
	s.program.Send(tea.KeyMsg{Type: tea.KeyCtrlC})
	<-s.doneChan
	fmt.Fprint(os.Stderr, "\033[?25h")

}

func (m spinnerModel) Init() tea.Cmd {
	return tea.Batch(
		m.spinner.Tick,
		tea.EnterAltScreen, // Start with alt screen
		tea.HideCursor,     // Hide cursor
	)
}

func (m spinnerModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q", "esc":
			m.quitting = true
			m.onQuit()
			return m, tea.Sequence(tea.ShowCursor, tea.Quit)
		}
	case tea.QuitMsg:
		return m, tea.Sequence(tea.ShowCursor, tea.Quit)
	}

	var cmd tea.Cmd
	m.spinner, cmd = m.spinner.Update(msg)
	return m, cmd
}

func (m spinnerModel) View() string {
	if m.quitting {
		return ""
	}
	if m.err != nil {
		return fmt.Sprintf(" %s Error: %v", m.spinner.View(), m.err)
	}
	return fmt.Sprintf(" %s %s", m.spinner.View(), m.message) + "\n\n  Press <q> or <ctrl+c> to quit"
}
