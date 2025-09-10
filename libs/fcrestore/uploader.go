package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gabriel-vasile/mimetype"
)

var (
	PART_SIZE       int64 = 1 * 1024 * 1024 * 1024 // 1GB per part
	MAX_CONCURRENCY       = 10                     // Limit concurrent uploads
	HTTP_TIMEOUT          = 30 * time.Minute       // Request timeout
)

type MultipartUpload struct {
	Path         string
	FileName     string
	ModifiedOn   time.Time
	MimeType     string
	TotalSize    int64
	UploadedSize int64 // atomic access only
	PartSize     int64
	SignedURLs   []string
	Etags        []string
	Key          string
	UploadID     string
	RemoteFile   string

	// Concurrency control
	client     *http.Client
	mu         sync.Mutex
	cancelFn   context.CancelFunc
	ctx        context.Context
	errors     []error
	wg         sync.WaitGroup
	bufferPool sync.Pool
}

type progressTracker struct {
	io.Reader
	size *int64
}

func (pt *progressTracker) Read(p []byte) (int, error) {
	n, err := pt.Reader.Read(p)
	if n > 0 {
		atomic.AddInt64(pt.size, int64(n))
	}
	return n, err
}

type partRange struct {
	start, end int64
}

func (m *MultipartUpload) NoOfParts() int {
	return len(m.SignedURLs)
}

func (m *MultipartUpload) CacheKey() string {
	now := time.Now()
	return fmt.Sprintf("%s.%d.%d.%d.%d", m.Path, m.ModifiedOn.UnixNano(), now.Day(), now.Month(), now.Year())
}

func (m *MultipartUpload) IsUploaded() bool {
	return strings.Compare(m.RemoteFile, "") != 0
}

func (s *Session) GenerateMultipartUploadLink(filePath string) (*MultipartUpload, error) {
	info, err := os.Stat(filePath)
	if err != nil {
		return nil, fmt.Errorf("file error: %w", err)
	}

	if info.IsDir() {
		return nil, fmt.Errorf("path is directory: %s", filePath)
	}

	totalSize := info.Size()
	if totalSize == 0 {
		return nil, fmt.Errorf("empty file: %s", filePath)
	}

	mime, err := mimetype.DetectFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("mime detection failed: %w", err)
	}

	partSize := min(PART_SIZE, totalSize)
	noOfParts := max(2, int(math.Ceil(float64(totalSize)/float64(partSize))))

	resp, err := s.SendRequest("press.api.site.get_upload_link", map[string]any{
		"file":  info.Name(),
		"parts": noOfParts,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get upload links: %w", err)
	}

	message, ok := resp["message"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("invalid response format")
	}

	upload := &MultipartUpload{
		Path:       filePath,
		FileName:   info.Name(),
		MimeType:   mime.String(),
		ModifiedOn: info.ModTime(),
		TotalSize:  totalSize,
		PartSize:   partSize,
		SignedURLs: convertToStringSlice(message["signed_urls"]),
		Etags:      make([]string, noOfParts),
		Key:        getString(message, "Key"),
		UploadID:   getString(message, "UploadId"),
		client: &http.Client{
			Timeout: HTTP_TIMEOUT,
			Transport: &http.Transport{
				MaxIdleConns:       MAX_CONCURRENCY,
				IdleConnTimeout:    90 * time.Second,
				DisableCompression: true,
			},
		},
		bufferPool: sync.Pool{
			New: func() interface{} {
				buf := make([]byte, 32*1024) // 32KB buffer
				return &buf
			},
		},
	}

	return upload, nil
}

func (m *MultipartUpload) UploadParts(s *Session) error {
	if m.IsUploaded() {
		// If it's already uploaded, silently ignore
		return nil
	}

	// Check if the file already uploaded previously
	if remote_file, ok := s.UploadedFiles[m.CacheKey()]; ok && remote_file != "" {
		m.RemoteFile = remote_file
		m.UploadedSize = m.TotalSize
		// This will clear the pre-signed URLs which isn't going to be used
		m.abortPresignedURLs(s)
		return nil
	}
	m.mu.Lock()
	m.ctx, m.cancelFn = context.WithCancel(context.Background())
	m.errors = make([]error, 0)
	m.UploadedSize = 0 // Reset progress
	m.mu.Unlock()

	partRanges := m.calculatePartRanges()
	errorChan := make(chan error, len(partRanges))
	sem := make(chan struct{}, MAX_CONCURRENCY)

	for i, r := range partRanges {
		if r.start == -1 {
			continue
		}

		m.wg.Add(1)
		sem <- struct{}{}

		go func(partNum int, start, end int64) {
			defer func() {
				<-sem
				m.wg.Done()
			}()

			etag, err := m.uploadPart(partNum, start, end)
			if err != nil {
				errorChan <- fmt.Errorf("part %d: %w", partNum, err)
				return
			}

			m.mu.Lock()
			m.Etags[partNum-1] = etag
			m.mu.Unlock()
		}(i+1, r.start, r.end)
	}

	go func() {
		m.wg.Wait()
		close(errorChan)
	}()

	for err := range errorChan {
		m.mu.Lock()
		m.errors = append(m.errors, err)
		m.mu.Unlock()
	}

	if len(m.errors) > 0 {
		errorString := ""
		for _, err := range m.errors {
			errorString += fmt.Sprintf("- %v\n", err)
		}
		return fmt.Errorf("%d parts failed:\n%s", len(m.errors), errorString)
	}
	return nil
}

