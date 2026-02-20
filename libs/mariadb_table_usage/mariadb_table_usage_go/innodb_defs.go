package main

import "encoding/binary"

const (
	// FSP_HEADER_OFFSET is the offset of the File Space Header within page 0
	FSP_HEADER_OFFSET = 38

	// FSP_EXTENT_SIZE is the number of pages in one extent
	FSP_EXTENT_SIZE = 64

	// FIL_PAGE_TYPE is the offset of the page type field in the file header
	FIL_PAGE_TYPE = 24

	// FIL_NULL is a special value used to represent a null pointer in InnoDB
	FIL_NULL = 0xFFFFFFFF

	// PAGE_HEADER is the offset where the page-specific header begins
	// This is after the FIL header (38 bytes)
	PAGE_HEADER = 38

	// PAGE_BTR_SEG_LEAF points to the segment inode for B-tree leaf pages
	PAGE_BTR_SEG_LEAF = 36

	// PAGE_BTR_SEG_TOP points to the segment inode for B-tree non-leaf pages
	PAGE_BTR_SEG_TOP = 46

	// File Space Header Offsets (Relative to FSP_HEADER_OFFSET)
	// reference: server/storage/innobase/include/fsp0fsp.h

	FSP_SPACE_ID = 0
	FSP_NOT_USED = 4

	// FSP_SIZE: current size of the tablespace in pages (4 bytes)
	FSP_SIZE = 8 // Current size of the tablespace in pages

	// FSP_FREE_LIMIT: Pages >= this limit are considered free (4 bytes)
	// These pages haven't been initialized yet.
	FSP_FREE_LIMIT = 12

	// FSP_SPACE_FLAGS: Tablespace flags (4 bytes)
	// Contains information about page size, compression, etc.
	FSP_SPACE_FLAGS = 16

	// FSP_FRAG_N_USED: Number of used pages in FSP_FREE_FRAG list (4 bytes)
	FSP_FRAG_N_USED = 20

	// FSP_FREE: List of completely free extents
	FSP_FREE = 24

	// FSP_FREE_FRAG: List of partially free extents
	FSP_FREE_FRAG = 40

	// FSP_FULL_FRAG: List of fully used fragment extents
	FSP_FULL_FRAG = 56

	// FSP_SEG_ID: Next segment ID to be assigned
	FSP_SEG_ID = 72

	// FSP_SEG_INODES_FULL: List of inode pages where all slots are used
	FSP_SEG_INODES_FULL = 80

	// FSP_SEG_INODES_FREE: List of inode pages with free slots
	FSP_SEG_INODES_FREE = 96

	// Tablespace Flags Constants
	// used to decode the FSP_SPACE_FLAGS field
	// reference: server/storage/innobase/include/fsp0types.h

	// FSP_FLAGS_POS_POST_ANTELOPE: Bit position for post-Antelope format flag
	FSP_FLAGS_POS_POST_ANTELOPE = 0

	// FSP_FLAGS_MASK_POST_ANTELOPE: Mask for post-Antelope flag (bit 0)
	FSP_FLAGS_MASK_POST_ANTELOPE = 0x1

	// FSP_FLAGS_POS_ZIP_SSIZE: Bit position for compressed page size
	FSP_FLAGS_POS_ZIP_SSIZE = 1

	// FSP_FLAGS_MASK_ZIP_SSIZE: Mask for ZIP_SSIZE (bits 1-4)
	// If non-zero: page_size = 512 << ZIP_SSIZE
	FSP_FLAGS_MASK_ZIP_SSIZE = 0x1E

	// FSP_FLAGS_POS_PAGE_SSIZE: Bit position for uncompressed page size
	FSP_FLAGS_POS_PAGE_SSIZE = 6

	// FSP_FLAGS_MASK_PAGE_SSIZE: Mask for PAGE_SSIZE (bits 6-9)
	// Values: 1=4K, 2=8K, 3=16K, 4=32K, 5=64K
	FSP_FLAGS_MASK_PAGE_SSIZE = 0x3C0

	// Flie based List Node (FLST) Constants
	// reference: server/storage/innobase/include/fut0lst.h

	// FLST_PREV: Offset of the previous node pointer (6 bytes : page + offset)
	FLST_PREV = 0

	// FLST_NEXT: Offset of the next node pointer (6 bytes : page + offset)
	FLST_NEXT = 6

	// FLST_NODE_SIZE: Total size of a list node (12 bytes)
	FLST_NODE_SIZE = 12

	// FLST_LEN: Length (number of nodes) in the list (4 bytes)
	FLST_LEN = 0

	// FLST_FIRST: Pointer to first node (6 bytes : page + offset)
	FLST_FIRST = 4

	// FLST_LAST: Pointer to last node (6 bytes : page + offset)
	FLST_LAST = 10

	// FLST_BASE_NODE_SIZE: Total size of a list base node (16 bytes)
	// Calculation: 4 (len) + 6 (first) + 6 (last) = 16
	FLST_BASE_NODE_SIZE = 16

	// Segment Inode Page Constants
	// reference: server/storage/innobase/include/fsp0fsp.h

	// FSEG_INODE_PAGE_NODE: Offset of the list node linking inode pages (12 bytes)
	FSEG_INODE_PAGE_NODE = 38

	// FSEG_ARR_OFFSET: Offset where the array of segment inodes begins
	// Calculation: FSEG_INODE_PAGE_NODE + FLST_NODE_SIZE = 38 + 12 = 50
	FSEG_ARR_OFFSET = 50

	// FSEG_INODE_SIZE: Size of each segment inode (192 bytes)
	// Reference: fsp0fsp.h - FSEG_INODE_SIZE
	FSEG_INODE_SIZE = 192

	// FSEG_INODES_PER_PAGE: Number of inodes that fit in one page
	// For 16KB page: (16384 - 50) / 192 ≈ 85
	FSEG_INODES_PER_PAGE = 85

	// Segment Inode Structure Offsets
	// reference: server/storage/innobase/include/fsp0fsp.h

	// FSEG_ID: Segment ID, 0 if this inode is unused (8 bytes)
	FSEG_ID = 0

	// FSEG_NOT_FULL_N_USED: Pages used in FSEG_NOT_FULL extents (4 bytes)
	FSEG_NOT_FULL_N_USED = 8

	// FSEG_FREE: List of free extents belonging to this segment (16 bytes)
	// These extents have all pages available for use.
	FSEG_FREE = 12

	// FSEG_NOT_FULL: List of partially used extents (16 bytes) (Offset: 12 + 16 = 28)
	FSEG_NOT_FULL = 28

	// FSEG_FULL: List of fully used extents (16 bytes) (Offset: 28 + 16 = 44)
	FSEG_FULL = 44

	// FSEG_MAGIC_N: Magic number for validation (4 bytes) (Offset: 44 + 16 = 60)
	FSEG_MAGIC_N = 60

	// FSEG_FRAG_ARR: Array of fragment page numbers (32 × 4 bytes = 128 bytes) (Offset: 60 + 4 = 64)
	// fragment pages are individually allocated pages (not part of any extents)
	FSEG_FRAG_ARR = 64

	// FSEG_MAGIC_N_VALUE is the expected magic number value
	// used to validate that an inode is properly initialized or whether the parser has parsed the correct structure
	// reference: server/storage/innobase/include/fsp0fsp.h - FSEG_MAGIC_N_VALUE
	FSEG_MAGIC_N_VALUE = 97937874

	// FSEG_FRAG_ARR_N_SLOTS: Number of slots in the fragment array
	// reference: server/storage/innobase/include/fsp0fsp.h - FSEG_FRAG_ARR_N_SLOTS
	FSEG_FRAG_ARR_N_SLOTS = FSP_EXTENT_SIZE / 2
)

