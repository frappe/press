<template>
	<SiteChangeRegionDialog :site="siteDoc.doc" v-model="show" />
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import SiteChangeRegionDialog from '../../src/views/site/SiteChangeRegionDialog.vue';

export default {
	props: ['site'],
	components: { SiteChangeRegionDialog },
	data() {
		return {
			show: true,
			siteDoc: getCachedDocumentResource('Site', this.site)
		};
	}
};
</script>
