<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<SiteDatabaseBackups :site="site" />
		<div v-if="site.status == 'Active'">
			<SiteDatabaseRestore :site="site" />
		</div>
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
