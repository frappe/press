package main

import (
	"encoding/binary"
	"os"
	"syscall"
)

type InnoDBParser struct {
	file     *os.File
	filename string

	pageSize int64

	dataLength  uint64
	indexLength uint64
	dataFree    uint64

	clusterIndexTopID  uint64 // segment ID for clustered index non-leaf pages
	clusterIndexLeafID uint64 // segment ID for clustered index leaf pages

	visitedPages map[uint32]bool
	pageCache    map[uint32][]byte

	ioThreshold float64        // disk IO utilization threshold for throttling
	rateLimiter *IORateLimiter // IO rate limiter for throttling reads
}

const DefaultIOMaxOpsPerSecond = 200.0

func NewInnoDBParser(filename string, ioThreshold float64) (*InnoDBParser, error) {
	return NewInnoDBParserWithRateLimit(filename, ioThreshold, DefaultIOMaxOpsPerSecond)
}

func NewInnoDBParserWithRateLimit(filename string, ioThreshold float64, maxIOOpsPerSecond float64) (*InnoDBParser, error) {
	file, err := os.OpenFile(filename, os.O_RDONLY|syscall.O_DIRECT, 0)
	if err != nil {
		return nil, err
	}
	return &InnoDBParser{
		file:         file,
		filename:     filename,
		pageSize:     16384, // default to 16KB, will be detected
		visitedPages: make(map[uint32]bool),
		pageCache:    make(map[uint32][]byte),
		ioThreshold:  ioThreshold,
		rateLimiter:  NewIORateLimiter(maxIOOpsPerSecond),
	}, nil
}

func (p *InnoDBParser) Run() error {
	p.detectPageSize()

	page0 := p.readPage(0)
	segInodesFull := parseListBaseNode(page0[FSP_HEADER_OFFSET+FSP_SEG_INODES_FULL:])
	segInodesFree := parseListBaseNode(page0[FSP_HEADER_OFFSET+FSP_SEG_INODES_FREE:])
	leafSegPage, topSegPage := p.findClusteredIndex()

	p.traverseInodes(segInodesFull)
	p.traverseInodes(segInodesFree)

	p.checkInodePage(leafSegPage)
	p.checkInodePage(topSegPage)

	// Handle empty tables (at least count one page for the root)
	if p.dataLength == 0 {
		stat, _ := p.file.Stat()
		if stat.Size() >= 4*int64(p.pageSize) {
			p.dataLength += uint64(p.pageSize)
		}
	}

	p.calculateDataFree(page0)

	return nil
}

func (p *InnoDBParser) Close() {
	p.file.Close()
	p.pageCache = nil
}

func (p *InnoDBParser) GetStats() (uint64, uint64, uint64) {
	return p.dataLength, p.indexLength, p.dataFree
}

// readPage reads a single page from the tablespace.
// follows the IO throttling criteria by pausing when disk is busy.
func (p *InnoDBParser) readPage(pageNumber uint32) []byte {
	// return cached page if available
	if cached, ok := p.pageCache[pageNumber]; ok {
		return cached
	}

	if p.rateLimiter != nil {
		p.rateLimiter.Wait()
	}

	// check disk IO utilization and pause if too high
	err := CheckLowIOOrPause(p.ioThreshold, func() {
		p.file.Close()
	}, func() error {
		f, err := os.OpenFile(p.filename, os.O_RDONLY|syscall.O_DIRECT, 0)
		if err != nil {
			return err
		}
		p.file = f
		return nil
	})
	if err != nil {
		panic(err)
	}

	// seek to the page offset and read
	offset := int64(pageNumber) * p.pageSize
	_, err = p.file.Seek(offset, 0)
	if err != nil {
		panic(err)
	}

	pageData := makeAligned(int(p.pageSize))
	_, err = p.file.Read(pageData)
	if err != nil {
		panic(err)
	}

	// cache the page for future reads
	p.pageCache[pageNumber] = pageData
	return pageData
}

