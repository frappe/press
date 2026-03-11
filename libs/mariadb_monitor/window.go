package main

type sample struct {
	value    float64
	breached bool
}

type RingBuffer[T any] struct {
	data  []T
	head  int
	count int
	cap   int
}

func NewRingBuffer[T any](capacity int) RingBuffer[T] {
	return RingBuffer[T]{
		data: make([]T, capacity),
		cap:  capacity,
	}
}

func (r *RingBuffer[T]) Push(v T) {
	r.data[r.head] = v
	r.head = (r.head + 1) % r.cap
	if r.count < r.cap {
		r.count++
	}
}

func (r *RingBuffer[T]) Len() int {
	return r.count
}

func (r *RingBuffer[T]) ForEach(fn func(idx int, v T)) {
	start := 0
	if r.count == r.cap {
		start = r.head
	}
	for i := 0; i < r.count; i++ {
		idx := (start + i) % r.cap
		fn(i, r.data[idx])
	}
}

func (r *RingBuffer[T]) Latest() T {
	idx := (r.head - 1 + r.cap) % r.cap
	return r.data[idx]
}

type MetricWindow struct {
	buf RingBuffer[sample]
}

func NewMetricWindow(capacity int) MetricWindow {
	return MetricWindow{buf: NewRingBuffer[sample](capacity)}
}

func (w *MetricWindow) Push(value float64, threshold float64) {
	w.buf.Push(sample{
		value:    value,
		breached: value >= threshold,
	})
}

func (w *MetricWindow) IsSustained(ratio float64) bool {
	if w.buf.Len() == 0 {
		return false
	}
	breachedCount := 0
	w.buf.ForEach(func(_ int, s sample) {
		if s.breached {
			breachedCount++
		}
	})
	return float64(breachedCount)/float64(w.buf.Len()) >= ratio
}

func (w *MetricWindow) IsSpike(ratio float64) bool {
	if w.buf.Len() == 0 {
		return false
	}
	latest := w.buf.Latest()
	return latest.breached && !w.IsSustained(ratio)
}

func (w *MetricWindow) Trend() string {
	n := w.buf.Len()
	if n < 2 {
		return "stable_low"
	}

	var sumX, sumY, sumXY, sumX2 float64
	w.buf.ForEach(func(i int, s sample) {
		x := float64(i)
		sumX += x
		sumY += s.value
		sumXY += x * s.value
		sumX2 += x * x
	})

	fn := float64(n)
	meanX := sumX / fn
	meanY := sumY / fn
	denominator := sumX2 - fn*meanX*meanX

	if denominator == 0 {
		if meanY > 0 {
			return "stable_high"
		}
		return "stable_low"
	}

	slope := (sumXY - fn*meanX*meanY) / denominator

	threshold := meanY * 0.05
	if threshold < 1.0 {
		threshold = 1.0
	}

	switch {
	case slope > threshold:
		return "rising"
	case slope < -threshold:
		return "falling"
	default:
		if meanY > 0 {
			return "stable_high"
		}
		return "stable_low"
	}
}
