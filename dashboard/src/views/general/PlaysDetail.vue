<template>
	<StepsDetail
		:showDetails="play"
		:loading="$resources.play.loading"
		:title="play ? play.play : ''"
		:subtitle="subtitle"
		:steps="steps"
	/>
</template>
<script>
import StepsDetail from './StepsDetail.vue';
export default {
	name: 'PlaysDetail',
	props: ['playName'],
	components: {
		StepsDetail
	},
	inject: ['viewportWidth'],
	resources: {
		play() {
			return {
				url: 'press.api.server.play',
				params: {
					play: this.playName
				},
				auto: Boolean(this.playName)
			};
		}
	},
	data() {
		return {
			runningPlay: null
		};
	},
	computed: {
		play() {
			return this.$resources.play.data;
		},
		subtitle() {
			if (!this.play) return;
			if (this.play.status == 'Success') {
				let when = this.formatDate(this.play.creation, 'relative');
				return `Completed ${when} in ${this.$formatDuration(
					this.play.duration,
					'hh:mm:ss'
				)}`;
			}
			if (this.play.status == 'Undelivered') {
				return 'play failed to start';
			}
			return null;
		},
		steps() {
			if (!this.play) return;
			return this.play.steps.map((step, index) => {
				return {
					name: step.task,
					status: step.status,
					output: step.output,
					running: this.isStepRunning(step),
					completed: this.isStepCompleted(step, index)
				};
			});
		}
	},
	mounted() {
		this.$socket.emit('doc_subscribe', 'Ansible Play', this.playName);
		this.$socket.on('ansible_play_update', this.onAnsiblePlayUpdate);
	},
	unmounted() {
		this.$socket.emit('doc_unsubscribe', 'Ansible Play', this.playName);
		this.$socket.off('ansible_play_update', this.onAnsiblePlayUpdate);
		this.runningPlay = null;
	},
	methods: {
		onAnsiblePlayUpdate(data) {
			if (data.id === this.playName) {
				this.runningPlay = data;
			}
		},
		isStepRunning(step) {
			if (!this.runningPlay) return false;
			let runningStep = this.runningPlay.steps.find(
				s => s.name == step.step_name
			);
			return runningStep?.status === 'Running';
		},
		isStepCompleted(step, index) {
			if (this.runningPlay) {
				return this.runningPlay.current.index > index;
			}
			return step.status === 'Success';
		}
	}
};
</script>