func (m *MultipartUpload) uploadPart(partNumber int, start, end int64) (string, error) {
	file, err := os.Open(m.Path)
	if err != nil {
		return "", fmt.Errorf("file open error: %w", err)
	}
	defer file.Close()

	if _, err := file.Seek(start, 0); err != nil {
		return "", fmt.Errorf("seek error: %w", err)
	}

	pr, pw := io.Pipe()
	defer pr.Close()

	go func() {
		defer pw.Close()
		bufPtr := m.bufferPool.Get().(*[]byte)
		defer m.bufferPool.Put(bufPtr)

		_, err := io.CopyBuffer(pw, &progressTracker{
			Reader: io.LimitReader(file, end-start+1),
			size:   &m.UploadedSize,
		}, *bufPtr)
		if err != nil {
			pw.CloseWithError(err)
		}
	}()

	req, err := http.NewRequestWithContext(m.ctx, "PUT", m.SignedURLs[partNumber-1], pr)
	if err != nil {
		return "", fmt.Errorf("request creation failed: %w", err)
	}
	req.ContentLength = end - start + 1

	resp, err := m.client.Do(req)
	if err != nil {
		if m.ctx.Err() != nil {
			return "", fmt.Errorf("upload cancelled")
		}
		return "", fmt.Errorf("upload failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("status %d", resp.StatusCode)
	}

	etag := strings.Trim(resp.Header.Get("ETag"), `"`)
	if etag == "" {
		return "", fmt.Errorf("missing ETag")
	}

	return etag, nil
}

func (m *MultipartUpload) calculatePartRanges() []partRange {
	ranges := make([]partRange, m.NoOfParts())
	for i := range ranges {
		start := int64(i) * m.PartSize
		end := start + m.PartSize - 1

		if start >= m.TotalSize {
			ranges[i] = partRange{-1, -1}
			continue
		}

		if end >= m.TotalSize {
			end = m.TotalSize - 1
		}

		ranges[i] = partRange{start, end}
	}
	return ranges
}

func (m *MultipartUpload) Complete(s *Session) error {
	if m.IsUploaded() {
		// If it's already uploaded, silently ignore
		return nil
	}
	parts := make([]map[string]any, 0, len(m.Etags))
	for i, etag := range m.Etags {
		if etag != "" {
			parts = append(parts, map[string]any{
				"ETag":       etag,
				"PartNumber": i + 1,
			})
		}
	}

	partJsonBytes, err := json.Marshal(parts)
	if err != nil {
		return fmt.Errorf("failed to marshal parts: %w", err)
	}

	_, err = s.SendRequest("press.api.site.multipart_exit", map[string]any{
		"file":   m.Key,
		"id":     m.UploadID,
		"action": "complete",
		"parts":  string(partJsonBytes),
	})
	if err != nil {
		return fmt.Errorf("completion failed: %w", err)
	}

	res, err := s.SendRequest("press.api.site.uploaded_backup_info", map[string]any{
		"file": m.FileName,
		"path": m.Key,
		"type": m.MimeType,
		"size": m.TotalSize,
	})
	if err != nil {
		return fmt.Errorf("remote file creation failed: %w", err)
	}

	m.RemoteFile = getString(res, "message")
	if m.RemoteFile == "" {
		return fmt.Errorf("remote file creation returned empty path")
	}

	s.UploadedFiles[m.CacheKey()] = m.RemoteFile
	if err := s.Save(); err != nil {
		return fmt.Errorf("failed to save uploaded files: %w", err)
	}
	return nil
}

func (m *MultipartUpload) Abort(s *Session) {
	m.Cancel()
	m.abortPresignedURLs(s)
}

func (m *MultipartUpload) abortPresignedURLs(s *Session) {
	_, _ = s.SendRequest("press.api.site.complete_multipart_upload", map[string]any{
		"file":   m.Key,
		"id":     m.UploadID,
		"action": "abort",
	})
}

func (m *MultipartUpload) Cancel() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.cancelFn != nil {
		m.cancelFn()
	}
}

func (m *MultipartUpload) Progress() (float64, string, string) {
	if m.TotalSize == 0 {
		return 0, "", ""
	}
	return float64(atomic.LoadInt64(&m.UploadedSize)) / float64(m.TotalSize), formatBytes(m.UploadedSize), formatBytes(m.TotalSize)
}

func (m *MultipartUpload) Errors() []error {
	m.mu.Lock()
	defer m.mu.Unlock()
	return append([]error(nil), m.errors...)
}
