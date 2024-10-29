<template>
	<div class="p-5" v-if="job">
		<Button
			:route="{
				name:
					object.doctype === 'Site'
						? 'Site Jobs'
						: `${object.doctype} Detail Jobs`
			}"
		>
			<template #prefix>
				<i-lucide-arrow-left class="inline-block h-4 w-4" />
			</template>
			All jobs
		</Button>

		<div class="mt-3">
			<div>
				<div class="flex items-center">
					<h2 class="text-lg font-medium text-gray-900">{{ job.job_type }}</h2>
					<Badge class="ml-2" :label="job.status" />
					<div class="ml-auto space-x-2">
						<Button
							@click="$resources.job.reload()"
							:loading="$resources.job.loading"
						>
							<template #icon>
								<i-lucide-refresh-ccw class="h-4 w-4" />
							</template>
						</Button>
						<Dropdown v-if="dropdownOptions.length" :options="dropdownOptions">
							<template v-slot="{ open }">
								<Button>
									<template #icon>
										<i-lucide-more-horizontal class="h-4 w-4" />
									</template>
								</Button>
							</template>
						</Dropdown>
					</div>
				</div>
				<div>
					<div
						class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5"
					>
						<div>
							<div class="text-sm font-medium text-gray-500">Creation</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $format.date(job.creation, 'lll') }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">Creator</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ job.owner }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">Duration</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ job.end ? $format.duration(job.duration) : '-' }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">Start</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $format.date(job.start, 'lll') }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">End</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ job.end ? $format.date(job.end, 'lll') : '-' }}
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="mt-8 space-y-4">
				<JobStep v-for="step in job.steps" :step="step" :key="step.name" />
			</div>
		</div>
	</div>
</template>
<script>
import { FeatherIcon, Tooltip } from 'frappe-ui';
import { duration } from '../utils/format';
import { getObject } from '../objects';
import JobStep from '../components/JobStep.vue';

export default {
	name: 'JobPage',
	props: ['id', 'objectType'],
	components: { Tooltip, FeatherIcon, JobStep },
	resources: {
		job() {
			return {
				type: 'document',
				doctype: 'Agent Job',
				name: this.id,
				transform(job) {
					for (let step of job.steps) {
						step.title = step.step_name;
						step.duration = duration(step.duration);
						step.isOpen =
							this.job?.steps?.find(s => s.name === step.name)?.isOpen || false;
					}

					// on delivery failure, there'll be no output for any step
					// so show the job output (error) in the first step
					if (job.status === 'Delivery Failure') {
						job.steps[0].output = job.output;
					}

					return job;
				},
				onSuccess() {
					this.lastLoaded = Date.now();
				}
			};
		}
	},
	computed: {
		object() {
			return getObject(this.objectType);
		},
		job() {
			return this.$resources.job.doc;
		},
		dropdownOptions() {
			return [
				{
					label: 'View in Desk',
					icon: 'external-link',
					condition: () => this.$team?.doc?.is_desk_user,
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/agent-job/${this.id}`,
							'_blank'
						);
					}
				}
			].filter(option => option.condition?.() ?? true);
		}
	},
	mounted() {
		this.$socket.emit('doc_subscribe', 'Agent Job', this.id);
		this.$socket.on('agent_job_update', data => {
			if (data.id === this.id) {
				data.steps = data.steps.map(step => {
					step.title = step.step_name;
					step.duration = duration(step.duration);
					step.isOpen =
						this.job?.steps?.find(s => s.name === step.name)?.isOpen || false;
					return step;
				});

				this.$resources.job.doc = {
					...this.$resources.job.doc,
					...data
				};
			}
		});
		// reload job every minute, in case socket is not working
		this.reloadInterval = setInterval(() => {
			this.reload();
		}, 1000 * 60);
	},
	beforeUnmount() {
		this.$socket.emit('doc_unsubscribe', 'Agent Job', this.id);
		this.$socket.off('agent_job_update');
		clearInterval(this.reloadInterval);
	},
	methods: {
		reload() {
			if (
				!this.$resources.job.loading &&
				// reload if job was loaded more than 5 seconds ago
				Date.now() - this.lastLoaded > 5000
			) {
				this.$resources.job.reload();
			}
		}
	}
};
</script>
