<template>
	<Dialog
		:options="{
			title: 'Normalized Slow Query',
			size: '2xl'
		}"
		v-model="show"
	>
		<template #body-content>
			<!-- <div
				v-if="$site.doc?.version !== 'Version 14'"
				class="mb-5 flex items-center space-x-2 rounded-lg border-blue-200 bg-blue-100 p-3 text-sm text-gray-800"
			>
				<i-lucide-info class="h-4 w-4" />
				<div>Upcoming Feature : Analyze Query coming soon on Version-15</div>
			</div> -->
			<h2 class="font-semibold">Query</h2>
			<pre
				class="mt-2 rounded-lg border-2 border-gray-200 bg-gray-100 p-3 text-sm text-gray-700"
				>{{ query }}</pre
			>
			<div class="flex p-2 text-sm">
				<span class="ml-auto pr-2"
					>Duration: {{ duration.toFixed(2) }} seconds</span
				>
			</div>
			<div
				v-if="analyze_query_already_running"
				class="mt-5 flex items-center rounded-lg border-blue-200 bg-yellow-100 p-3 text-sm text-gray-800"
			>
				There already is a query that is being analyzed for this site.
			</div>
			<div v-if="optimizable === true">
				<h2 class="font-semibold">Suggested Index</h2>
				<div
					class="mt-2 space-y-1 whitespace-pre-wrap rounded-lg border-2 border-gray-200 bg-gray-100 p-3 text-sm text-gray-700"
				>
					<div class="flex">
						<p class="font-semibold">Table:</p>
						<span>{{
							this.$resources.getSuggestedIndex.data.suggested_index.split(
								'.'
							)[0]
						}}</span>
					</div>
					<div class="flex">
						<p class="font-semibold">Column:</p>
						<span>{{
							this.$resources.getSuggestedIndex.data.suggested_index.split(
								'.'
							)[1]
						}}</span>
					</div>
				</div>
			</div>
			<!-- <div
				v-if="optimizable === false"
				class="mt-5 flex items-center rounded-lg border-blue-200 bg-yellow-100 p-3 text-sm text-gray-800"
			>
				No query index suggestions available. Try adding indexes manually.
			</div> -->
		</template>
		<template v-if="$site.doc?.version === 'Version 14'" #actions>
			<Button
				v-if="!analyze_query_already_running && !optimizable"
				class="w-full"
				:variant="'solid'"
				theme="gray"
				size="sm"
				label="Button"
				:loading="analyze_button"
				@click="$resources.analyzeQuery.submit()"
			>
				Analyze Query
			</Button>
			<Button
				v-if="optimizable"
				class="w-full"
				:variant="'solid'"
				theme="gray"
				size="sm"
				label="Button"
				@click="applySuggestion"
			>
				Apply Suggestion
			</Button>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import AlertBanner from '../../../src2/components/AlertBanner.vue';
import { toast } from 'vue-sonner';
import router from '../../router';

export default {
	props: [
		'siteName',
		'query',
		'duration',
		'count',
		'rows_examined',
		'rows_sent',
		'example'
	],
	components: {
		AlertBanner
	},
	data() {
		return {
			show: true,
			analyze_button: false,
			optimizable: null,
			analyze_query_already_running: true
		};
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.siteName);
		}
	},
	methods: {
		applySuggestion() {
			toast.promise(this.$resources.applySuggested.submit(), {
				loading: 'Scheduling add database index job...',
				success: s => {
					this.show = false;
					this.$router.push({
						name: 'Site Detail Jobs',
						params: { name: this.siteName }
					});
					return 'The job to add a database index has been sucessfully created.';
				},
				error: e => {
					return e.messages.length ? e.messages.join('\n') : e.message;
				}
			});
		}
	},
	resources: {
		analyzeQuery() {
			return {
				url: 'press.api.dboptimize.mariadb_analyze_query',
				makeParams() {
					return {
						row: {
							query: this.query,
							count: this.count,
							duration: this.duration,
							rows_examined: this.rows_examined,
							rows_sent: this.rows_sent,
							example: this.example
						},
						name: this.siteName
					};
				},
				onSuccess(data) {
					this.analyze_button = false;
					if (data == 'Running') {
						this.optimizable = false;
						toast.success('Analayze query has started in the background');
					} else {
						this.optimizable = true;
						toast.success('Analaysis on query could not be performed');
					}
					this.show = false;
				},
				beforeSubmit(params) {
					this.analyze_button = true;
				},
				onError(error) {
					this.analyze_button = false;
				},
				initialData: { data: [] }
			};
		},
		applySuggested() {
			return {
				url: 'press.api.analytics.mariadb_add_suggested_index',
				method: 'POST',
				makeParams() {
					return {
						name: this.siteName,
						table:
							this.$resources.getSuggestedIndex.data.suggested_index.split(
								'.'
							)[0],
						column:
							this.$resources.getSuggestedIndex.data.suggested_index.split(
								'.'
							)[1]
					};
				}
			};
		},
		getSuggesteIndex() {
			return {
				url: 'press.api.dboptimize.get_status_of_mariadb_analyze_query',
				auto: true,
				method: 'POST',
				makeParams() {
					return {
						name: this.siteName,
						query: this.query
					};
				}
			};
		},
		mariadbAnalyzeQueryAlreadyRunningForSite() {
			return {
				url: 'press.api.dboptimize.mariadb_analyze_query_already_running_for_site',
				auto: true,
				makeParams() {
					return {
						name: this.siteName
					};
				},
				onSuccess(data) {
					if (data) {
						this.analyze_query_already_running = true;
					} else {
						this.analyze_query_already_running = false;
					}
				}
			};
		},
		getSuggestedIndex() {
			return {
				url: 'press.api.dboptimize.get_suggested_index',
				auto: true,
				makeParams() {
					return {
						name: this.siteName,
						normalized_query: this.query
					};
				},
				onSuccess(data) {
					try {
						if (data.suggested_index.length == 0) {
							this.optimizable = false;
						} else {
							this.optimizable = true;
						}
					} catch (error) {}
				}
			};
		}
	}
};
</script>
