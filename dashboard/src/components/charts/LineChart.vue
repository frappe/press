<template>
	<Card :title="title" class="h-80" :loading="loading" :stopOverflow="true">
		<template #actions>
			<slot name="actions"></slot>
		</template>
		<div
			v-if="error || !data.datasets.length"
			class="flex h-full items-center justify-center"
		>
			<ErrorMessage v-if="error" :message="error" />
			<span v-else class="text-base text-gray-700">No data</span>
		</div>
		<VChart
			v-else
			autoresize
			class="chart"
			:option="options"
			:init-options="initOptions"
		/>
	</Card>
</template>

<script setup>
import { ref, toRefs } from 'vue';
import { DateTime } from 'luxon';
import { use, graphic } from 'echarts/core';
import { SVGRenderer } from 'echarts/renderers';
import { LineChart } from 'echarts/charts';
import {
	GridComponent,
	LegendComponent,
	TooltipComponent,
	MarkLineComponent
} from 'echarts/components';
import VChart from 'vue-echarts';
import theme from '../../../tailwind.theme.json';

const props = defineProps({
	title: {
		type: String,
		required: true
	},
	unit: {
		type: String,
		required: false,
		default: () => ''
	},
	data: {
		type: Object,
		required: true,
		default: () => ({ labels: [], datasets: [] })
	},
	type: {
		type: String,
		required: false,
		default: () => 'category'
	},
	chartTheme: {
		type: Array,
		required: false,
		default: () => [
			theme.colors.red[500],
			theme.colors.blue[500],
			theme.colors.green[500],
			theme.colors.purple[500],
			theme.colors.yellow[500],
			theme.colors.teal[500],
			theme.colors.pink[500],
			theme.colors.cyan[500]
		]
	},
	loading: {
		type: Boolean,
		required: false,
		default: () => false
	},
	error: {
		type: String,
		required: false,
		default: () => ''
	}
});

const { title, unit, data, type, chartTheme } = toRefs(props);

use([
	SVGRenderer,
	GridComponent,
	LegendComponent,
	LineChart,
	TooltipComponent,
	MarkLineComponent
]);

const initOptions = {
	renderer: 'svg'
};

function formatBytes(bytes, decimals = 2, current = 0) {
	if (bytes === 0) return '0 Bytes';

	const k = 1024;
	const dm = decimals < 0 ? 0 : decimals;
	const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
	const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));

	return (
		parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i + current]
	);
}

function getUnit(value, seriesName) {
	if (seriesName === 'bytes') return formatBytes(value);
	else return `${+value.toFixed(2)} ${seriesName}`;
}

const options = ref({
	tooltip: {
		trigger: 'axis',
		formatter: params => {
			// for the dot to follow the same color as the line 🗿
			let tooltip = `<p>${DateTime.fromSQL(
				params[0].axisValueLabel
			).toLocaleString(DateTime.DATETIME_MED)}</p>`;

			params.forEach(({ value, seriesName }, i) => {
				let colorSpan = color =>
					'<span style="display:inline-block;margin-right:4px;border-radius:10px;width:10px;height:10px;background-color:' +
					color +
					'"></span>';

				tooltip += `<p>${colorSpan(chartTheme.value[i])}  ${getUnit(
					value[1],
					unit.value
				)} ${unit.value !== seriesName ? `- ${seriesName}` : ''}</p>`;
			});
			return tooltip;
		}
	},
	xAxis: {
		type: type,
		boundaryGap: false,
		data: data.value.labels,
		axisLine: {
			show: false
		},
		axisTick: {
			show: false
		}
	},
	yAxis: {
		type: 'value',
		max: data.value.yMax,
		axisLabel: {
			formatter: value => {
				if (unit.value === 'bytes') {
					return formatBytes(value, 0);
				} else {
					if (value >= 1000000000) return `${value / 1000000000}B`;
					else if (value >= 1000000) return `${value / 1000000}M`;
					else if (value >= 1000) return `${value / 1000}K`;
					return value;
				}
			}
		}
	},
	labelLine: {
		smooth: 0.2,
		length: 10,
		length2: 20
	},
	legend: {
		top: 'bottom',
		icon: 'circle',
		show: data.value.datasets.length > 1
	},
	series: data.value.datasets.map((dataset, i) => {
		return {
			name: dataset.name || unit,
			type: 'line',
			stack: dataset.stack,
			showSymbol: false,
			data: dataset.dataset || dataset,
			markLine: data.value.markLine,
			emphasis: {
				itemStyle: {
					shadowBlur: 10,
					shadowOffsetX: 0,
					shadowColor: 'rgba(0, 0, 0, 0.5)'
				}
			},
			lineStyle: {
				color: chartTheme.value[i]
			},
			itemStyle: {
				color: chartTheme.value[i]
			},
			areaStyle: {
				color: new graphic.LinearGradient(0, 0, 0, 1, [
					{
						offset: 0,
						color: chartTheme.value[i]
					},
					{
						offset: 1,
						color: '#fff'
					}
				]),
				opacity: 0.3
			}
		};
	})
});
</script>
