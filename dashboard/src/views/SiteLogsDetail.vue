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
		<div class="flex-auto overflow-auto px-6 font-mono text-xs" v-if="log">
			<div
				class="mb-6 whitespace-pre-line rounded-md bg-gray-100 px-2 py-2.5"
				:style="{ width: viewportWidth < 768 ? 'calc(100vw - 6rem)' : '' }"
			>
				<div class="overflow-x-auto">
					<div v-for="(line, id) in logLines" :key="id">
						{{ line }}
					</div>
				</div>
			</div>
		</div>
	</CardDetails>
</template>
<script>
import CardDetails from '@/components/CardDetails.vue';
export default {
	name: 'SiteLogsDetail',
	props: ['site', 'logName'],
	components: { CardDetails },
	inject: ['viewportWidth'],
	resources: {
		log() {
			return {
				method: 'press.api.site.log',
				params: {
					name: this.site?.name,
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
			if (this.log && this.logName) return this.log.split('\n');
			return [];
		}
	}
};
</script>
