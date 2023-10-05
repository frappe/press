<template>
	<Card :title="title" class="h-80">
		<template #actions>
			<slot name="actions"></slot>
		</template>
		<div
			v-if="error || loading || !data.datasets.length"
			class="flex h-full items-center justify-center"
		>
			<Button v-if="loading" :loading="loading" label="Loading..." />
			<ErrorMessage v-else-if="error" :message="error" />
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
import { use, graphic } from 'echarts/core';
import { SVGRenderer } from 'echarts/renderers';
import { LineChart } from 'echarts/charts';
import {
	GridComponent,
	LegendComponent,
	TitleComponent,
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
		type: String,
		required: false,
		default: () => theme.colors.blue[500]
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
	TitleComponent,
	TooltipComponent,
	MarkLineComponent
]);

const initOptions = {
	renderer: 'svg'
};

const options = ref({
	tooltip: {
		trigger: 'axis',
		formatter: params => {
			// for the dot to follow the same color as the line 🗿
			let tooltip = `<p>${params[0].axisValueLabel}</p>`;
			params.forEach(({ value, seriesName }) => {
				let colorSpan = color =>
					'<span style="display:inline-block;margin-right:4px;border-radius:10px;width:10px;height:10px;background-color:' +
					color +
					'"></span>';
				tooltip += `<p>${colorSpan(chartTheme.value)} ${+value[1].toFixed(
					2
				)} ${seriesName}</p>`;
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
		},
		axisLabel: {
			formatter: '{d} {MMM}'
		}
	},
	yAxis: {
		type: 'value',
		axisLabel: {
			formatter: value => {
				if (value >= 1000) return `${value / 1000}K`;
				return value;
			}
		}
	},
	labelLine: {
		smooth: 0.2,
		length: 10,
		length2: 20
	},
	series: [
		{
			name: unit,
			type: 'line',
			showSymbol: false,
			data: data.value.datasets,
			markLine: data.value.markLine,
			emphasis: {
				itemStyle: {
					shadowBlur: 10,
					shadowOffsetX: 0,
					shadowColor: 'rgba(0, 0, 0, 0.5)'
				}
			},
			lineStyle: {
				color: chartTheme
			},
			itemStyle: {
				color: chartTheme
			},
			areaStyle: {
				color: new graphic.LinearGradient(0, 0, 0, 1, [
					{
						offset: 0,
						color: chartTheme
					},
					{
						offset: 1,
						color: '#fff'
					}
				]),
				opacity: 0.3
			}
		}
	]
});
</script>
