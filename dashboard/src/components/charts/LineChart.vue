<template>
	<component
		:is="showCard ? Card : 'div'"
		:title="title"
		:class="showCard ? 'h-80' : ''"
		:loading="loading"
		:stopOverflow="true"
	>
		<template #actions>
			<slot name="actions"></slot>
		</template>
		<div
			v-if="
				error ||
				!data.datasets.length ||
				(data.datasets[0].length !== undefined && !data.datasets[0].length)
			"
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
	</component>
</template>

<script setup>
import Card from '../global/Card.vue';
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
import { formatBytes, getUnit } from './utils';

const props = defineProps({
	showCard: {
		type: Boolean,
		required: false,
		default: () => true
	},
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

const options = ref({
	grid: {
		top: 20,
		left: 40,
		right: 20,
		bottom: 30
	},
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
