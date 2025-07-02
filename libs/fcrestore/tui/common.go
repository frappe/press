package tui

func ClearScreen() {
	// Clear the terminal screen
	print("\033[H\033[2J")
}
