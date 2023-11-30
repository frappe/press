<template>
	<div class="p-5" v-if="job">
		<Button variant="ghost" :route="{ name: `${object.doctype} Detail Jobs` }">
			<template #prefix>
				<i-lucide-arrow-left class="inline-block h-4 w-4" />
			</template>
			Back to all jobs
		</Button>

		<div class="mt-3">
			<div>
				<div class="flex items-center space-x-2">
					<h2 class="text-lg font-medium text-gray-900">{{ job.job_type }}</h2>
					<Badge :label="job.status" />
					<Button
						class="!ml-auto"
						@click="$resources.job.reload()"
						:loading="$resources.job.loading"
					>
						<template #prefix>
							<i-lucide-refresh-ccw class="h-4 w-4" />
						</template>
						Refresh
					</Button>
				</div>
				<div>
					<div class="mt-4 grid grid-cols-5 gap-4">
						<div>
							<div class="text-sm font-medium text-gray-500">Creation</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $dayjs(job.creation).toLocaleString() }}
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
								{{ $format.duration(job.duration) }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">Start</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $dayjs(job.start).toLocaleString() }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">End</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $dayjs(job.end).toLocaleString() }}
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

export default {
	name: 'JobPage',
	props: ['id', 'objectType'],
	data() {
		return {
			isOpen: {}
		};
	},
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
						step.isOpen = false;
					}
					return job;
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
		}
	},
	components: { Tooltip, FeatherIcon },
	mounted() {
		this.$socket.on('agent_job_update', data => {
			if (data.id === this.id) {
				if (!this.$resources.job.loading) {
					this.$resources.job.reload();
				}
			}
		});
		// reload job every minute, in case socket is not working
		this.reloadInterval = setInterval(() => {
			if (!this.$resources.job.loading) {
				this.$resources.job.reload();
			}
		}, 1000 * 60);
	},
	beforeUnmount() {
		this.$socket.off('agent_job_update');
		clearInterval(this.reloadInterval);
	}
};
</script>
