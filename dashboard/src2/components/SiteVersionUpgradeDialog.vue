<template>
	<SiteVersionUpgradeDialog :site="$resources.siteData.data" v-model="show" />
</template>

<script>
import SiteVersionUpgradeDialog from '../../src/views/site/SiteVersionUpgradeDialog.vue';

export default {
	props: ['site'],
	components: { SiteVersionUpgradeDialog },
	data() {
		return {
			show: true
		};
	},
	resources: {
		siteData() {
			return {
				url: 'press.api.site.get',
				params: {
					name: this.site
				},
				auto: true,
				initialData: {
					name: this.site
				}
			};
		}
	}
};
</script>
