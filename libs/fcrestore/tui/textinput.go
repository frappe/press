package tui

import (
	"fmt"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
)

// AskInput shows a text input prompt and returns the entered value or empty string if cancelled
func AskInput(prompt, placeholder string) (string, error) {
	ti := textinput.New()
	ti.Placeholder = placeholder
	ti.Focus()
	ti.Width = 40

	m := &inputModel{ // Use pointer
		textInput: ti,
		prompt:    prompt,
		result:    "",
	}

	p := tea.NewProgram(m)
	finalModel, err := p.Run()
	if err != nil {
		return "", err
	}

	// Cast back to our model type and access result
	if finalInputModel, ok := finalModel.(*inputModel); ok {
		return finalInputModel.result, nil
	}

	return "", nil
}

type inputModel struct {
	textInput textinput.Model
	prompt    string
	result    string
}

func (m *inputModel) Init() tea.Cmd { // Use pointer receiver
	return tea.Sequence(tea.EnterAltScreen, textinput.Blink, tea.HideCursor)
}

func (m *inputModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) { // Use pointer receiver
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyEnter:
			m.result = m.textInput.Value()
			fmt.Println("You entered:", m.result)
			return m, tea.Quit
		case tea.KeyCtrlQ:
			return m, tea.Quit
		}
	}

	m.textInput, cmd = m.textInput.Update(msg)
	return m, cmd
}

func (m *inputModel) View() string { // Use pointer receiver
	return fmt.Sprintf(
		"%s\n\n%s\n\n<enter> to submit • <ctrl+q> to quit",
		titleStyle.Render(m.prompt),
		m.textInput.View(),
	)
}
