package main

import (
	"fcrestore/tui"
	"fmt"
	"strings"
	"time"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"
)

func main() {
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("An unexpected error occurred:", r)
			fmt.Println("Please try again or contact support if the issue persists.")
		} else {
			fmt.Println("Thank you for using Frappe Cloud Restore CLI!")
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
			fmt.Println("Error picking item: " + error.Error())
			return
		}
		if option == "" {
			fmt.Println("No option selected. Exiting.")
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
			fmt.Println("Error asking for email: " + err.Error())
			return
		}
		if email == "" {
			fmt.Println("Login cancelled.")
			return
		}
		err = session.SendLoginVerificationCode(email)
		if err != nil {
			fmt.Println("Error logging in: " + err.Error())
			return
		}

		// Ask to enter the verification code
		code, err := tui.AskInput("Enter the verification code sent to "+email, "123456")
		if err != nil {
			fmt.Println("Error asking for verification code: " + err.Error())
			return
		}
		if code == "" {
			fmt.Println("Login cancelled.")
			return
		}
		err = session.Login(code)
		if err != nil {
			fmt.Println("Error logging in: " + err.Error())
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
		fmt.Println("Error picking team: " + err.Error())
		return
	}
	if selectedTeam == "" {
		fmt.Println("No team selected. Exiting.")
		return
	}
	teamName := strings.Split(selectedTeam, "<")[1]
	teamName = strings.TrimSuffix(teamName, ">")
	fmt.Println("Selected team:", teamName)
	err = session.SetCurrentTeam(teamName, true)
	if err != nil {
		fmt.Println("Error setting current team: " + err.Error())
		return
	}

	// Ask to pick the site to restore
	sites, err := session.FetchSites()
	if err != nil {
		fmt.Println("Error fetching sites: " + err.Error())
		return
	}
	if len(sites) == 0 {
		fmt.Println("No sites found in the selected team. Exiting.")
		return
	}
	selectedSite, err := tui.PickItem("Select the site you want to restore:", sites)
	if err != nil {
		fmt.Println("Error picking site: " + err.Error())
		return
	}
	if selectedSite == "" {
		fmt.Println("No site selected. Exiting.")
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
		fmt.Println("Error picking restore options: " + err.Error())
		return
	}
	if len(selectedRestoreOptions) == 0 {
		fmt.Println("No restore options selected. Exiting.")
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
			fmt.Println("Unknown restore option:", option)
			return
		}
	}

	// Ask to pick the files to restore
	for restoreType := range filePaths {
		filePath, err := tui.PickFile(fmt.Sprintf("Select the %s file (%s) to restore for %s:", restoreType, strings.Join(allowedFileTypes[restoreType], ", "), selectedSite), allowedFileTypes[restoreType])
		if err != nil {
			fmt.Println("Error picking file for", restoreType+":", err.Error())
			return
		}
		if filePath == "" {
			fmt.Println("No file selected for", restoreType+". Exiting.")
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
			fmt.Println("Error generating upload link for", restoreType+":", err.Error())
			return
		}
		fileUploads[restoreType] = upload
	}
	spinner.Done()

	// Pre-verify restoration space requirements
	spinner = tui.ShowSpinner("Checking Space on Server", func() {})
	defer spinner.Done()

	result, err := session.CheckSpaceOnserver(selectedSite, fileUploads["database"], fileUploads["private"], fileUploads["public"])
	if err != nil {
		fmt.Println("Error validating restoration space requirements:", err.Error())
		return
	}

	if !result.AllowedToUpload {
		fmt.Println("Restoration cannot be performed due to insufficient space on the server.")
		if result.IsInsufficientSpaceOnAppServer {
			fmt.Printf("- Insufficient space on app server [Required: %s, Available: %s]\n", formatBytes(result.RequiredSpaceOnAppServer), formatBytes(result.FreeSpaceOnAppServer))
		}
		if result.ISInsufficientSpaceOnDBServer {
			fmt.Printf("- Insufficient space on database server [Required: %s, Available: %s]\n", formatBytes(result.RequiredSpaceOnDBServer), formatBytes(result.FreeSpaceOnDBServer))
		}
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
		go func(upload *MultipartUpload) {
			ticker := time.NewTicker(1 * time.Second) // Update every second
			defer ticker.Stop()

			for {
				select {
				case <-ticker.C:
					progress, uploadedSize, totalSize := upload.Progress()
					progressBar.Update(progress, uploadedSize, totalSize)
					if progress >= 1.0 {
						close(done)
						progressBar.Done()
						return
					}
				case <-done:
					progressBar.Done()
					return
				}
			}
		}(upload)

		// Start the upload
		err := upload.UploadParts(&session)
		if err != nil {
			progressBar.Done()
			fmt.Println("\nError uploading", restoreType+" file:", err)
			return
		}

		// Check whether uploaded whole file or not
		if upload.UploadedSize < upload.TotalSize {
			fmt.Printf("Uploaded %s file: %s (%d bytes)\n", restoreType, upload.RemoteFile, upload.UploadedSize)
			fmt.Println("Upload incomplete. Please check the file and try again.")
			return
		}

		// Wait for progress monitor to finish
		<-done
		<-progressBar.DoneChan

		err = upload.Complete(&session)
		if err != nil {
			progressBar.Done()
			fmt.Println("Error completing multipart upload for", restoreType+":", err)
			return
		}
	}

	// Validate if all uploaded
	failedUploads := false
	for restoreType, upload := range fileUploads {
		restoreType = cases.Title(language.English).String(restoreType)
		if !upload.IsUploaded() {
			fmt.Printf("x %s file upload failed\n", restoreType)
			failedUploads = true
			return
		}
	}

	// Ask for confirmation to restore
	if !failedUploads {
		confirm, err := tui.PickItem("Do you want to restore the site "+selectedSite+" with the uploaded files?", []string{"Yes, Restore", "No, Cancel"})
		if err != nil {
			fmt.Println("Error picking confirmation:", err.Error())
			return
		}
		if confirm == "" || strings.HasPrefix(confirm, "No") {
			fmt.Println("Restoration cancelled.")
			return
		}
		// Proceed with restoration
		spinner = tui.ShowSpinner("Restoring site...", func() {
		})
		defer spinner.Done()
		err = session.RestoreSite(selectedSite, fileUploads["database"], fileUploads["private"], fileUploads["public"])
		if err != nil {
			fmt.Println("Error restoring site:", err.Error())
			return
		}
		spinner.Done()
		fmt.Println("Site restoration triggered successfully!")
		fmt.Println("You can check the status of the restoration in your Frappe Cloud dashboard.")
		fmt.Printf("%s/dashboard/sites/%s/insights/jobs\n", session.Server, selectedSite)
	}
}
