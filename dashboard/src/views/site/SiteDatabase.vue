<template>
	<div v-if="site" class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<SiteDatabaseBackups :site="site" />
		<SiteDatabaseRestore :site="site" />
	</div>
</template>

<script>
import SiteDatabaseBackups from './SiteDatabaseBackups.vue';
import SiteDatabaseRestore from './SiteDatabaseRestore.vue';

export default {
	name: 'SiteDatabase',
	props: ['site'],
	components: { SiteDatabaseBackups, SiteDatabaseRestore }
};
</script>
