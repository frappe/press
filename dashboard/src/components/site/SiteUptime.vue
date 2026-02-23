<template>
	<div class="flex items-center justify-center flex-grow">
		<div
			v-if="!data || data[0].date === undefined"
			class="flex h-5/6 items-center justify-center"
		>
			<div class="text-base text-gray-700">No data</div>
		</div>
		<template v-else-if="filteredData?.length > 0">
			<div
				class="w-full h-full flex flex-col justify-center items-center px-5 py-3"
			>
				<div
					class="flex justify-between mb-1 w-full text-[11px] text-gray-700 font-normal mt-1"
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
							<span class="opacity-30">&#x2022;</span>
							{{ hoveringOn.prettyDate }}
						</template>
					</div>
					<div class="text-[11px] whitespace-nowrap flex gap-1 items-center">
						<span>{{ subtitle }}</span>
						<Tooltip
							:text="`Aggregated over ${firstDateTime} to ${lastDateTime}`"
						>
							<Help />
						</Tooltip>
					</div>
				</div>
				<div
					class="flex items-center justify-center w-full h-1/3 max-h-24 gap-1"
				>
					<Button
						v-if="chunkedData.length > 1"
						@click="scrollPrev"
						:disabled="currentChunkIndex === 0"
						class="rounded-full h-8 w-8"
					>
						<Left />
					</Button>

					<div
						ref="scrollContainer"
						class="flex h-full overflow-x-auto snap-x snap-mandatory no-scrollbar flex-grow"
					>
						<div
							v-for="(group, index) in chunkedData"
							:key="index"
							class="flex w-full flex-shrink-0 snap-start justify-center"
							:class="chunkedData.length > 1 && 'px-2'"
						>
							<div
								v-for="d in group"
								:key="d.date"
								@mouseenter="inspectBar(d)"
								@mouseleave="clearInspect()"
								class="rounded-full flex-shrink-0 h-full"
								:style="`width: ${barWidth};`"
								:class="[
									'hover:brightness-[110%] border-r border-white',
									d.value === undefined
										? 'bg-gray-100'
										: d.value === 1
											? 'bg-green-500'
											: d.value === 0
												? 'bg-red-500'
												: 'bg-yellow-500',
								]"
							>
								<Tooltip
									placement="bottom"
									:text="`${hoveringOn.percentValue}% aggregated for ~${interval} (until ${hoveringOn.prettyDate})`"
								>
									<div class="h-full w-full" />
								</Tooltip>
							</div>
						</div>
					</div>

					<Button
						v-if="chunkedData.length > 1"
						@click="scrollNext"
						:disabled="currentChunkIndex === chunkedData.length - 1"
						class="rounded-full h-8 w-8"
					>
						<Right />
					</Button>
				</div>
				<div
					class="flex justify-between w-full text-[11px] text-gray-700 font-normal mt-1"
				>
					<div
						class="flex-shrink transition-all duration-300 bg-gray-200"
						:class="highlightDates ? 'bg-opacity-100' : 'bg-opacity-0'"
					>
						{{ firstDateTime }}
					</div>

					<div
						class="w-fit flex-shrink transition-all duration-300 bg-gray-200"
						:class="highlightDates ? 'bg-opacity-100' : 'bg-opacity-0'"
					>
						{{ lastDateTime }}
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<script>
import dayjs from '../../utils/dayjs';
import { icon } from '../../utils/components';
import { Tooltip, debounce } from 'frappe-ui';

