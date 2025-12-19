package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

var debugLogFile *os.File
var sessionFile = "session_v2.json"
var apiHTTPClient *http.Client

func init() {
	if os.Getenv("DEBUG") == "1" {
		var err error
		debugLogFile, err = os.OpenFile("debug.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			debugLogFile = nil
		}
	}

	// Initialize HTTP client with proper timeout for API requests
	apiHTTPClient = &http.Client{
		Timeout: 5 * time.Minute, // 5 minute timeout for API requests
		Transport: &http.Transport{
			MaxIdleConns:        100,
			IdleConnTimeout:     90 * time.Second,
			DisableCompression:  false,
			TLSHandshakeTimeout: 10 * time.Second,
		},
	}
}

func DebugLogger(format string, args ...any) {
	if debugLogFile != nil {
		fmt.Fprintf(debugLogFile, format, args...)
	}
}

type Session struct {
	Server           string            `json:"server"`
	SessionID        string            `json:"session_id"`
	LoginEmail       string            `json:"login_email"`
	CurrentTeam      string            `json:"current_team"`
	CurrentTeamTitle string            `json:"current_team_title"`
	TwoFactorState   map[string]bool   `json:"two_factor_state"` // Track 2FA state for each team
	Teams            []Team            `json:"teams"`
	UploadedFiles    map[string]string `json:"uploaded_files"`
	/*
		In UploadedFiles store the remote file reference to prevent re-uploading the same file in case of failure.
		Key Format : <file_path>_<last_modified_timestamp>_<current_day>_<current_month>_<current_year>
		Value: Remote file name
	*/
}

type Team struct {
	Name  string `json:"name"`
	Title string `json:"team_title"`
	User  string `json:"user"`
}

func GetSession() Session {
	defaultServer := "frappecloud.com"

	// Check if session file exists
	if fileExists(sessionFile) {
		data, err := os.ReadFile(sessionFile)
		if err == nil {
			var session Session
			if json.Unmarshal(data, &session) == nil {
				if session.Server == "" {
					session.Server = defaultServer
				}
				return session
			}
		}
	}

	// session.json does not exist → create it
	server := os.Getenv("FC_SERVER")
	if server == "" {
		server = defaultServer
	}

	session := Session{
		Server:           server,
		SessionID:        "",
		LoginEmail:       "",
		CurrentTeam:      "",
		CurrentTeamTitle: "",
		TwoFactorState:   make(map[string]bool),
		Teams:            []Team{},
		UploadedFiles:    make(map[string]string),
	}

	data, err := json.MarshalIndent(session, "", "  ")
	if err == nil {
		_ = os.WriteFile(sessionFile, data, 0644)
	}

	return session
}

func (s *Session) Save() error {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(sessionFile, data, 0644)
}

func (s *Session) SendRequest(method string, payload map[string]any) (map[string]any, error) {
	return s.SendRequestWithContext(context.Background(), method, payload)
}

