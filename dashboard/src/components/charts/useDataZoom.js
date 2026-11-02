import { onMounted } from 'vue'

// A one finger drag must scroll the page, not draw a zoom box.
const isTouchDevice = window.matchMedia('(pointer: coarse)').matches

/** The zoomed range of the x axis: timestamps on a time axis, else indexes. */
function xAxisWindow(chart) {
	const axis = chart.getModel().getComponent('xAxis', 0).axis
	return axis.scale.getExtent().map(Math.round)
}

/**
 * Turns on drag-to-zoom and reports the picked range as dates.
 * On a touch device the gesture is a pinch instead of a drag.
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

		if (isTouchDevice) {
			// `inside` keeps the pinch. All the drag and wheel behaviour stays off,
			// so a scroll of the page keeps its usual effect.
			chart?.setOption({
				dataZoom: [
					{
						type: 'inside',
						zoomOnMouseWheel: false,
						moveOnMouseMove: false,
						moveOnMouseWheel: false,
					},
				],
			})
		} else {
			chart?.on('finished', activateDataZoomCursor)
		}

		chart?.on('datazoom', (event) => {
			// A category axis reports the range in a batch, a time axis reports it
			// on the event itself. A pinch reports percentages only, so read the
			// range off the axis.
			const { startValue, endValue } = event.batch?.[0] ?? event
			const [start, end] =
				startValue == null ? xAxisWindow(chart) : [startValue, endValue]
			emit('datazoom', {
				startDate: toDate(start),
				endDate: toDate(end),
			})
		})
	})
}
