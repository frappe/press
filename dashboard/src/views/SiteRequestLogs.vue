<template>
	<Card title="Request Logs">
		<template #actions>
			<Input type="select" :options="sortOptions" v-model="sort" />
			<Input type="select" :options="dateOptions" v-model="whichDate" />
			<Input type="date" v-if="whichDate === 'Custom'" v-model="date" />
		</template>
		<div class="divide-y">
			<div class="flex items-center py-2 text-base text-gray-600">
				<div class="w-2/12">Time</div>
				<div class="w-1/12">Method</div>
				<div class="w-5/12">Path</div>
				<div class="w-2/12">Status Code</div>
				<div class="w-2/12">CPU Time (seconds)</div>
			</div>
			<div
				class="flex items-center py-2 text-base"
				v-for="log in requestLogs.data"
				:key="log.uuid"
			>
				<div class="w-2/12">
					{{ formatDate(log.timestamp, 'TIME_24_WITH_SHORT_OFFSET') }}
				</div>
				<div class="w-1/12">
					<Badge>{{ log.request.method }}</Badge>
				</div>
				<div class="w-5/12 break-words pr-2">{{ log.request.path }}</div>
				<div class="w-2/12">{{ log.request.status_code }}</div>
				<div class="w-2/12">{{ $formatCPUTime(log.duration) }}</div>
			</div>
			<div
				class="px-2 py-2 text-base text-gray-600"
				v-if="
					$resources.requestLogs.loading &&
					$resources.requestLogs.data.length == 0
				"
			>
				<Loading />
			</div>
			<div
				class="py-2 text-base text-gray-600"
				v-if="
					!$resources.requestLogs.loading &&
					$resources.requestLogs.data.length == 0
				"
			>
				No data
			</div>
			<Button
				v-if="$resources.requestLogs.data && $resources.requestLogs.data.length"
				:loading="$resources.requestLogs.loading"
				loadingText="Loading..."
				@click="start += 10"
			>
				Load more
			</Button>
		</div>
	</Card>
</template>

<script>
import { DateTime } from 'luxon';

export default {
	name: 'SiteRequestLogs',
	props: ['site'],
	data() {
		return {
			whichDate: 'Today',
			date: null,
			sort: 'CPU Time (Descending)',
			start: 0
		};
	},
	watch: {
		sort(value) {
			this.reset();
		},
		dateValue(value, old) {
			if (value && value != old) {
				this.reset();
			}
		}
	},
	resources: {
		requestLogs() {
			return {
				method: 'press.api.analytics.request_logs',
				params: {
					name: this.site.name,
					timezone: DateTime.local().zoneName,
					date: this.dateValue,
					sort: this.sort,
					start: this.start
				},
				auto: Boolean(this.dateValue),
				paged: true,
				keepData: true,
				default: []
			};
		}
	},
	methods: {
		reset() {
			this.$resources.requestLogs.reset();
			this.start = 0;
		}
	},
	computed: {
		dateValue() {
			if (this.whichDate === 'Today') {
				return DateTime.local().toISODate();
			} else if (this.whichDate === 'Yesterday') {
				return DateTime.local().minus({ days: 1 }).toISODate();
			} else if (this.whichDate === 'Custom') {
				return this.date;
			}
		},
		dateOptions() {
			return ['Today', 'Yesterday', 'Custom'];
		},
		sortOptions() {
			return ['Time (Ascending)', 'Time (Descending)', 'CPU Time (Descending)'];
		}
	}
};
</script>
