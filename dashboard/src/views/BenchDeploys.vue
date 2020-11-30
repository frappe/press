<template>
	<div>
		<Section
			title="Deploys"
			:description="
				candidates.length ? 'Deploys on your bench' : 'No deploys on your bench'
			"
		>
			<div class="flex" v-if="candidates.length">
				<div
					class="w-full py-4 overflow-auto text-base border rounded-md sm:w-1/3 sm:rounded-r-none"
					:class="{ 'hidden sm:block': selectedCandidate }"
				>
					<router-link
						class="block px-6 py-3 cursor-pointer"
						:class="
							selectedCandidate && selectedCandidate.name === candidate.name
								? 'bg-gray-100'
								: 'hover:bg-gray-50'
						"
						v-for="candidate in candidates"
						:key="candidate.name"
						:to="`/benches/${bench.name}/deploys/${candidate.name}`"
					>
						Deploy on
						<FormatDate>
							{{ candidate.creation }}
						</FormatDate>
					</router-link>
				</div>
				<div class="w-full sm:w-2/3" v-if="selectedCandidate">
					<router-link
						:to="`/benches/${bench.name}/deploys`"
						class="flex items-center py-4 -mt-4 sm:hidden"
					>
						<FeatherIcon name="arrow-left" class="w-4 h-4" />
						<span class="ml-2">
							Select another Deploy
						</span>
					</router-link>
					<div class="min-h-full pb-16 -mx-4 bg-black sm:mx-0">
						<div class="px-6 py-4 mb-2 border-b border-gray-900">
							<div class="text-sm font-semibold text-white">
								Build Log
							</div>
							<div
								class="text-xs text-gray-500"
								v-if="selectedCandidate.status === 'Success'"
							>
								Completed
								<FormatDate type="relative">
									{{ selectedCandidate.build_end }}
								</FormatDate>
								in {{ formatDuration(selectedCandidate.build_duration) }}
							</div>
						</div>
						<details
							class="px-6 text-white cursor-pointer"
							v-for="step in selectedCandidate.build_steps"
							:key="step.idx"
						>
							<summary
								class="flex items-center py-2 text-xs text-gray-600 focus:outline-none"
							>
								<span class="ml-1">
									<Spinner
										v-if="step.status === 'Running'"
										class="w-3 h-3 text-gray-500"
									/>
									<FeatherIcon
										v-else-if="step.status === 'Success'"
										name="check"
										:stroke-width="3"
										class="w-3 h-3 text-green-500"
									/>
									<FeatherIcon
										v-else-if="step.status === 'Failure'"
										name="x"
										:stroke-width="3"
										class="w-3 h-3 text-red-500"
									/>
								</span>
								<span class="ml-2 font-semibold text-white flex-grow">
									{{ step.stage }} - {{ step.step }}
								</span>
								<div
									v-if="step.status === 'Success' || step.status === 'Failure'"
								>
									<div
										class="text-gray-300"
										v-if="step.cached && !step.duration"
									>
										Cached
									</div>
									<div class="text-gray-300" v-else>
										{{ step.duration }}<span class="pl-0.5">s</span>
									</div>
								</div>
							</summary>
							<div class="px-6 font-mono text-xs text-blue-200">
								<pre class="whitespace-pre-wrap">{{ step.command }}</pre>
							</div>
							<div class="px-6 font-mono text-xs text-gray-200">
								<pre class="whitespace-pre-wrap">{{ step.output }}</pre>
							</div>
						</details>
					</div>
				</div>
			</div>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'BenchDeploys',
	props: ['bench', 'candidateName'],
	watch: {
		candidateName(value) {
			if (value) {
				this.$resources.selectedCandidate.reload();
			}
		}
	},
	mounted() {
		if (this.candidateName) {
			this.$resources.selectedCandidate.reload();
			this.setupSocket();
		}
	},
	methods: {
		formatDuration(duration) {
			return duration.split('.')[0];
		},
		if (this.deployName) {
			this.$resources.selectedDeploy.reload();
		}
	},
	resources: {
		candidates() {
			return {
				method: 'press.api.bench.candidates',
				params: {
					name: this.bench.name
				},
				auto: true,
				default: []
			};
		},
		selectedCandidate() {
			return {
				method: 'press.api.bench.candidate',
				params: {
					name: this.candidateName
				},
				auto: false
			};
		}
	},
	computed: {
		selectedCandidate() {
			return this.$resources.selectedCandidate.data;
		},
		candidates() {
			return this.$resources.candidates.data;
		}
	}
};
</script>
