<template>
	<Section title="Logs" description="Available Logs for your site">
		<div class="flex" v-if="logs.length > 0">
			<div
				class="w-full py-4 overflow-auto text-base border rounded-md sm:w-1/3 sm:rounded-r-none"
				:class="{ 'hidden sm:block': selectedLog }"
			>
				<router-link
					class="block px-6 py-3 cursor-pointer"
					:class="
						selectedLog && logName === log.name
							? 'bg-gray-100'
							: 'hover:bg-gray-50'
					"
					v-for="log in logs"
					:key="log.name"
					:to="`/sites/${site.name}/logs/${log.name}`"
				>
					<div>
						{{ log.name }}
					</div>

					<div class="text-sm text-gray-600">
						<div>
							<FormatDate> {{ log.modified }} </FormatDate> - {{ log.size }} kB
						</div>
					</div>
				</router-link>
			</div>
			<div class="w-full sm:w-2/3" v-if="selectedLog">
				<router-link
					:to="`/sites/${site.name}/logs`"
					class="flex items-center py-4 -mt-4 sm:hidden"
				>
					<FeatherIcon name="arrow-left" class="w-4 h-4" />
					<span class="ml-2">
						Select another Log
					</span>
				</router-link>

				<div class="min-h-full pb-16 -mx-4 bg-black sm:mx-0">
					<div class="px-6 py-4 mb-2 border-b border-gray-900">
						<div class="text-sm font-semibold text-white">
							{{ logName }}
							<span class="text-gray-900"
								>({{ selectedLogLines.length }} lines)</span
							>
						</div>
					</div>
					<div class="px-6 font-mono text-xs text-gray-200">
						<div class="overflow-auto" style="white-space: pre-line;">
							<div
								v-for="(line, id) in selectedLogLines"
								v-bind:key="id"
								class="hover:text-yellow-200"
							>
								{{ line }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="flex text-base text-center text-gray-900" v-else>
			Site wise logging is enabled only for sites powered by Frappe Version 13.
		</div>
	</Section>
</template>

<script>
export default {
	name: 'SiteLogs',
	props: ['site', 'logName'],
	data: () => ({
		logs: [],
		selectedLog: null
	}),
	watch: {
		logName(value) {
			if (!value) {
				this.selectedLog = null;
			} else {
				this.fetchLogFile();
			}
		}
	},
	mounted() {
		this.fetchLogs();
		this.fetchLogFile();
	},
	methods: {
		async fetchLogs() {
			this.logs = await this.$call('press.api.site.logs', {
				name: this.site.name
			});
			if (this.logs && !this.logName) {
				this.$router.push(`/sites/${this.site.name}/logs/${this.logs[0].name}`);
			}
		},
		async fetchLogFile() {
			if (this.logName) {
				this.selectedLog = await this.$call('press.api.site.log', {
					name: this.site.name,
					log: this.logName
				});
			}
		}
	},
	computed: {
		selectedLogLines() {
			if (this.selectedLog && this.logName && this.selectedLog[this.logName])
				return this.selectedLog[this.logName].split('\n');
			return [];
		}
	}
};
</script>
