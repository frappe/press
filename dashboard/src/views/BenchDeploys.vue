<template>
	<div>
		<CardWithDetails
			title="Deploys"
			:subtitle="
				candidates.length ? 'Deploys on your bench' : 'No deploys on your bench'
			"
			:show-details="selectedCandidate"
		>
			<div>
				<router-link
					v-for="candidate in candidates"
					class="block px-2.5 rounded-md cursor-pointer"
					:class="
						selectedCandidate && selectedCandidate.name === candidate.name
							? 'bg-gray-100'
							: 'hover:bg-gray-50'
					"
					:key="candidate.name"
					:to="`/benches/${bench.name}/deploys/${candidate.name}`"
				>
					<ListItem
						:title="
							`Deploy on ${formatDate(candidate.creation, 'DATETIME_SHORT')}`
						"
						:subtitle="itemSubtitle(candidate)"
					>
						<template #actions>
							<Badge
								v-if="candidate.status != 'Success'"
								:status="candidate.status"
							>
								{{ candidate.status }}
							</Badge>
						</template>
					</ListItem>
					<div class="border-b"></div>
				</router-link>
				<div class="py-3" v-if="!$resources.candidates.lastPageEmpty">
					<Button
						:loading="$resources.candidates.loading"
						loadingText="Loading..."
						@click="pageStart += 10"
					>
						Load more
					</Button>
				</div>
			</div>
			<template #details>
				<StepsDetail
					:showDetails="selectedCandidate"
					:loading="$resources.selectedCandidate.loading"
					:steps="getSteps(selectedCandidate)"
					title="Build Log"
					:subtitle="subtitle"
				/>
			</template>
		</CardWithDetails>
	</div>
</template>

<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import StepsDetail from './StepsDetail.vue';
export default {
	name: 'BenchDeploys',
	props: ['bench', 'candidateName'],
	components: {
		CardWithDetails,
		StepsDetail
	},
	data() {
		return {
			pageStart: 0
		};
	},
	resources: {
		candidates() {
			return {
				method: 'press.api.bench.candidates',
				params: {
					name: this.bench.name,
					start: this.pageStart
				},
				auto: true,
				paged: true,
				keepData: true,
				default: []
			};
		},
		selectedCandidate() {
			return {
				method: 'press.api.bench.candidate',
				params: {
					name: this.candidateName
				},
				validate() {
					if (!this.candidateName) {
						return 'Select a candidate first';
					}
				},
				auto: true
			};
		}
	},
	mounted() {
		if (this.candidateName && this.selectedCandidate?.status != 'Success') {
			this.$socket.on(`bench_deploy:${this.candidateName}:steps`, this.onSteps);
			this.$socket.on(
				`bench_deploy:${this.candidateName}:finished`,
				this.onStopped
			);
		}
	},
	destroyed() {
		this.$socket.off(`bench_deploy:${this.candidateName}:steps`, this.onSteps);
		this.$socket.off(
			`bench_deploy:${this.candidateName}:finished`,
			this.onStopped
		);
	},
	methods: {
		onSteps(data) {
			this.$resources.selectedCandidate.data.build_steps = data.steps;
		},
		onStopped() {
			this.$resources.candidates.reset();
			this.$resources.candidates.reload();
			this.$resources.selectedCandidate.reload();
		},
		getSteps(candidate) {
			if (!candidate) return [];
			let steps = candidate.build_steps.map(step => {
				let name = step.stage + ' - ' + step.step;
				let output =
					step.command || step.output
						? `${step.command || ''}\n${step.output || ''}`.trim()
						: '';
				let duration = ['Success', 'Failure'].includes(step.status)
					? step.cached
						? 'Cached'
						: `${step.duration} s`
					: null;
				return {
					name,
					output,
					status: step.status,
					duration,
					completed: step.status == 'Success',
					running: step.status == 'Running'
				};
			});

			let bench = this.bench;
			let jobs = candidate.jobs.map(job => {
				return {
					name: `Deploy ${job.bench}`,
					output:
						job.status == 'Success'
							? `Deploy completed in ${job.duration.split('.')[0]}`
							: null,
					status: job.status,
					completed: job.status == 'Success',
					running: ['Pending', 'Running'].includes(job.status),
					action: {
						render(h) {
							return h(
								'Link',
								{
									props: { to: `/benches/${bench.name}/jobs/${job.name}` },
									class: 'text-sm'
								},
								'Job Log →'
							);
						}
					}
				};
			});
			return [...steps, ...jobs];
		},
		itemSubtitle(candidate) {
			return ['frappe', ...candidate.apps.filter(d => d !== 'frappe')].join(
				', '
			);
		}
	},
	computed: {
		selectedCandidate() {
			return this.$resources.selectedCandidate.data;
		},
		subtitle() {
			if (
				this.selectedCandidate &&
				this.selectedCandidate.status == 'Success'
			) {
				let when = this.formatDate(
					this.selectedCandidate.build_end,
					'relative'
				);
				let duration = this.selectedCandidate.build_duration.split('.')[0];
				return `Completed ${when} in ${duration}`;
			}
		},
		candidates() {
			return this.$resources.candidates.data;
		}
	}
};
</script>