func (s *Session) SendRequestWithContext(ctx context.Context, method string, payload map[string]any) (map[string]any, error) {
	schema := "https"
	if strings.Contains(s.Server, ".local") {
		schema = "http"
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", "", bytes.NewBuffer(data))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.URL = &url.URL{
		Scheme: schema,
		Host:   s.Server,
		Path:   fmt.Sprintf("/api/method/%s", method),
	}
	req.Header = http.Header{
		"Content-Type": {"application/json"},
		"X-Press-Team": {s.CurrentTeam},
		"Cookie":       {fmt.Sprintf("sid=%s", s.SessionID)},
	}

	resp, err := apiHTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Handle 417 status specially
	if resp.StatusCode == http.StatusExpectationFailed || resp.StatusCode == http.StatusUnauthorized {
		var errorPayload struct {
			ExcType        string `json:"exc_type"`
			ServerMessages string `json:"_server_messages"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&errorPayload); err != nil {
			return nil, fmt.Errorf("status 417 but failed to parse body: %w", err)
		}

		var rawMessages []string
		if err := json.Unmarshal([]byte(errorPayload.ServerMessages), &rawMessages); err != nil {
			return nil, fmt.Errorf("failed to unmarshal _server_messages array: %w", err)
		}

		var combinedMessages []string
		for _, raw := range rawMessages {
			var msgData map[string]interface{}
			if err := json.Unmarshal([]byte(raw), &msgData); err != nil {
				continue // skip malformed message entries
			}
			if m, ok := msgData["message"].(string); ok {
				combinedMessages = append(combinedMessages, m)
			}
		}

		return nil, fmt.Errorf("%s: %s", errorPayload.ExcType, strings.Join(combinedMessages, " + "))
	}

	if resp.StatusCode != http.StatusOK {
		if os.Getenv("DEBUG") == "1" {
			DebugLogger("Request Failed")
			DebugLogger("Status Code: %d\n", resp.StatusCode)
			DebugLogger("URL: %s\n", req.URL.String())
			DebugLogger("Method: %s\n", req.Method)
			DebugLogger("Headers: %v\n", req.Header)
			DebugLogger("Request Body: %s\n", string(data))
			// Read the response body to provide more context in the error
			bodyBytes, err := io.ReadAll(resp.Body)
			if err == nil {
				bodyString := string(bodyBytes)
				DebugLogger("Response body: %s\n", bodyString)
			}
			DebugLogger("\n\n")
		}
		return nil, fmt.Errorf("request failed with status: %s", resp.Status)
	}

	// Check if the request has sid cookie set
	if cookie := resp.Header.Get("Set-Cookie"); cookie != "" {
		cookieParts := strings.Split(cookie, ";")
		for _, part := range cookieParts {
			if strings.HasPrefix(part, "sid=") {
				// If sid is set, update the session
				sid := strings.TrimPrefix(part, "sid=")
				if strings.Compare(s.SessionID, sid) != 0 && strings.Compare(sid, "Guest") != 0 {
					s.SessionID = sid
					if err := s.Save(); err != nil {
						return nil, fmt.Errorf("failed to save session after setting sid: %w", err)
					}
				}
				break
			}
		}
	}

	var response map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, err
	}

	return response, nil
}

func (s *Session) SendLoginVerificationCode(email string) error {
	s.LoginEmail = email
	if err := s.Save(); err != nil {
		return fmt.Errorf("failed to save session: %w", err)
	}
	_, err := s.SendRequest("press.api.account.send_otp", map[string]any{
		"email": s.LoginEmail,
	})
	return err
}

func (s *Session) Is2FAEnabled() (bool, error) {
	// Check if we already have the 2FA state for this user
	if state, exists := s.TwoFactorState[s.LoginEmail]; exists {
		return state, nil
	}
	if s.LoginEmail == "" {
		return false, fmt.Errorf("login email is not set")
	}
	// Check if 2FA is enabled for the user
	resp, err := s.SendRequest("press.api.account.is_2fa_enabled", map[string]any{
		"user": s.LoginEmail,
	})
	if err != nil {
		return false, fmt.Errorf("error checking 2FA status: %w", err)
	}
	// grab the message field
	message, ok := resp["message"].(bool)
	if !ok {
		return false, fmt.Errorf("response does not contain 'message'")
	}
	// Cache the 2FA state for the user
	// Because the endpoint rate limited highly
	// Every hour only 10 requests are allowed
	s.TwoFactorState[s.LoginEmail] = message
	if err := s.Save(); err != nil {
		return false, fmt.Errorf("failed to save session after checking 2FA status: %w", err)
	}
	return message, nil
}

func (s *Session) Verify2FA(totp_code string) error {
	if s.LoginEmail == "" {
		return fmt.Errorf("login email is not set")
	}
	resp, err := s.SendRequest("press.api.account.verify_2fa", map[string]any{
		"user":      s.LoginEmail,
		"totp_code": totp_code,
	})
	if err != nil {
		return fmt.Errorf("error verifying 2FA OTP: %w", err)
	}

	// Check if the response contains a message
	verified, ok := resp["message"].(bool)
	if !ok {
		return fmt.Errorf("response does not contain 'message'")
	}

	if !verified {
		return fmt.Errorf("2FA verification failed, provided code might be incorrect")
	}

	return nil
}

func (s *Session) Login(otp string) error {
	_, err := s.SendRequest("press.api.account.verify_otp_and_login", map[string]any{
		"email": s.LoginEmail,
		"otp":   otp,
	})
	if err != nil {
		return err
	}

	// Fetch account info
	resp, err := s.SendRequest("press.api.account.get", map[string]any{})
	if err != nil {
		return fmt.Errorf("error fetching account info: %w", err)

	}

	// Extract message from the response
	resp, ok := resp["message"].(map[string]any)
	if !ok {
		return fmt.Errorf("response does not contain 'message'")
	}

	// Extract teams from the response
	raw, ok := resp["teams"]
	if !ok {
		return fmt.Errorf("response does not contain 'teams'")
	}

	jsonBytes, err := json.Marshal(raw)
	if err != nil {
		return fmt.Errorf("failed to marshal teams data: %w", err)
	}

	var teams []Team
	if err := json.Unmarshal(jsonBytes, &teams); err != nil {
		return fmt.Errorf("failed to unmarshal teams data: %w", err)
	}
	s.Teams = teams

	// Extract current team from the response
	team, ok := resp["team"]
	if !ok {
		return fmt.Errorf("failed to extract current team from response")
	}
	teamId, ok := team.(map[string]any)["name"].(string)
	if !ok {
		return fmt.Errorf("failed to convert current team to string")
	}
	if err := s.SetCurrentTeam(teamId, true); err != nil {
		return fmt.Errorf("failed to set current team: %w", err)
	}
	return nil
}

func (s *Session) Logout() {
	_, _ = s.SendRequest("logout", map[string]any{})
	// Delete session file
	_ = os.Remove("session.json")
}

func (s *Session) SetCurrentTeam(teamID string, save bool) error {
	currentTeamTitle := ""
	foundTeam := false
	for _, t := range s.Teams {
		if t.Name == teamID {
			currentTeamTitle = t.Title
			foundTeam = true
			break
		}
	}
	if !foundTeam {
		return fmt.Errorf("team with ID '%s' not found. Please logout and login again to refresh teams list", teamID)
	}
	s.CurrentTeam = teamID
	s.CurrentTeamTitle = currentTeamTitle
	if save {
		if err := s.Save(); err != nil {
			return fmt.Errorf("failed to save session after setting current team: %w", err)
		}
	}
	return nil
}

func (s *Session) IsLoggedIn() bool {
	if s.SessionID == "" || s.LoginEmail == "" || s.SessionID == "Guest" {
		return false
	}
	// Check if the session is still valid by sending a simple request
	resp, err := s.SendRequest("press.api.account.get", map[string]any{})
	if err != nil {
		return false
	}
	// If the response contains a message, it means the session is valid
	_, ok := resp["message"].(map[string]any)

	if !ok {
		s.Logout()
	}

	return ok
}

func (s *Session) FetchSites() ([]string, error) {
	resp, err := s.SendRequest("press.api.client.get_list", map[string]any{
		"doctype":           "Site",
		"fields":            []string{"name"},
		"filters":           map[string]any{},
		"order_by":          "creation desc",
		"start":             0,
		"limit":             1000,
		"limit_start":       0,
		"limit_page_length": 1000,
	})
	if err != nil {
		return nil, fmt.Errorf("error fetching sites: %w", err)
	}

	// Extract sites from the response
	sites, ok := resp["message"].([]any)
	if !ok {
		return nil, fmt.Errorf("response does not contain 'sites'")
	}

	var siteNames []string
	for _, site := range sites {
		if name, ok := site.(map[string]any)["name"].(string); ok {
			siteNames = append(siteNames, name)
		}
	}

	return siteNames, nil
}

type SpaceRequirementResponse struct {
	AllowedToUpload                bool  `json:"allowed_to_upload"`
	FreeSpaceOnAppServer           int64 `json:"free_space_on_app_server"`
	FreeSpaceOnDBServer            int64 `json:"free_space_on_db_server"`
	IsInsufficientSpaceOnAppServer bool  `json:"is_insufficient_space_on_app_server"`
	ISInsufficientSpaceOnDBServer  bool  `json:"is_insufficient_space_on_db_server"`
	RequiredSpaceOnAppServer       int64 `json:"required_space_on_app_server"`
	RequiredSpaceOnDBServer        int64 `json:"required_space_on_db_server"`
}

func (s *Session) CheckSpaceOnserver(siteName string, databaseFile *MultipartUpload, publicFile *MultipartUpload, privateFile *MultipartUpload) (*SpaceRequirementResponse, error) {
	resp, err := s.SendRequest("press.api.site.validate_restoration_space_requirements", map[string]any{
		"name":              siteName,
		"db_file_size":      getTotalSize(databaseFile),
		"public_file_size":  getTotalSize(publicFile),
		"private_file_size": getTotalSize(privateFile),
	})
	if err != nil {
		return nil, fmt.Errorf("error validating restoration space requirements: %w", err)
	}
	message, ok := resp["message"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("response does not contain 'message'")
	}
	var spaceResp SpaceRequirementResponse
	jsonBytes, err := json.Marshal(message)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal space requirement response: %w", err)
	}
	if err := json.Unmarshal(jsonBytes, &spaceResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal space requirement response: %w", err)
	}
	return &spaceResp, nil
}

func (s *Session) RestoreSite(siteName string, databaseFile *MultipartUpload, publicFile *MultipartUpload, privateFile *MultipartUpload, skipFailingPatches bool) error {
	files := map[string]any{
		"database": nil,
		"public":   nil,
		"private":  nil,
	}
	if databaseFile != nil && databaseFile.RemoteFile != "" {
		files["database"] = databaseFile.RemoteFile
	}
	if publicFile != nil && publicFile.RemoteFile != "" {
		files["public"] = publicFile.RemoteFile
	}
	if privateFile != nil && privateFile.RemoteFile != "" {
		files["private"] = privateFile.RemoteFile
	}
	_, err := s.SendRequest("press.api.site.restore", map[string]any{
		"name":                 siteName,
		"files":                files,
		"skip_failing_patches": skipFailingPatches,
	})
	if err != nil {
		return fmt.Errorf("error restoring site: %w", err)
	}
	return nil
}
