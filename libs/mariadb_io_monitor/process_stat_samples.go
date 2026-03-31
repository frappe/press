package main

import (
	"fmt"
	"time"
)

func (m *Monitor) ProcessStatSamples() {
	m.wg.Add(1)
	defer m.wg.Done()

	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-m.ctx.Done():
			fmt.Println("Analyzer stopping:", m.ctx.Err())
			return
		case <-ticker.C:

			latest := m.sampler.buf.GetLatest()
			if latest == nil {
				continue
			}

			m.UpdateAnomalyState(*latest)
		}
	}
}
