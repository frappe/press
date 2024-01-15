<template>
	<SiteTransferDialog :site="site" v-model="show" />
</template>

<script>
import SiteTransferDialog from '../../src/views/site/SiteTransferDialog.vue';

export default {
	props: ['site'],
	components: { SiteTransferDialog },
	data() {
		return {
			show: true
		};
	}
};
</script>
