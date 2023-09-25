<template>
	<div>
		<CardWithDetails
			title="Deploys"
			:subtitle="
				deployments.length
					? 'Deploys on your stack'
					: 'No deploys on your stack'
			"
			:show-details="selectedDeployment"
		>
			<div>
				<router-link
					v-for="deployment in deployments"
					class="block cursor-pointer rounded-md px-2.5"
					:class="
						selectedDeployment && selectedDeployment.name === deployment.name
							? 'bg-gray-100'
							: 'hover:bg-gray-50'
					"
					:key="deployment.name"
					:to="`/stacks/${stack.name}/deploys/${deployment.name}`"
				>
					<ListItem
						:title="`Deploy on ${formatDate(
							deployment.creation,
							'DATETIME_SHORT'
						)}`"
					>
						<template #actions>
							<Badge
								v-if="deployment.status != 'Success'"
								:label="deployment.status"
							>
							</Badge>
						</template>
					</ListItem>
					<div class="border-b"></div>
				</router-link>
				<div class="py-3" v-if="$resources.deployments.hasNextPage">
					<Button
						:loading="$resources.deployments.loading"
						loadingText="Loading..."
						@click="$resources.deployments.next()"
					>
						Load more
					</Button>
				</div>
			</div>
			<template #details>
				<StepsDetail
					:showDetails="selectedDeployment"
					:loading="$resources.selectedDeployment.loading"
					:steps="getSteps(selectedDeployment)"
					title="Deploy Log"
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
	name: 'StackDeploys',
	props: ['stack', 'deploymentName'],
	components: {
		CardWithDetails,
		StepsDetail
	},
	resources: {
		deployments() {
			return {
				type: 'list',
				doctype: 'Deployment',
				url: 'press.api.stack.deployments',
				filters: {
					stack: this.stack?.name
				},
				start: 0,
				auto: true,
				pageLength: 10
			};
		},
		selectedDeployment() {
			return {
				url: 'press.api.stack.deployment',
				params: {
					name: this.deploymentName
				},
				validate() {
					if (!this.deploymentName) {
						return 'Select a deployment first';
					}
				},
				auto: true
			};
		}
	},
	mounted() {
		if (this.deploymentName && this.selectedDeployment?.status != 'Success') {
			this.$socket.on(`stack_deploy:${this.deploymentName}:jobs`, this.onJobs);
			this.$socket.on(
				`stack_deploy:${this.deploymentName}:finished`,
				this.onStopped
			);
		}
	},
	unmounted() {
		this.$socket.off(`stack_deploy:${this.deploymentName}:jobs`, this.onJobs);
		this.$socket.off(
			`stack_deploy:${this.deploymentName}:finished`,
			this.onStopped
		);
	},
	methods: {
		onJobs(data) {
			if (this.$resources.selectedDeployment?.data.name === data.name) {
				this.$resources.selectedDeployment.data.jobs = data.jobs;
			}
		},
		onStopped() {
			this.$resources.deployments.reload();
			this.$resources.selectedDeployment.reload();
		},
		getSteps(deployment) {
			if (!deployment) return [];

			let stack = this.stack;
			let jobs = deployment.jobs.map(job => {
				return {
					name: `Deploy ${job.service}`,
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
									props: { to: `/stacks/${stack?.name}/jobs/${job.name}` },
									class: 'text-sm'
								},
								'Job Log →'
							);
						}
					}
				};
			});
			return [...jobs];
		}
	},
	computed: {
		selectedDeployment() {
			return this.$resources.selectedDeployment.data;
		},
		subtitle() {
			if (
				this.selectedDeployment &&
				this.selectedDeployment.status == 'Success'
			) {
				let when = this.formatDate(this.selectedDeployment.end, 'relative');
				let duration = this.$formatDuration(this.selectedDeployment.duration);
				return `Completed ${when} in ${duration}`;
			} else if (this.selectedDeployment?.status === 'Running') {
				const when = this.formatDate(this.selectedDeployment.start, 'relative');
				return `Started ${when}`;
			} else if (this.selectedDeployment?.status === 'Failure') {
				const when = this.formatDate(this.selectedDeployment.end, 'relative');
				return `Failed ${when}`;
			}
		},
		deployments() {
			return this.$resources.deployments.data || [];
		}
	}
};
</script>