export default {
	name: 'SiteUptime',
	props: ['data', 'loading'],
	components: {
		Help: icon('help-circle'),
		Right: icon('arrow-right'),
		Left: icon('arrow-left'),
	},
	data() {
		return {
			chunkSize: 30,
			currentChunkIndex: 0,
			hoveringOn: {
				key: null, // (== date)
				value: null,
				percentValue: null,
				prettyDate: null,
				colour: null,
			},
			highlightDates: false,
		};
	},
	mounted() {
		this.$nextTick(() => {
			const totalChunks = this.chunkedData.length;
			if (!totalChunks) return;

			this.currentChunkIndex = totalChunks - 1;
			this.scrollToCurrentChunk();

			const el = this.$refs.scrollContainer;
			el?.addEventListener('scroll', this.handleScroll);
		});
	},
	beforeUnmount() {
		const el = this.$refs.scrollContainer;
		el?.removeEventListener('scroll', this.handleScroll);
	},
	computed: {
		subtitle() {
			if (!this.data) return '';

			let total = 0;
			let i = 0;
			for (; i < this.data.length; i++) {
				// there could be empty objects at the end of the array
				// so we don't have to count them
				if (typeof this.data[i].value !== 'number') break;

				total += this.data[i].value;
			}
			const average = ((total / i) * 100).toFixed(2);

			return !isNaN(average) ? `${average}% Overall Uptime` : '';
		},
		interval() {
			if (!this.filteredData || this.filteredData.length < 2) return '';

			const first = dayjs(this.filteredData[0].date);
			const second = dayjs(this.filteredData[1].date);

			const diffMs = second.diff(first);

			return dayjs.duration(diffMs).humanize();
		},
		filteredData() {
			if (!this.data?.length) return [];
			return this.data.filter((obj) => !!obj.value);
		},
		chunkedData() {
			const size = this.chunkSize;
			const chunks = [];

			for (let i = 0; i < this.filteredData.length; i += size) {
				chunks.push(this.filteredData.slice(i, i + size));
			}

			return chunks;
		},
		firstDateTime() {
			return this.formatDate(
				this.chunkedData.at(this.currentChunkIndex).at(0)?.date,
			);
		},
		lastDateTime() {
			return this.formatDate(
				this.chunkedData.at(this.currentChunkIndex).at(-1)?.date,
			);
		},
		barWidth() {
			if (!this.filteredData?.length) return '0%';
			const percentageWidth = 100 / this.filteredData.length;
			return Math.max(percentageWidth, (100 / this.chunkSize).toFixed(2)) + '%';
		},
	},
	methods: {
		formatDate(date) {
			return dayjs(date).format('D MMM YYYY, hh:mm a');
		},
		inspectBar({ date, value }) {
			const prettyDate = this.formatDate(date);
			const percentValue = (value * 100).toFixed(2);
			const colour =
				value === 1
					? 'text-green-500'
					: value === 0
						? 'text-red-500'
						: 'text-yellow-500';

			this.hoveringOn = { key: date, value, percentValue, prettyDate, colour };
		},
		clearInspect() {
			this.hoveringOn = {
				key: null,
				value: null,
				prettyDate: null,
				colour: null,
			};
		},
		scrollNext() {
			if (this.currentChunkIndex >= this.chunkedData.length - 1) return;
			this.currentChunkIndex++;
			this.scrollToCurrentChunk();
		},
		scrollPrev() {
			if (this.currentChunkIndex <= 0) return;
			this.currentChunkIndex--;
			this.scrollToCurrentChunk();
		},
		handleScroll: debounce(() => {
			const el = this?.$refs.scrollContainer;
			if (!el) return;

			const index = Math.round(el.scrollLeft / el.clientWidth);
			this.currentChunkIndex = index;
		}, 500),
		scrollToCurrentChunk() {
			const el = this.$refs.scrollContainer;
			if (!el) return;

			el.scrollTo({
				left: el.clientWidth * this.currentChunkIndex,
				behavior: 'smooth',
			});
		},
	},
	watch: {
		currentChunkIndex() {
			this.highlightDates = true;

			clearTimeout(this._highlightTimeout);

			this._highlightTimeout = setTimeout(() => {
				this.highlightDates = false;
			}, 300);
		},
	},
};
</script>
<style>
.no-scrollbar::-webkit-scrollbar {
	display: none;
}

.no-scrollbar {
	-ms-overflow-style: none;
	/* IE + Edge */
	scrollbar-width: none;
	/* Firefox */
}
</style>
