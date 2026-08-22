import { onMounted } from 'vue'

/**
 * Turns on drag-to-zoom and reports the picked range as dates.
 * `toDate` maps an axis value to a Date: a timestamp on a time axis, an index
 * into the labels on a category axis.
 */
export function useDataZoom(chartRef, toDate, emit) {
	onMounted(() => {
		const chart = chartRef.value?.chart
		// Wait for the first render: the toolbox drops the action before that.
		// Detach before dispatching: takeGlobalCursor triggers a re-render, which
		// fires `finished` again. Left attached, that is an endless render loop that
		// pegs the main thread for as long as the page is open.
		const activateDataZoomCursor = () => {
			chart?.off('finished', activateDataZoomCursor)
			chart?.dispatchAction({
				type: 'takeGlobalCursor',
				key: 'dataZoomSelect',
				dataZoomSelectActive: true,
			})
		}
		chart?.on('finished', activateDataZoomCursor)

		chart?.on('datazoom', (event) => {
			// A category axis reports the range in a batch, a time axis reports it
			// on the event itself.
			const { startValue, endValue } = event.batch?.[0] ?? event
			emit('datazoom', {
				startDate: toDate(startValue),
				endDate: toDate(endValue),
			})
		})
	})
}