// detectPageSize reads the FSP flags from page 0 and determines the page size.
//
// innoDB has different kind of page format which has different page size:
//   - antelope format: Always 16KB
//   - barracuda format: 4K, 8K, 16K, 32K, or 64K
//   - compressed: 1K, 2K, 4K, 8K, 16K, 32K
//
// reference: storage/innobase/include/fsp0types.h
func (p *InnoDBParser) detectPageSize() {
	// page 0 (FSP Header) will be always 16KB regardless of any configuration
	initialReadSize := int64(16384)

	stat, _ := p.file.Stat()
	if stat.Size() < initialReadSize {
		initialReadSize = stat.Size()
	}

	page0Data := makeAligned(int(initialReadSize))
	_, err := p.file.ReadAt(page0Data, 0)
	if err != nil {
		panic(err)
	}

	// parse FSP_SPACE_FLAGS field
	// reference: fsp0types.h - structure of FSP_SPACE_FLAGS
	flags := binary.BigEndian.Uint32(page0Data[FSP_HEADER_OFFSET+FSP_SPACE_FLAGS:])

	// check if POST_ANTELOPE format (bit 0)
	// pre-antelope (MySQL < 5.0) always used 16KB pages
	isPostAntelope := (flags & FSP_FLAGS_MASK_POST_ANTELOPE) != 0

	// extract ZIP_SSIZE (bits 1-4) for compressed page size
	zipSSIZE := (flags & FSP_FLAGS_MASK_ZIP_SSIZE) >> FSP_FLAGS_POS_ZIP_SSIZE

	// extract PAGE_SSIZE (bits 6-9) for uncompressed page size
	pageSSIZE := (flags & FSP_FLAGS_MASK_PAGE_SSIZE) >> FSP_FLAGS_POS_PAGE_SSIZE

	if !isPostAntelope {
		p.pageSize = 16384
	} else {
		isCompressed := false

		// check for compressed tablespace
		// ZIP_SSIZE > 0 means compressed; page_size = 512 << ZIP_SSIZE
		if zipSSIZE > 0 && zipSSIZE <= 7 {
			p.pageSize = 512 << zipSSIZE
			isCompressed = true
		}

		// if not compressed, use PAGE_SSIZE
		if !isCompressed {
			switch pageSSIZE {
			case 1:
				p.pageSize = 4096 // 4KB
			case 2:
				p.pageSize = 8192 // 8KB
			case 3:
				p.pageSize = 16384 // 16KB (default)
			case 4:
				p.pageSize = 32768 // 32KB
			case 5:
				p.pageSize = 65536 // 64KB
			default:
				p.pageSize = 16384 // Default to 16KB
			}
		}
	}

	// cache page 0 if we read enough data
	if int64(len(page0Data)) == p.pageSize {
		p.pageCache[0] = page0Data
	} else if p.pageSize < int64(len(page0Data)) {
		p.pageCache[0] = page0Data[:p.pageSize]
	}
}

// findClusteredIndex reads the clustered index (PRIMARY KEY) root page
// and extracts the segment IDs for the leaf and non-leaf segments.
// clustered index is always page 3 while using file-per-table tablespace
//
// structure of segment header (10 bytes at PAGE_BTR_SEG_LEAF and PAGE_BTR_SEG_TOP):
//   - Bytes 0-3: Space ID (unnecessary for file-per-table tablespace)
//   - Bytes 4-7: Page number of inode page
//   - Bytes 8-9: Offset within inode page
//
// returns (no of leaf segment pages, no of non-leaf segment pages)
// reference: storage/innobase/include/fsp0types.h - FSEG_HDR_* constants
func (p *InnoDBParser) findClusteredIndex() (uint32, uint32) {
	page3 := p.readPage(3)

	// read leaf segment header (for leaf pages of the B-tree)
	leafSegOffset := PAGE_HEADER + PAGE_BTR_SEG_LEAF // PAGE_HEADER (38) + PAGE_BTR_SEG_LEAF (36) = 74
	leafSegPage := binary.BigEndian.Uint32(page3[leafSegOffset+4 : leafSegOffset+8])
	leafSegInodeOffset := binary.BigEndian.Uint16(page3[leafSegOffset+8 : leafSegOffset+10])

	// read the segment inodes and store its ID
	if leafSegPage != FIL_NULL {
		leafInodePage := p.readPage(leafSegPage)
		leafInodeData := leafInodePage[leafSegInodeOffset : leafSegInodeOffset+FSEG_INODE_SIZE]
		ciLeafInode := parseSegmentInode(leafInodeData)
		p.clusterIndexLeafID = ciLeafInode.ID
	}

	// read top segment header (for non-leaf pages of the B-tree)
	topSegOffset := PAGE_HEADER + PAGE_BTR_SEG_TOP // PAGE_HEADER (38) + PAGE_BTR_SEG_TOP (46) = 84
	topSegPage := binary.BigEndian.Uint32(page3[topSegOffset+4 : topSegOffset+8])
	topSegInodeOffset := binary.BigEndian.Uint16(page3[topSegOffset+8 : topSegOffset+10])

	if topSegPage != FIL_NULL {
		topInodePage := p.readPage(topSegPage)
		topInodeData := topInodePage[topSegInodeOffset : topSegInodeOffset+FSEG_INODE_SIZE]
		ciTopInode := parseSegmentInode(topInodeData)
		p.clusterIndexTopID = ciTopInode.ID
	}

	return leafSegPage, topSegPage
}

// scanInodePage scans all segment inodes on an inode page and accumulates sizes.
//
// each inode page contains up to 85 segment inodes (FSEG_INODES_PER_PAGE).
// for each valid inode, we calculate its reserved space and segregate
//
// reference: storage/innobase/fsp/fsp0fsp.cc - fseg_n_reserved_pages_low()
func (p *InnoDBParser) scanInodePage(limit int, pageData []byte) {
	for i := range limit {
		offset := FSEG_ARR_OFFSET + i*FSEG_INODE_SIZE
		inodeData := pageData[offset : offset+FSEG_INODE_SIZE]
		inode := parseSegmentInode(inodeData)

		// skip unused inodes (ID=0) or inodes with wrong magic number
		if inode.ID == 0 || inode.MagicNumber != FSEG_MAGIC_N_VALUE {
			continue
		}

		// reserved = frag_pages + extent_size * (free + not_full + full)
		//
		// fragment pages: individually allocated pages (not in extents)
		// each extent list length is the count of extents in that list
		// each extent contains FSP_EXTENT_SIZE (64) pages
		allocatedPages := (uint64(inode.FullListLen+inode.NotFullListLen+inode.FreeListLen)*uint64(FSP_EXTENT_SIZE) + uint64(inode.FragPages))
		sizeBytes := allocatedPages * uint64(p.pageSize)

		if inode.ID == p.clusterIndexLeafID || inode.ID == p.clusterIndexTopID {
			// data_length = Clustered index segments (leaf + top)
			// primary index also gets counted in data_length
			p.dataLength += sizeBytes
		} else {
			// index_length = All other segments (secondary indexes)
			p.indexLength += sizeBytes
		}
	}
}

