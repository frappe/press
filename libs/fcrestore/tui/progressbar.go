package tui

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/progress"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	progressHelpStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#626262")).Render
)

const (
	progressPadding  = 2
	progressMaxWidth = 80
)

type progressMsg struct {
	ratio      float64
	uploadedGB string
	totalGB    string
}

type progressErrMsg struct{ err error }

type progressModel struct {
	prompt      string
	progress    progress.Model
	err         error
	currentInfo string
	quitting    bool
	onQuit      func()
}

func finalPause() tea.Cmd {
	return tea.Tick(time.Millisecond*750, func(_ time.Time) tea.Msg {
		return nil
	})
}

func (m progressModel) Init() tea.Cmd {
	return tea.Batch(
		tea.EnterAltScreen,
		tea.HideCursor,
		m.progress.Init(),
	)
}

func (m progressModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.Type == tea.KeyCtrlQ {
			m.quitting = true
			if m.onQuit != nil {
				m.onQuit()
			}
			return m, tea.Batch(
				tea.ExitAltScreen,
				tea.ShowCursor,
				tea.Quit,
			)
		}
		return m, nil

	case tea.WindowSizeMsg:
		m.progress.Width = msg.Width - progressPadding*2 - 4
		if m.progress.Width > progressMaxWidth {
			m.progress.Width = progressMaxWidth
		}
		return m, nil

	case progressErrMsg:
		m.err = msg.err
		return m, nil

	case progressMsg:
		var cmds []tea.Cmd
		if msg.ratio >= 1.0 {
			m.quitting = true
			cmds = append(cmds, tea.Sequence(
				finalPause(),
				tea.ExitAltScreen,
				tea.ShowCursor,
				tea.Quit,
			))
		}

		m.currentInfo = fmt.Sprintf("%s / %s", msg.uploadedGB, msg.totalGB)
		cmds = append(cmds, m.progress.SetPercent(msg.ratio))
		return m, tea.Batch(cmds...)

	case progress.FrameMsg:
		progressModel, cmd := m.progress.Update(msg)
		m.progress = progressModel.(progress.Model)
		return m, cmd

	default:
		return m, nil
	}
}

func (m progressModel) View() string {
	if m.quitting {
		return ""
	}

	if m.err != nil {
		return "\n  " + titleStyle.Render(m.prompt) + "\n\n  Error: " + m.err.Error() + "\n\n  " +
			progressHelpStyle("press <ctrl+q> to quit") + "\n"
	}

	pad := strings.Repeat(" ", progressPadding)
	progressView := m.progress.View()

	return "\n  " + titleStyle.Render(m.prompt) + "\n\n" +
		pad + progressView + "\n" +
		pad + m.currentInfo + "\n\n" +
		pad + progressHelpStyle("press <ctrl+q> to quit") + "\n"
}

type ProgressUI struct {
	updateChan chan progressMsg
	errChan    chan error
	DoneChan   chan struct{}
	program    *tea.Program
}

func ShowProgress(prompt string, onQuit func()) *ProgressUI {
	prog := progress.New(
		progress.WithGradient("#FF87D7", "#FF87D7"),
	)

	m := progressModel{
		prompt:   prompt,
		progress: prog,
		onQuit:   onQuit,
	}

	p := tea.NewProgram(m)

	updateChan := make(chan progressMsg)
	errChan := make(chan error)
	doneChan := make(chan struct{})

	go func() {
		if _, err := p.Run(); err != nil {
			// Ensure terminal state is restored on error
			fmt.Fprint(os.Stderr, "\033[?25h\033[?1049l")
		}
		close(doneChan)
	}()

	go func() {
		for {
			select {
			case msg := <-updateChan:
				p.Send(msg)
			case err := <-errChan:
				p.Send(progressErrMsg{err})
			case <-doneChan:
				return
			}
		}
	}()

	return &ProgressUI{
		updateChan: updateChan,
		errChan:    errChan,
		DoneChan:   doneChan,
		program:    p,
	}
}

func (p *ProgressUI) Update(ratio float64, uploadedGB, totalGB string) {
	select {
	case <-p.DoneChan:
		return
	default:
		p.updateChan <- progressMsg{
			ratio:      ratio,
			uploadedGB: uploadedGB,
			totalGB:    totalGB,
		}
	}
}

func (p *ProgressUI) Error(err error) {
	select {
	case <-p.DoneChan:
		return
	default:
		p.errChan <- err
	}
}

func (p *ProgressUI) Done() {
	// Send Ctrl+Q to quit
	p.program.Send(tea.KeyMsg{Type: tea.KeyCtrlQ})

	// Add timeout to prevent hanging
	select {
	case <-p.DoneChan:
	case <-time.After(2 * time.Second):
		// Force cleanup if graceful quit times out
		fmt.Fprint(os.Stdout, "\033[?25h\033[?1049l")
	}

	// Extra terminal reset to be safe
	fmt.Fprint(os.Stdout, "\033[?25h\033[?1049l")
}
