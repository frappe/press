<template></template>

<script>
export default {
	name: 'SpacesList',
	data() {
		return {
			recentlyCreatedSites: []
		};
	},
	props: {
		spaces: {
			type: Object,
			default: () => {}
		}
	}
};
</script>
