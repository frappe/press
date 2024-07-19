<template>
	<Dialog
		:options="{
			title: 'Normalized Slow Query',
			size: '2xl'
		}"
		v-model="show"
	>
		<template #body-content>
			<div
				v-if="$site.doc?.version !== 'Version 14'"
				class="mb-5 flex items-center space-x-2 rounded-lg border-blue-200 bg-blue-100 p-3 text-sm text-gray-800"
			>
				<i-lucide-info class="h-4 w-4" />
				<div>Upcoming Feature : Analyze Query coming soon on Version-15</div>
			</div>
			<h2 class="font-semibold">Query</h2> 
			<pre
				class="rounded-lg mt-2 border-2 border-gray-200 bg-gray-100 p-3 text-sm text-gray-700"
				>{{ query }}</pre
			>
			<div class="flex p-2 text-sm">
				<span class="ml-auto pr-2"
					>Duration: {{ duration.toFixed(2) }} seconds</span
				>
			</div>
			<div v-if="optimizable === true">
				<h2 class="font-semibold">Suggested Index</h2> 
				<div
					class="mt-2 space-y-1 whitespace-pre-wrap rounded-lg border-2 border-gray-200 bg-gray-100 p-3 text-sm text-gray-700"
				><div class="flex">
					<p class="font-semibold">Table: </p> <span >{{ this.$resources.analyzeQuery.data[0].suggested_index.split('.')[0] }}</span>

				</div>
				<div class="flex">
					<p class="font-semibold">Column: </p> <span>{{ this.$resources.analyzeQuery.data[0].suggested_index.split('.')[1] }}</span>

				</div>
			</div>
			</div>
			<div
				v-if="optimizable === false"
				class="mt-5 flex items-center rounded-lg border-blue-200 bg-yellow-100 p-3 text-sm text-gray-800"
			>
				No query index suggestions available. Try adding indexes manually.
			</div>
		</template>
		<template v-if="$site.doc?.version === 'Version 14'" #actions>
			<Button
				v-if="!optimizable"
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
				success: s =>{

					this.show = false;
					this.$router.push(({name: 'Site Detail Jobs',params:{ name: this.siteName}}))
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
				url: 'press.api.analytics.mariadb_analyze_query',
				makeParams() {
					return {
						rows: [
							{
								query: this.query,
								count: this.count,
								duration: this.duration,
								rows_examined: this.rows_examined,
								rows_sent: this.rows_sent,
								example: this.example
							}
						],
						name: this.siteName
					};
				},
				onSuccess(data) {
					this.analyze_button = false;
					data = data[0];
					if (!data.suggested_index) {
						this.optimizable = false;
					} else {
						this.optimizable = true;
					}
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
							this.$resources.analyzeQuery.data[0].suggested_index.split(
								'.'
							)[0],
						column:
							this.$resources.analyzeQuery.data[0].suggested_index.split('.')[1]
					};
				},
			};
		}
	}
};
</script>
