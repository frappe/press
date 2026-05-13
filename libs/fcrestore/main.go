package main

import (
	"fcrestore/tui"
	"fmt"
	"os"
	"strings"
	"time"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"
)

var errorLogFile *os.File

// initErrorLog initializes the error log file
func initErrorLog() error {
	var err error
	errorLogFile, err = os.OpenFile("error.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("failed to open error.log: %w", err)
	}
	// Write session start marker
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Fprintf(errorLogFile, "\n=== Session started at %s ===\n", timestamp)
	return nil
}

// closeErrorLog closes the error log file
func closeErrorLog() {
	if errorLogFile != nil {
		timestamp := time.Now().Format("2006-01-02 15:04:05")
		fmt.Fprintf(errorLogFile, "=== Session ended at %s ===\n\n", timestamp)
		errorLogFile.Close()
	}
}

// logError logs error message to both console and error.log file
func logError(format string, args ...interface{}) {
	message := fmt.Sprintf(format, args...)

	// Print to console
	fmt.Println(message)

	// Write to error log file with timestamp
	if errorLogFile != nil {
		timestamp := time.Now().Format("2006-01-02 15:04:05")
		fmt.Fprintf(errorLogFile, "[%s] %s\n", timestamp, message)
	}
}

// waitForUser pauses execution and waits for user to press Enter
// This ensures error messages are visible before program exits
func waitForUser() {
	fmt.Println("\nPress Enter to exit...")
	fmt.Scanln()
}

