package main

import (
	"C"
	"io"
	"log"
	"os"
	"sync"
	"syscall"
	"time"

	"github.com/iceber/iouring-go"
	"golang.org/x/sys/unix"
)
import "unsafe"

// const blockSize int64 = 1024 * 256          // 256 KB
// const psyncWorkersCount int = 4             // Number of workers
// const smallFileSize int64 = 1024 * 1024 * 2 // 2MB

type FileIOMethod string

const (
	PosixSync FileIOMethod = "psync"
	IOUring   FileIOMethod = "io_uring"
)

type FileReadRequest struct {
	fd     int
	offset int64
}

func main() {}

//export WarmupFiles
func WarmupFiles(filePaths **C.char, filePathCount C.int, method *C.char, smallFileSizeThreshold C.long, blockSizeForSmallFiles C.long, blockSizeForLargeFiles C.long, smallFilesWorkerCount C.int, largeFilesWorkerCount C.int, loggingEnabled C.int) {
	// Convert the C char array back to a Go slice
	length := int(filePathCount)
	tmpSlice := (*[1 << 30]*C.char)(unsafe.Pointer(filePaths))[:length:length]
	goFilePaths := make([]string, length)
	for i := 0; i < length; i++ {
		goFilePaths[i] = C.GoString(tmpSlice[i])
	}

	// Call the Go function with converted values
	warmupFiles(goFilePaths, FileIOMethod(C.GoString(method)), int64(smallFileSizeThreshold), int64(blockSizeForSmallFiles), int64(blockSizeForLargeFiles), int(smallFilesWorkerCount), int(largeFilesWorkerCount), int(loggingEnabled) == 1)
}

func warmupFiles(filePaths []string, method FileIOMethod, smallFileSizeThreshold int64, blockSizeForSmallFiles int64, blockSizeForLargeFiles int64, smallFilesWorkerCount int, largeFilesWorkerCount int, loggingEnabled bool) {
	var logger = log.New(os.Stdout, "", log.LstdFlags)

	var totalFileSize int64
	var startTime = time.Now()

	var files []*os.File
	for _, filePath := range filePaths {
		// Open file with O_DIRECT and O_RDONLY
		// To prevent going through disk cache + prevent modification to file
		// Disk cache is useless as on the system free memory will be less
		// And reading large file will add/remove cache and slow down system and the whole process
		file, err := os.OpenFile(filePath, os.O_RDONLY|syscall.O_DIRECT, 0)
		if err != nil {
			if loggingEnabled {
				logger.Printf("Error opening file: %v\n", err)
			}
			continue
		}
		defer file.Close()
		files = append(files, file)
	}

	// Separate small and large files
	var smallFiles []*os.File
	var largeFiles []*os.File
	for _, file := range files {
		fileInfo, err := file.Stat()
		if err != nil {
			logger.Printf("Error getting file info: %v\n", err)
			continue
		}
		if fileInfo.Size() <= smallFileSizeThreshold {
			smallFiles = append(smallFiles, file)
		} else {
			largeFiles = append(largeFiles, file)
		}
		totalFileSize += fileInfo.Size()
	}

	var wg sync.WaitGroup
	wg.Add(2)

	// Always run a single thread for small files
	warmupFileGroup(smallFiles, method, blockSizeForSmallFiles, smallFilesWorkerCount, &wg, logger, loggingEnabled)
	warmupFileGroup(largeFiles, method, blockSizeForLargeFiles, largeFilesWorkerCount, &wg, logger, loggingEnabled)

	// Log stats
	if loggingEnabled {
		totalData := (float64(totalFileSize) / 1024 / 1024) // MB
		duration := time.Since(startTime)
		logger.Printf("~~~ Overall Stats ~~~ \n")
		logger.Printf("Total time: %.2f seconds\n", duration.Seconds())
		logger.Printf("Total data: %.2f MB\n", totalData)
		logger.Printf("Average throughput: %.2f MB/s\n", totalData/duration.Seconds())
	}

}

func warmupFileGroup(files []*os.File, method FileIOMethod, blockSize int64, workersCount int, wg *sync.WaitGroup, logger *log.Logger, loggingEnabled bool) {
	defer wg.Done()

	if len(files) == 0 {
		if loggingEnabled {
			logger.Println("No files to warmup")
		}
		return
	}

	// Find the largest file size
	// To calculate length of channel
	var largestFileSize int64
	for _, file := range files {
		fileInfo, err := file.Stat()
		if err == nil {
			fileSize := fileInfo.Size()
			if fileSize > largestFileSize {
				largestFileSize = fileSize
			}
		}
	}

	// Create a channel for block numbers
	numBlocks := (largestFileSize + blockSize - 1) / blockSize
	blockChan := make(chan FileReadRequest, min(workersCount*2, int(numBlocks)))

	// Create a WaitGroup to wait for all workers to finish
	var workerWg sync.WaitGroup

	// Start workers
	for i := 0; i < workersCount; i++ {
		workerWg.Add(1)
		go warmupWorker(blockChan, blockSize, &workerWg, method, logger)
	}

	for _, file := range files {
		if loggingEnabled {
			logger.Printf("Warming up file: %s\n", file.Name())
		}

		fd := int(file.Fd())

		// Tell the kernel to not cache the file
		// Avoid high memory usage during the block reads
		// https://man7.org/linux/man-pages/man2/posix_fadvise.2.html
		err := unix.Fadvise(fd, 0, 0, unix.FADV_DONTNEED)
		if err != nil {
			logger.Printf("Error fadvise: %v\n", err)
			continue
		}

		// Send block numbers to channel to be processed
		for blockNum := int64(0); blockNum < numBlocks; blockNum++ {
			blockChan <- FileReadRequest{fd: fd, offset: blockNum * blockSize}
		}

	}

	// Close the channel
	close(blockChan)

	// Wait for all workers to finish
	workerWg.Wait()
}

func warmupWorker(blockChan chan FileReadRequest, blockSize int64, wg *sync.WaitGroup, method FileIOMethod, logger *log.Logger) {
	defer wg.Done()

	// Create buffer for each worker
	// To avoid internal sync lock on buffer pool sync.pool
	buffer := make([]byte, blockSize)

	var prepRequests []iouring.PrepRequest
	var iour *iouring.IOURing
	var err error

	if method == IOUring {
		prepRequests = make([]iouring.PrepRequest, 0, 64)
		iour, err = iouring.New(68) // Keep some extra space
		if err != nil {
			logger.Printf("Error creating iouring: %v\n", err)
			return
		}
		defer iour.Close()
	}

	for details := range blockChan {
		// Submit requests in batches of 64
		if method == IOUring {
			req := iouring.Pread(details.fd, buffer, uint64(details.offset))
			prepRequests = append(prepRequests, req)
			if len(prepRequests) >= 64 {
				request, err := iour.SubmitRequests(prepRequests, nil)
				if err != nil {
					logger.Printf("Error submitting requests: %v\n", err)
					continue
				}
				<-request.Done()
				prepRequests = prepRequests[:0]
			}
		}

		// Just read blocks one by one in case of PosixSync
		if method == PosixSync {
			_, err := unix.Pread(details.fd, buffer, details.offset)
			if err != nil && err != syscall.EIO && err != io.EOF {
				logger.Printf("Error reading block at offset %d: %v\n", details.offset, err)
				continue
			}
		}
	}

	if method == IOUring {
		// Submit any remaining requests
		if len(prepRequests) > 0 {
			request, err := iour.SubmitRequests(prepRequests, nil)
			if err != nil {
				logger.Printf("Error submitting requests: %v\n", err)
				return
			}
			<-request.Done()
		}
	}
}
