<template>
	<SiteChangeServerDialog :site="siteDoc.doc" v-model="show" />
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import SiteChangeServerDialog from '../../src/views/site/SiteChangeServerDialog.vue';

export default {
	name: 'SiteChangeServerDialogWrapper',
	props: ['site'],
	components: { SiteChangeServerDialog },
	data() {
		return {
			show: true,
			siteDoc: getCachedDocumentResource('Site', this.site)
		};
	}
};
</script>
