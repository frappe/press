// Mock responses for press.api.server.analytics, shaped like the real endpoint:
// { datasets: [{ name, values: number[] }], labels: ISOString[] }.

const CPU_MODES = [
	'system',
	'user',
	'iowait',
	'irq',
	'softirq',
	'nice',
	'steal',
	'idle',
] as const

const POINTS = 24

export function labels(): string[] {
	// 24 points, 90s apart — the 1h/90s grid that regressed the chart.
	const start = new Date('2024-01-01T13:00:00.000Z').getTime()
	return Array.from({ length: POINTS }, (_, i) =>
		new Date(start + i * 90 * 1000).toISOString(),
	)
}

// A healthy, gap-free CPU response: idle dominates, the rest are small but
// non-zero. With the rate-window fix the backend never returns nulls, so no
// value here is null.
export function cpuData() {
	const datasets = CPU_MODES.map((mode) => {
		const base = mode === 'idle' ? 88 : 1.5
		return {
			name: mode,
			values: Array.from({ length: POINTS }, (_, i) =>
				Number((base + Math.sin(i) * (mode === 'idle' ? 4 : 0.5)).toFixed(2)),
			),
		}
	})
	return { datasets, labels: labels() }
}

// The pre-fix shape: every other step is null because the rate() window saw a
// single sample. The chart used to draw these as spikes down to zero.
export function cpuDataWithGaps() {
	const data = cpuData()
	for (const dataset of data.datasets) {
		dataset.values = dataset.values.map((value, i) =>
			i % 2 === 1 ? null : value,
		)
	}
	return data
}

export function emptyData() {
	return { datasets: [], labels: [] }
}

export function singleSeriesData() {
	return {
		datasets: [
			{
				name: 'Used',
				values: Array.from({ length: POINTS }, (_, i) =>
					Number((2_000_000_000 + i * 1_000_000).toFixed(0)),
				),
			},
		],
		labels: labels(),
	}
}
