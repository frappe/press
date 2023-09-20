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
					class="block cursor-pointer rounded-md px-2.5"
					:class="
						selectedCandidate && selectedCandidate.name === candidate.name
							? 'bg-gray-100'
							: 'hover:bg-gray-50'
					"
					:key="candidate.name"
					:to="`/benches/${bench.name}/deploys/${candidate.name}`"
				>
					<ListItem
						:title="`Deploy on ${formatDate(
							candidate.creation,
							'DATETIME_SHORT'
						)}`"
						:subtitle="itemSubtitle(candidate)"
					>
						<template #actions>
							<Badge
								v-if="candidate.status != 'Success'"
								:label="candidate.status"
							>
							</Badge>
						</template>
					</ListItem>
					<div class="border-b"></div>
				</router-link>
				<div class="py-3" v-if="$resources.candidates.hasNextPage">
					<Button
						:loading="$resources.candidates.list.loading"
						loadingText="Loading..."
						@click="$resources.candidates.next()"
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
import { h } from 'vue';
import StepsDetail from '@/views/general/StepsDetail.vue';
import CardWithDetails from '@/components/CardWithDetails.vue';

export default {
	name: 'BenchDeploys',
	props: ['bench', 'benchName', 'candidateName'],
	components: {
		CardWithDetails,
		StepsDetail
	},
	resources: {
		candidates() {
			return {
				type: 'list',
				doctype: 'Deploy Candidate',
				url: 'press.api.bench.candidates',
				filters: {
					group: this.benchName
				},
				start: 0,
				auto: true,
				pageLength: 10
			};
		},
		selectedCandidate() {
			return {
				url: 'press.api.bench.candidate',
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
	unmounted() {
		this.$socket.off(`bench_deploy:${this.candidateName}:steps`, this.onSteps);
		this.$socket.off(
			`bench_deploy:${this.candidateName}:finished`,
			this.onStopped
		);
	},
	methods: {
		onSteps(data) {
			if (this.$resources.selectedCandidate?.data.name === data.name) {
				this.$resources.selectedCandidate.data.build_steps = data.steps;
			}
		},
		onStopped() {
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
						render() {
							return h(
								'Link',
								{
									props: { to: `/benches/${bench?.name}/jobs/${job.name}` },
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
				let duration = this.$formatDuration(
					this.selectedCandidate.build_duration
				);
				return `Completed ${when} in ${duration}`;
			} else if (this.selectedCandidate?.status === 'Running') {
				const when = this.formatDate(
					this.selectedCandidate.build_start,
					'relative'
				);
				return `Started ${when}`;
			} else if (this.selectedCandidate?.status === 'Failure') {
				const when = this.formatDate(
					this.selectedCandidate.build_end,
					'relative'
				);
				return `Failed ${when}`;
			}
		},
		candidates() {
			return this.$resources.candidates.data || [];
		}
	}
};
</script>
