<template>
	<SiteChangeGroupDialog :site="{ name: site }" v-model="show" />
</template>

<script>
import SiteChangeGroupDialog from '../../src/views/site/SiteChangeGroupDialog.vue';

export default {
	props: ['site'],
	components: { SiteChangeGroupDialog },
	data() {
		return {
			show: true
		};
	}
};
</script>