// traverseInodes walks a linked list of inode pages and scans all inodes.
//
// the FSP header contains two lists of inode pages:
//   - FSP_SEG_INODES_FULL: pages where all 85 inode slots are used
//   - FSP_SEG_INODES_FREE: pages with at least one free slot
//
// together, these lists contain ALL segment inodes in the tablespace.
//
// structure of each inode page:
//   - offset 38: list node (12 bytes) linking to prev/next inode pages
//   - offset 50: array of 85 segment inodes (192 bytes each)
func (p *InnoDBParser) traverseInodes(list ListBaseNode) {
	if list.Length == 0 {
		return
	}

	curr := list.First
	for curr.Page != FIL_NULL { // FIL_NULL indicates end of list
		if p.visitedPages[curr.Page] {
			// skip if already visited (prevents infinite loops)
			break
		}
		p.visitedPages[curr.Page] = true

		pageData := p.readPage(curr.Page)
		p.scanInodePage(FSEG_INODES_PER_PAGE, pageData)

		if int(curr.Offset)+FLST_NODE_SIZE <= len(pageData) {
			nodeData := pageData[curr.Offset : curr.Offset+FLST_NODE_SIZE]
			curr = parseFileAddr(nodeData[FLST_NEXT:]) // FLST_NEXT gives the next pointer
		} else {
			curr = p.getNextNode(curr)
		}
	}
}

// getNextNode reads the next pointer from a list node.
func (p *InnoDBParser) getNextNode(addr FileAddr) FileAddr {
	if addr.Page == FIL_NULL {
		return FileAddr{FIL_NULL, 0}
	}
	page := p.readPage(addr.Page)
	nodeData := page[addr.Offset : addr.Offset+FLST_NODE_SIZE]
	return parseFileAddr(nodeData[FLST_NEXT:])
}

// calculateDataFree calculates the free space in the tablespace.
//
// free space consists of :
//   - free extents in the FSP_FREE list
//   - uninitialized pages above FSP_FREE_LIMIT
//   - remove reserved extents for tablespace overhead
//
// the reserved extents formula according to mariadb source code:
// reserve = 2 + (size_in_extents * 2) / 200
// this reserves about 1% of space plus 2 extents for metadata
//
// reference: storage/innobase/fsp/fsp0fsp.cc - fsp_reserve_free_extents()
func (p *InnoDBParser) calculateDataFree(page0 []byte) {
	// read FSP header fields
	fspSize := binary.BigEndian.Uint32(page0[FSP_HEADER_OFFSET+FSP_SIZE:])
	fspFreeLimit := binary.BigEndian.Uint32(page0[FSP_HEADER_OFFSET+FSP_FREE_LIMIT:])
	fspFree := parseListBaseNode(page0[FSP_HEADER_OFFSET+FSP_FREE:])

	// calculate free extents above the free limit
	// these are pages that haven't been initialized yet
	var nFreeUp uint64 = 0
	if fspSize > fspFreeLimit {
		nFreeUp = uint64(fspSize-fspFreeLimit) / FSP_EXTENT_SIZE
	}

	// subtract overhead for extent descriptors
	// every 256 extents, one extent is used for XDES pages
	if nFreeUp > 0 {
		nFreeUp--
		nFreeUp -= nFreeUp / 256
	}

	// calculate tablespace overhead
	sizeInExtents := uint64(fspSize) / FSP_EXTENT_SIZE
	reserve := 2 + (sizeInExtents*2)/200

	// total free = free list + uninitialized - reserved
	nFree := uint64(fspFree.Length) + nFreeUp

	if nFree > uint64(reserve) {
		p.dataFree = (nFree - uint64(reserve)) * FSP_EXTENT_SIZE * uint64(p.pageSize)
	}
}

// checkInodePage scans an inode page if it wasn't already visited.
// This catches edge cases where the inode page containing the
// clustered index segment isn't in the main inode lists.
func (p *InnoDBParser) checkInodePage(pageNum uint32) {
	if pageNum != FIL_NULL && !p.visitedPages[pageNum] {
		stat, _ := p.file.Stat()
		if uint64(pageNum)*uint64(p.pageSize) < uint64(stat.Size()) {
			pageData := p.readPage(pageNum)
			p.scanInodePage(FSEG_INODES_PER_PAGE, pageData)
		}
	}
}
