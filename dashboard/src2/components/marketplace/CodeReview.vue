<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Code Review',
			size: '6xl'
		}"
	>
		<template v-if="getResults" #body-content>
			<div class="container mx-auto px-4 py-3">
				<div class="grid gap-3">
					<div
						class="card bg-white shadow-md rounded-md overflow-hidden"
						v-for="file in getResults"
						:key="file.name"
					>
						<div class="card-header bg-gray-200 p-3">
							<h2 class="text-md font-semibold text-gray-800">
								{{ file.name }} - {{ file.score }} issues
							</h2>
						</div>
						<div class="p-4">
							<div
								class="issues space-y-4"
								v-for="line in file.lines"
								:key="line.context.line_number"
							>
								<div
									class="issue-item p-4 mb-4"
									v-for="issue in line.issues"
									:key="issue.violation"
								>
									<div class="flex items-center mb-3">
										<span class="text-red-600 mr-2">{{ issue.severity }}</span>
										<span class="text-gray-800">({{ issue.violation }})</span>
										<span class="text-orange-500 font-semibold pl-2">
											- {{ issue.match }}</span
										>
									</div>
									<div class="bg-gray-50 border border-gray-400 p-2 rounded-md">
										<div
											v-for="(lineText, i) in line.context.lines"
											:key="i"
											:class="{
												'bg-yellow-200':
													lineText.includes(issue.match) &&
													line.context.line_range[i] ===
														line.context.line_number
											}"
										>
											<code class="p-2 text-sm whitespace-pre-wrap">
												<span class="text-gray-500"
													>{{ line.context.line_range[i] }}:</span
												>
												{{ lineText }}
											</code>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
export default {
	props: ['row'],
	data() {
		return {
			show: true
		};
	},
	computed: {
		getResults() {
			const results = JSON.parse(this.$resources.codeScreening.data[0].result);
			return results;
		}
	},
	resources: {
		codeScreening() {
			return {
				type: 'list',
				doctype: 'App Release Approval Request',
				fields: [
					'name',
					'marketplace_app',
					'screening_status',
					'app_release',
					'status',
					'result'
				],
				filters: {
					app_release: this.row.name,
					status: 'Open'
				},
				orderBy: 'creation desc',
				start: 0,
				auto: true
			};
		}
	}
};
</script>
