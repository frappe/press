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
			<pre
				class="rounded-lg border-2 border-gray-200 bg-gray-100 p-3 text-sm text-gray-700"
			>
 {{ query }} </pre
			>
			<div class="flex p-2 text-sm">
				<span class="ml-auto pr-2"
					>Duration: {{ duration.toFixed(2) }} seconds</span
				>
			</div>
		</template>
		<template v-if="$site.doc?.version === 'Version 14'" #actions>
			<Button
				class="mb-6 w-full"
				:variant="'solid'"
				theme="gray"
				size="sm"
				label="Button"
				:loading="analyze_button"
				@click="$resources.analyzeQuery.submit()"
			>
				Analyze Query
			</Button>
			<div v-if="optimizable === true">
				<pre
					class="whitespace-pre-wrap rounded-lg border-2 border-gray-200 bg-gray-100 p-4 text-sm text-gray-700"
				>
    <span class="font-semibold">Suggested Index:</span> 
    <span class="ml-2">Table: <span class="font-semibold">{{ this.$resources.analyzeQuery.data[0].suggested_index.split('.')[0] }}</span></span>
    <span class="ml-2">Column: <span class="font-semibold">{{ this.$resources.analyzeQuery.data[0].suggested_index.split('.')[1] }}</span></span>
</pre>

				<Button
					class="mb-6 mt-6 w-full"
					:variant="'solid'"
					theme="gray"
					size="sm"
					label="Button"
					@click="$resources.applySuggested.submit()"
				>
					Apply Suggestion
				</Button>
				<div v-if="sucesfullyCreatedIndexJob === true">
					<AlertBanner
						title="The job to add a database index has been sucessfully created. Check the jobs tab to keep track on progress. It might take time for large tables."
						type="info"
					>
						<Button
							class="ml-auto"
							variant="outline"
							:route="`/sites/${siteName}/jobs`"
						>
							View
						</Button>
					</AlertBanner>
				</div>
			</div>
			<div
				v-else-if="optimizable === false"
				class="mb-5 mt-5 flex items-center rounded-lg border-blue-200 bg-yellow-100 p-3 text-sm text-gray-800"
			>
				No query index suggestions available 😕. Try adding indexes manually 🤷‍♂️
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import AlertBanner from '../../../src2/components/AlertBanner.vue';
import { toast } from 'vue-sonner';

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
			sucesfullyCreatedIndexJob: null
		};
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.siteName);
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
				onSuccess(data) {
					if (data == 'prexisting job') {
						this.sucesfullyCreatedIndexJob = false;
						toast.error('There already is an Agent Job for Add Database Index');
						this.show = false;
						return;
					}
					this.sucesfullyCreatedIndexJob = true;
				}
			};
		}
	}
};
</script>
