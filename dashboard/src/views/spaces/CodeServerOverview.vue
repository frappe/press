<template>
	<div class="grid grid-cols-1 gap-5 sm:grid-cols-2" v-if="codeServer">
		<CodeServerOverviewInfo :codeServer="codeServer" />
	</div>
</template>

<script>
import CodeServerOverviewInfo from './CodeServerOverviewInfo.vue';
export default {
	name: 'CodeServerOverview',
	components: {
		CodeServerOverviewInfo
	},
	props: {
		codeServer: {
			type: Object,
			default: () => {}
		}
	}
};
</script>
