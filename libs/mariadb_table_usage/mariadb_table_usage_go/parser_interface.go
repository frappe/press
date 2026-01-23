package main

type Output struct {
	DataLength  uint64 `json:"data_length"`
	IndexLength uint64 `json:"index_length"`
	DataFree    uint64 `json:"data_free"`
	Engine      string `json:"engine"`
	Filename    string `json:"filename"`
}

type Parser interface {
	Run() error
	GetStats() (uint64, uint64, uint64)
}
