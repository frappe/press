<template>
	<div class="m-4 mr-0 flex h-full w-1/4 flex-col">
		<FormControl
			class="mb-4 mr-4"
			label="Search log files"
			v-model="searchLogQuery"
		>
			<template #prefix>
				<lucide-search class="h-4 w-4 text-gray-500" />
			</template>
		</FormControl>
		<div class="h-[81.5vh] space-y-2 overflow-auto pr-4">
			<div
				v-if="$resources.benchLogs?.loading || $resources.siteLogs?.loading"
				class="mt-20 flex justify-center space-x-2 text-sm text-gray-700"
			>
				<Spinner class="w-4" />
				<span> Fetching logs... </span>
			</div>
			<div
				v-else-if="logs.length === 0"
				class="mt-20 flex justify-center text-sm text-gray-700"
			>
				No logs found
			</div>
			<template v-else v-for="log in logs">
				<div
					class="cursor-pointer rounded border border-gray-200 p-3 hover:bg-gray-50"
					:class="{
						'border-gray-800': logId === log.name,
					}"
					@click="
						() => {
							logId = log.name;
							$router.push({
								name: 'Log Browser',
								params: {
									mode,
									docName: mode === 'bench' ? bench : site,
									logId: log.name,
								},
							});
						}
					"
				>
					<div class="flex items-center justify-between">
						<div class="space-y-1">
							<p class="text-base text-gray-700">{{ log.name }}</p>
							<p class="text-xs text-gray-500">
								{{ $format.date(log.modified, 'YYYY-MM-DD HH:mm') }}
							</p>
						</div>
						<p class="text-sm text-gray-500">
							{{ $format.bytes(log.size) }}
						</p>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script>
export default {
	props: {
		mode: String,
		docName: String,
	},
	data() {
		return {
			searchLogQuery: '',
			logId: this.$route.params.logId,
		};
	},
	resources: {
		benchLogs() {
			return {
				url: 'press.api.bench.logs',
				params: {
					name: this.bench?.split('-').slice(0, 2).join('-'), // TODO: fetch group instead of hardcoding
					bench: this.bench,
				},
				auto: this.mode === 'bench' && this.bench,
				cache: ['BenchLogs', this.bench],
			};
		},
		siteLogs() {
			return {
				url: 'press.api.site.logs',
				params: {
					name: this.site,
				},
				auto: this.mode === 'site' && this.site,
				cache: ['SiteLogs', this.site],
			};
		},
	},
	computed: {
		logs() {
			let logs = [];
			if (this.mode === 'bench') {
				logs = this.$resources.benchLogs?.data || [];
			} else if (this.mode === 'site') {
				logs = this.$resources.siteLogs?.data || [];
			}

			// filter out rotated logs that ends with .1, .2, .3, etc
			// TODO: do the filtering in agent instead
			// logs = logs.filter(log => !log.name.match(/\.\d+$/));

			if (this.searchLogQuery) {
				logs = logs.filter((log) =>
					log.name.toLowerCase().includes(this.searchLogQuery.toLowerCase()),
				);
			}

			return logs;
		},
		bench() {
			if (this.mode === 'bench') {
				return this.docName;
			}
			return null;
		},
		site() {
			if (this.mode === 'site') {
				return this.docName;
			}
			return null;
		},
	},
};
</script>
