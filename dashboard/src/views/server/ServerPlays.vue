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
		plaResource(start) {
			return {
				method: 'press.api.server.plays',
				params: { name: this.server?.name, start },
				paged: true,
				keepData: true,
				auto: true
			};
		},
		playRoute(play) {
			return `/servers/${this.server.name}/plays/${play.name}`;
		}
	}
};
</script>
