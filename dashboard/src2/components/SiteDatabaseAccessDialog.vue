<template>
	<DatabaseAccessDialog :site="site" v-model="show" />
</template>
<script>
import DatabaseAccessDialog from '../../src/views/site/DatabaseAccessDialog.vue';
export default {
	name: 'SiteDatabaseAccessDialog',
	props: ['site'],
	components: { DatabaseAccessDialog },
	data() {
		return {
			show: true
		};
	}
};
</script>
