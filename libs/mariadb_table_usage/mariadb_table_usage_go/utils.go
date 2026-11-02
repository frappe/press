package main

import "unsafe"

func makeAligned(size int) []byte {
	alignment := 4096
	block := make([]byte, size+alignment)

	p := unsafe.Pointer(&block[0])
	rem := uintptr(p) % uintptr(alignment)
	offset := 0
	if rem != 0 {
		offset = alignment - int(rem)
	}
	return block[offset : offset+size]
}
