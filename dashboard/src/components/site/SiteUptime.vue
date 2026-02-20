<template>
	<div
		v-if="!data || data[0].date === undefined"
		class="flex h-5/6 items-center justify-center"
	>
		<div class="text-base text-gray-700">No data</div>
	</div>
	<template v-else-if="filteredData?.length > 0">
		<div
			class="w-full h-full flex flex-col justify-center items-center px-5 py-3"
			v-for="type in uptimeTypes"
			:key="type.key"
		>
			<div
				class="flex justify-between mb-1 w-full text-sm text-gray-700 font-normal mt-1"
			>
				<div>
					<template v-if="hoveringOn.key">
						<span
							class="contrast-75 font-bold"
							:class="hoveringOn.colour || []"
						>
							{{
								(hoveringOn.value * 100).toFixed(
									hoveringOn.value === 0 || hoveringOn.value === 1 ? 0 : 2,
								)
							}}%
						</span>
						Uptime at {{ hoveringOn.prettyDate }}
					</template>
				</div>
				<div>{{ subtitle }}</div>
			</div>
			<div class="flex h-1/3 flex-row w-full">
				<div
					v-for="d in filteredData"
					:key="d.date"
					@mouseenter="inspectBar(d)"
					@mouseleave="clearInspect()"
					class="rounded-full"
					:style="`width: ${barWidth};`"
					:class="[
						'hover:brightness-[110%] border-r border-white',
						d[type.key] === undefined
							? 'bg-gray-100'
							: d[type.key] === 1
								? 'bg-green-500'
								: d[type.key] === 0
									? 'bg-red-500'
									: 'bg-yellow-500',
					]"
				></div>
			</div>
			<div
				class="flex justify-between w-full text-[11px] text-gray-700 font-normal mt-1"
			>
				<div class="flex-shrink">{{ firstDateTime }}</div>
				<div class="w-fit flex-shrink">{{ lastDateTime }}</div>
			</div>
		</div>
	</template>
</template>

<script>
import dayjs from 'dayjs';
export default {
	name: 'SiteUptime',
	props: ['data', 'loading'],
	data() {
		return {
			hoveringOn: {
				key: null, // (== date)
				value: null,
				prettyDate: null,
				colour: null,
			},
		};
	},
	computed: {
		uptimeTypes() {
			return [{ key: 'value', label: 'Web' }];
		},
		subtitle() {
			let total = 0;
			let i = 0;
			for (; i < this.filteredData.length; i++) {
				// there could be empty objects at the end of the array
				// so we don't have to count them
				if (typeof this.filteredData[i].value !== 'number') break;

				total += this.filteredData[i].value;
			}
			const average = ((total / i) * 100).toFixed(2);

			return !isNaN(average) ? `${average}% avg. Uptime` : '';
		},
		filteredData() {
			if (!this.data?.length) return [];
			let i = this.data.length - 1;
			for (; i >= 0; i--) {
				if (typeof this.data[i]?.value === 'number') break;
			}
			// trim trailing empty objects
			return this.data.slice(0, i + 1);
		},
		firstDateTime() {
			return this.formatDate(this.filteredData[0]?.date);
		},
		lastDateTime() {
			return this.formatDate(this.filteredData.at(-1)?.date);
		},
		barWidth() {
			if (!this.filteredData?.length) return '0%';
			const percentageWidth = 100 / this.filteredData.length;
			return percentageWidth + '%';
		},
	},
	methods: {
		formatDate(date) {
			return dayjs(date).format('D MMM YYYY, hh:mm a');
		},
		inspectBar({ date, value }) {
			const prettyDate = this.formatDate(date);
			const colour =
				value === 1
					? 'text-green-500'
					: value === 0
						? 'text-red-500'
						: 'text-yellow-500';

			this.hoveringOn = { key: date, value, prettyDate, colour };
		},
		clearInspect() {
			this.hoveringOn = {
				key: null,
				value: null,
				prettyDate: null,
				colour: null,
			};
		},
	},
};
</script>
