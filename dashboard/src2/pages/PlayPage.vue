<template>
	<div class="p-5" v-if="play">
		<Button :route="{ name: `${object.doctype} Detail Plays` }">
			<template #prefix>
				<i-lucide-arrow-left class="inline-block h-4 w-4" />
			</template>
			All plays
		</Button>

		<div class="mt-3">
			<div>
				<div class="flex items-center space-x-2">
					<h2 class="text-lg font-medium text-gray-900">{{ play.play }}</h2>
					<Badge :label="play.status" />
					<Button
						class="!ml-auto"
						@click="$resources.play.reload()"
						:loading="$resources.play.loading"
					>
						<template #icon>
							<i-lucide-refresh-ccw class="h-4 w-4" />
						</template>
					</Button>
				</div>
				<div>
					<div class="mt-4 grid grid-cols-5 gap-4">
						<div>
							<div class="text-sm font-medium text-gray-500">Creation</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $format.date(play.creation) }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">Creator</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ play.owner }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">Duration</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $format.duration(play.duration) }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">Start</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $format.date(play.start) }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">End</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $format.date(play.end) }}
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="mt-8 space-y-4">
				<JobStep v-for="task in play.tasks" :step="task" :key="task.name" />
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
	name: 'PlayPage',
	props: ['id', 'objectType'],
	components: { Tooltip, FeatherIcon, JobStep },
	resources: {
		play() {
			return {
				type: 'document',
				doctype: 'Ansible Play',
				name: this.id,
				transform(play) {
					for (let task of play.tasks) {
						task.title = task.task;
						task.duration = duration(task.duration);
						task.isOpen = false;
					}
					return play;
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
		play() {
			return this.$resources.play.doc;
		}
	},
	mounted() {
		this.$socket.emit('doc_subscribe', 'Ansible Play', this.id);
		this.$socket.on('ansible_play_update', data => {
			if (data.id === this.id) {
				this.reload();
			}
		});
		// reload play every minute, in case socket is not working
		this.reloadInterval = setInterval(() => {
			this.reload();
		}, 1000 * 60);
	},
	beforeUnmount() {
		this.$socket.emit('doc_unsubscribe', 'Ansible Play', this.id);
		this.$socket.off('ansible_play_update');
		clearInterval(this.reloadInterval);
	},
	methods: {
		reload() {
			if (
				!this.$resources.play.loading &&
				// reload if play was loaded more than 5 seconds ago
				Date.now() - this.lastLoaded > 5000
			) {
				this.$resources.play.reload();
			}
		}
	}
};
</script>