type FileAddr struct {
	Page   uint32 // page number (4 bytes)
	Offset uint16 // byte offset within the page (2 bytes)
}

// ListBaseNode represents the "head" of a file-based linked list
type ListBaseNode struct {
	Length uint32   // number of nodes in the list
	First  FileAddr // pointer to first node
	Last   FileAddr // pointer to last node
}

// SegmentInode represents metadata about a single segment.
// The inode tracks all space allocated to that segment.
// reference: server/storage/innobase/include/fsp0fsp.h - fseg_inode_t
type SegmentInode struct {
	ID             uint64   // unique segment identifier
	NotFullNUsed   uint32   // pages used in NOT_FULL extents
	FreeListLen    uint32   // number of free extents
	NotFullListLen uint32   // number of partially-full extents
	FullListLen    uint32   // number of full extents
	MagicNumber    uint32   // validation magic number
	FragPages      int      // count of individually allocated pages
	FragPageIDs    []uint32 // page numbers of fragment pages
}

// parseFileAddr reads a 6-byte file address from the given data.
func parseFileAddr(data []byte) FileAddr {
	return FileAddr{
		Page:   binary.BigEndian.Uint32(data[0:4]),
		Offset: binary.BigEndian.Uint16(data[4:6]),
	}
}

// parseListBaseNode reads a 16-byte list base node from the given data
func parseListBaseNode(data []byte) ListBaseNode {
	return ListBaseNode{
		Length: binary.BigEndian.Uint32(data[0:4]),
		First:  parseFileAddr(data[4:10]),
		Last:   parseFileAddr(data[10:16]),
	}
}

// parseSegmentInode reads a 192-byte segment inode from the given data
// this extracts all the metadata needed to calculate the segment's size
func parseSegmentInode(data []byte) SegmentInode {
	inode := SegmentInode{}
	inode.ID = binary.BigEndian.Uint64(data[FSEG_ID:])
	inode.NotFullNUsed = binary.BigEndian.Uint32(data[FSEG_NOT_FULL_N_USED:])

	// read list lengths from the first 4 bytes of each list base node
	inode.FreeListLen = binary.BigEndian.Uint32(data[FSEG_FREE:])
	inode.NotFullListLen = binary.BigEndian.Uint32(data[FSEG_NOT_FULL:])
	inode.FullListLen = binary.BigEndian.Uint32(data[FSEG_FULL:])

	inode.MagicNumber = binary.BigEndian.Uint32(data[FSEG_MAGIC_N:])

	// count fragment pages by scanning the FSEG_FRAG_ARR array
	// each slot is 4 bytes and there are FSEG_FRAG_ARR_N_SLOTS slots
	fragCount := 0
	fragOff := FSEG_FRAG_ARR
	inode.FragPageIDs = make([]uint32, 0, FSEG_FRAG_ARR_N_SLOTS)
	for range FSEG_FRAG_ARR_N_SLOTS {
		p := binary.BigEndian.Uint32(data[fragOff : fragOff+4])
		if p != FIL_NULL {
			fragCount++
			inode.FragPageIDs = append(inode.FragPageIDs, p)
		}
		fragOff += 4
	}
	inode.FragPages = fragCount

	return inode
}
