<template>
	<CardDetails :showDetails="log">
		<div class="px-6 py-5">
			<template v-if="log != null">
				<div class="flex items-center">
					<Button
						class="mr-3 md:hidden"
						@click="$router.back()"
						icon="chevron-left"
					/>
					<h4 class="text-lg font-medium">
						{{ logName }}
						<span class="">({{ logLines.length }} lines)</span>
					</h4>
				</div>
			</template>
			<div v-else>
				<Button
					:loading="true"
					loading-text="Loading..."
					v-if="$resources.log.loading"
				/>
				<span v-else class="text-base text-gray-600">
					{{ logName ? 'Invalid Log' : 'No log selected' }}
				</span>
			</div>
		</div>
		<div class="flex-auto px-6 overflow-auto font-mono text-xs" v-if="log">
			<div
				class="bg-gray-100 rounded-md px-2 py-2.5 mb-6"
				:style="{ width: viewportWidth < 768 ? 'calc(100vw - 6rem)' : '' }"
			>
				<div class="overflow-x-auto">
					<pre v-for="(line, id) in logLines" :key="id">{{ line }}</pre>
				</div>
			</div>
		</div>
	</CardDetails>
</template>
<script>
import CardDetails from '@/components/CardDetails.vue';
export default {
	name: 'BenchLogsDetail',
	props: ['bench', 'instanceName', 'logName'],
	components: { CardDetails },
	inject: ['viewportWidth'],
	resources: {
		log() {
			return {
				method: 'press.api.bench.log',
				params: {
					name: this.bench.name,
					bench: this.instanceName,
					log: this.logName
				},
				auto: Boolean(this.logName)
			};
		}
	},
	computed: {
		log() {
			return this.$resources.log.data && this.$resources.log.data[this.logName];
		},
		logLines() {
			if (this.log && this.logName) return this.log.split('\n').slice(-4096);
			return [];
		}
	}
};
</script>
