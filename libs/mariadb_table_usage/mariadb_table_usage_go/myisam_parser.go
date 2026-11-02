package main

import (
	"os"
)

type MyISAMParser struct {
	mydPath     string
	myiPath     string
	dataLength  uint64
	indexLength uint64
}

func NewMyISAMParser(mydPath, myiPath string) *MyISAMParser {
	return &MyISAMParser{
		mydPath: mydPath,
		myiPath: myiPath,
	}
}

func (p *MyISAMParser) Run() error {
	// Data Length is size of .MYD
	mydStat, err := os.Stat(p.mydPath)
	if err != nil {
		return err
	}
	p.dataLength = uint64(mydStat.Size())

	// Index Length is size of .MYI
	myiStat, err := os.Stat(p.myiPath)
	if err == nil {
		p.indexLength = uint64(myiStat.Size())
	} else if os.IsNotExist(err) {
		// If MYI is missing, report 0
		p.indexLength = 0
	} else {
		return err
	}

	return nil
}

func (p *MyISAMParser) GetStats() (uint64, uint64, uint64) {
	return p.dataLength, p.indexLength, 0
}
