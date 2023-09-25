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
	props: ['serverName', 'playName'],
	components: {
		AnsiblePlays
	},
	methods: {
		plaResource() {
			return {
				type: 'list',
				doctype: 'Ansible Play',
				url: 'press.api.server.plays',
				filters: { server: this.serverName },
				pageLength: 10,
				start: 0,
				auto: true
			};
		},
		playRoute(play) {
			return `/servers/${this.serverName}/plays/${play.name}`;
		}
	}
};
</script>
