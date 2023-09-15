<template>
	<NginxAccessRule :server="server" />
</template>

<script>
import NginxAccessRule from './NginxAccessRule.vue';

export default {
	name: 'Nginx',
	props: ['server'],
	components: {
		NginxAccessRule
	}
};
</script>