func main() {
	// Initialize error log
	if err := initErrorLog(); err != nil {
		fmt.Println("Warning: Could not initialize error log:", err)
	}
	defer closeErrorLog()

	defer func() {
		if r := recover(); r != nil {
			logError("An unexpected error occurred: %v", r)
			logError("Please try again or contact support if the issue persists.")
			waitForUser()
		} else {
			fmt.Println("\n\nThank you for using Frappe Cloud Restore CLI!")
			fmt.Println("Exiting in 5 seconds...")
			time.Sleep(5 * time.Second)
		}
	}()
	session := GetSession()
	loginRequired := true
	fmt.Println("Welcome to Frappe Cloud Restore CLI")
	fmt.Println("This CLI will help you restore your site on Frappe Cloud")
	fmt.Print("\n\n")
	time.Sleep(1 * time.Second)

	// Check if the user is already logged in
	if session.IsLoggedIn() {
		option, error := tui.PickItem("You are already logged in as "+session.LoginEmail+". Do you want to continue?", []string{"Yes, Continue with " + session.LoginEmail, "No, Logout and Login with a different account"})
		if error != nil {
			logError("Error picking item: %s", error.Error())
			waitForUser()
			return
		}
		if option == "" {
			logError("No option selected. Exiting.")
			waitForUser()
			return
		}
		if strings.HasPrefix(option, "No") {
			session.Logout()
		} else {
			loginRequired = false
		}
	}

	// Prompt user to log in
	if loginRequired {
		email, err := tui.AskInput("Enter your email address to login to Frappe Cloud", "")
		if err != nil {
			logError("Error asking for email: %s", err.Error())
			waitForUser()
			return
		}
		if email == "" {
			logError("Login cancelled.")
			waitForUser()
			return
		}
		session.LoginEmail = email
		is2FAEnabled, err := session.Is2FAEnabled()
		if err != nil {
			logError("Error checking 2FA status: %s", err.Error())
			waitForUser()
			return
		}
		err = session.SendLoginVerificationCode(email)
		if err != nil {
			logError("Error logging in: %s", err.Error())
			waitForUser()
			return
		}

		// Ask to enter the verification code
		code, err := tui.AskInput("Enter the verification code sent to "+email, "123456")
		if err != nil {
			logError("Error asking for verification code: %s", err.Error())
			waitForUser()
			return
		}
		if code == "" {
			logError("Login cancelled.")
			waitForUser()
			return
		}
		// Ask for 2FA code if enabled
		if is2FAEnabled {
			totpCode, err := tui.AskInput("Enter the 2FA code", "123456")
			if err != nil {
				logError("Error logging in: %s", err.Error())
				waitForUser()
				return
			}
			if totpCode == "" {
				logError("Login cancelled.")
				waitForUser()
				return
			}
			err = session.Verify2FA(totpCode)
			if err != nil {
				logError("Error verifying 2FA code: %s", err.Error())
				waitForUser()
				return
			}
		}
		// Log in with the verification code
		err = session.Login(code)
		if err != nil {
			logError("Error logging in: %s", err.Error())
			waitForUser()
			return
		}
		fmt.Println("Logged in successfully as " + session.LoginEmail)
	}

	// Ask to pick correct team
	teamOptions := []string{}
	for _, team := range session.Teams {
		teamOptions = append(teamOptions, fmt.Sprintf("%s <%s>", team.Title, team.Name))
	}
	selectedTeam, err := tui.PickItem("Select the team you want to restore the site to:", teamOptions)
	if err != nil {
		logError("Error picking team: %s", err.Error())
		waitForUser()
		return
	}
	if selectedTeam == "" {
		logError("No team selected. Exiting.")
		waitForUser()
		return
	}
	teamName := strings.Split(selectedTeam, "<")[1]
	teamName = strings.TrimSuffix(teamName, ">")
	fmt.Println("Selected team:", teamName)
	err = session.SetCurrentTeam(teamName, true)
	if err != nil {
		logError("Error setting current team: %s", err.Error())
		waitForUser()
		return
	}

	// Ask to pick the site to restore
	sites, err := session.FetchSites()
	if err != nil {
		logError("Error fetching sites: %s", err.Error())
		waitForUser()
		return
	}
	if len(sites) == 0 {
		logError("No sites found in the selected team. Exiting.")
		waitForUser()
		return
	}
	selectedSite, err := tui.PickItem("Select the site you want to restore:", sites)
	if err != nil {
		logError("Error picking site: %s", err.Error())
		waitForUser()
		return
	}
	if selectedSite == "" {
		logError("No site selected. Exiting.")
		waitForUser()
		return
	}

	// Ask to choose what user wants to restore
	restoreOptions := []string{
		"Database",
		"Private Files",
		"Public Files",
	}
	selectedRestoreOptions, err := tui.PickMultipleOptions(fmt.Sprintf("Select what you want to restore on %s :", selectedSite), restoreOptions)
	if err != nil {
		logError("Error picking restore options: %s", err.Error())
		waitForUser()
		return
	}
	if len(selectedRestoreOptions) == 0 {
		logError("No restore options selected. Exiting.")
		waitForUser()
		return
	}

	filePaths := map[string]string{}
	allowedFileTypes := map[string][]string{
		"database": {".sql", ".sql.gz"},
		"private":  {".tar", ".tar.gz"},
		"public":   {".tar", ".tar.gz"},
	}

	for _, option := range selectedRestoreOptions {
		switch option {
		case "Database":
			filePaths["database"] = ""
		case "Private Files":
			filePaths["private"] = ""
		case "Public Files":
			filePaths["public"] = ""
		default:
			logError("Unknown restore option: %s", option)
			waitForUser()
			return
		}
	}

	// Ask to pick the files to restore
	for restoreType := range filePaths {
		filePath, err := tui.PickFile(fmt.Sprintf("Select the %s file (%s) to restore for %s:", restoreType, strings.Join(allowedFileTypes[restoreType], ", "), selectedSite), allowedFileTypes[restoreType])
		if err != nil {
			logError("Error picking file for %s: %s", restoreType, err.Error())
			waitForUser()
			return
		}
		if filePath == "" {
			logError("No file selected for %s. Exiting.", restoreType)
			waitForUser()
			return
		}
		filePaths[restoreType] = filePath
	}
	// Create the link for multipart upload
	fileUploads := make(map[string]*MultipartUpload)
	spinner := tui.ShowSpinner("Generating upload links...", func() {
	})
	defer spinner.Done()
	for restoreType, filePath := range filePaths {
		upload, err := session.GenerateMultipartUploadLink(filePath)
		if err != nil {
			spinner.Done()
			time.Sleep(500 * time.Millisecond)
			logError("\nError generating upload link for %s: %s", restoreType, err.Error())
			waitForUser()
			return
		}
		fileUploads[restoreType] = upload
	}
	spinner.Done()

	// Pre-verify restoration space requirements
	spinner = tui.ShowSpinner("Checking Space on Server", func() {})
	defer spinner.Done()

	result, err := session.CheckSpaceOnserver(selectedSite, fileUploads["database"], fileUploads["public"], fileUploads["private"])
	if err != nil {
		spinner.Done()
		time.Sleep(500 * time.Millisecond)
		logError("\nError validating restoration space requirements: %s", err.Error())
		waitForUser()
		return
	}

	if !result.AllowedToUpload {
		spinner.Done()
		time.Sleep(500 * time.Millisecond)
		logError("\nRestoration cannot be performed due to insufficient space on the server.")
		if result.IsInsufficientSpaceOnAppServer {
			logError("- Insufficient space on app server [Required: %s, Available: %s]", formatBytes(result.RequiredSpaceOnAppServer), formatBytes(result.FreeSpaceOnAppServer))
		}
		if result.ISInsufficientSpaceOnDBServer {
			logError("- Insufficient space on database server [Required: %s, Available: %s]", formatBytes(result.RequiredSpaceOnDBServer), formatBytes(result.FreeSpaceOnDBServer))
		}
		waitForUser()
		return
	}

	spinner.Done()

	// Start uploading files
	for restoreType, upload := range fileUploads {
		// Create channel to signal when upload is done
		done := make(chan struct{})
		progressBar := tui.ShowProgress(fmt.Sprintf("Uploading %s file...", restoreType), func() {
			upload.Abort(&session)
		})

		// Start progress monitoring in a separate goroutine
		go func(upload *MultipartUpload, done chan struct{}) {
			ticker := time.NewTicker(1 * time.Second) // Update every second
			defer ticker.Stop()
			defer progressBar.Done()

			for {
				select {
				case <-ticker.C:
					progress, uploadedSize, totalSize := upload.Progress()
					progressBar.Update(progress, uploadedSize, totalSize)
					if progress >= 1.0 {
						return
					}
				case <-done:
					// Upload finished or cancelled
					progress, uploadedSize, totalSize := upload.Progress()
					progressBar.Update(progress, uploadedSize, totalSize)
					return
				}
			}
		}(upload, done)

		// Start the upload
		err := upload.UploadParts(&session)

		// Signal progress monitor to stop
		close(done)

		if err != nil {
			<-progressBar.DoneChan
			time.Sleep(500 * time.Millisecond)
			logError("\nError uploading %s file: %v", restoreType, err)
			waitForUser()
			return
		}

		// Check whether uploaded whole file or not
		if upload.UploadedSize < upload.TotalSize {
			<-progressBar.DoneChan
			time.Sleep(500 * time.Millisecond)
			logError("\nUploaded %s file: %s (%d bytes)", restoreType, upload.RemoteFile, upload.UploadedSize)
			logError("Upload incomplete. Please check the file and try again.")
			waitForUser()
			return
		}

		// Wait for progress monitor to finish
		<-progressBar.DoneChan

		err = upload.Complete(&session)
		if err != nil {
			time.Sleep(500 * time.Millisecond)
			logError("\nError completing multipart upload for %s: %v", restoreType, err)
			waitForUser()
			return
		}
	}

	// Validate if all uploaded
	failedUploads := false
	for restoreType, upload := range fileUploads {
		restoreType = cases.Title(language.English).String(restoreType)
		if !upload.IsUploaded() {
			logError("x %s file upload failed", restoreType)
			failedUploads = true
			waitForUser()
			return
		}
	}

	// Ask for confirmation to restore
	if !failedUploads {
		confirm, err := tui.PickItem("Do you want to restore the site "+selectedSite+" with the uploaded files?", []string{"Yes, Restore", "No, Cancel"})
		if err != nil {
			logError("Error picking confirmation: %s", err.Error())
			waitForUser()
			return
		}
		if confirm == "" || strings.HasPrefix(confirm, "No") {
			logError("Restoration cancelled.")
			waitForUser()
			return
		}
		isDatabaseGettingRestored := false
		if fileUploads["database"] != nil && fileUploads["database"].IsUploaded() {
			isDatabaseGettingRestored = true
		}
		skipFailingPatches := false
		if isDatabaseGettingRestored {
			isSkipPatches, err := tui.PickItem("Do you want to skip failing patches during migration ?\nYou can fix the issues manually and migrate from Site Actions later", []string{"Yes, Skip Patches", "No, Migrate with Patches"})
			if err != nil {
				logError("Error picking skip patches option: %s", err.Error())
				waitForUser()
				return
			}
			skipFailingPatches = strings.HasPrefix(isSkipPatches, "Yes")
		}
		// Proceed with restoration
		spinner = tui.ShowSpinner("Restoring site...", func() {
		})
		err = session.RestoreSite(selectedSite, fileUploads["database"], fileUploads["public"], fileUploads["private"], skipFailingPatches)
		if err != nil {
			spinner.Done()
			time.Sleep(1 * time.Second)
			logError("\nFailed to restore site: %s", err.Error())
			waitForUser()
			return
		}
		spinner.Done()
		time.Sleep(1 * time.Second)
		fmt.Println("Site restoration triggered successfully!")
		fmt.Println("You can check the status of the restoration in your Frappe Cloud dashboard.")
		fmt.Printf("%s/dashboard/sites/%s/insights/jobs\n", session.Server, selectedSite)
		if isDatabaseGettingRestored {
			fmt.Println()
			fmt.Println("NOTE: Once restoration gets completed, please collect the encryption key from backed up site_config.json file and set it in the restored site.")
		}
	}
}
