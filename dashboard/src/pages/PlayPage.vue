<template>
	<div class="p-5" v-if="play">
		<Button :route="{ name: `${object.doctype} Detail Plays` }">
			<template #prefix>
				<lucide-arrow-left class="inline-block h-4 w-4" />
			</template>
			All plays
		</Button>

		<div class="mt-3">
			<div>
				<div class="flex items-center">
					<h2 class="text-lg font-medium text-gray-900">{{ play.play }}</h2>
					<Badge class="ml-2" :label="play.status" />
					<div class="ml-auto space-x-2">
						<Button
							@click="$resources.play.reload()"
							:loading="$resources.play.loading"
						>
							<template #icon>
								<lucide-refresh-ccw class="h-4 w-4" />
							</template>
						</Button>
						<Dropdown v-if="dropdownOptions.length" :options="dropdownOptions">
							<template v-slot="{ open }">
								<Button>
									<template #icon>
										<lucide-more-horizontal class="h-4 w-4" />
									</template>
								</Button>
							</template>
						</Dropdown>
					</div>
				</div>
				<div>
					<div class="mt-4 grid grid-cols-5 gap-4">
						<div>
							<div class="text-sm font-medium text-gray-500">Creation</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $format.date(play.creation, 'lll') }}
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
								{{ $format.date(play.start, 'lll') }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-gray-500">End</div>
							<div class="mt-2 text-sm text-gray-900">
								{{ $format.date(play.end, 'lll') }}
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
				},
			};
		},
	},
	computed: {
		object() {
			return getObject(this.objectType);
		},
		play() {
			return this.$resources.play.doc;
		},
		dropdownOptions() {
			return [
				{
					label: 'View in Desk',
					icon: 'external-link',
					condition: () => this.$team.doc?.is_desk_user,
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/ansible-play/${this.id}`,
							'_blank',
						);
					},
				},
			].filter((option) => option.condition?.() ?? true);
		},
	},
	mounted() {
		this.$socket.emit('doc_subscribe', 'Ansible Play', this.id);
		this.$socket.on('ansible_play_update', (data) => {
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
		},
	},
};
</script>
