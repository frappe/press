<template>
	<AnsiblePlays
		title="Plays"
		subtitle="History of ansible plays that ran on your server"
		:resource="plaResource"
		:playName="playName"
		:playRoute="playRoute"
	/>
</template>
<script>
import AnsiblePlays from '@/views/general/AnsiblePlays.vue';
export default {
	name: 'ServerPlays',
	props: ['server', 'playName'],
	components: {
		AnsiblePlays
	},
	methods: {
		plaResource() {
			return {
				type: 'list',
				doctype: 'Ansible Play',
				filters: { server: this.server?.name },
				fields: [
					'name',
					'play',
					'creation',
					'status',
					'start',
					'end',
					'duration'
				],
				pageLength: 10,
				start: 0,
				auto: true
			};
		},
		playRoute(play) {
			return `/servers/${this.server.name}/plays/${play.name}`;
		}
	}
};
</script>
