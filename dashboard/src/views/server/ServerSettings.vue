<template>
	<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
		<Tags
			v-if="server"
			:name="server.name"
			doctype="Server"
			:resourceTags="server.server_tags"
			:tags="server.tags"
		/>
	</div>
</template>

<script>
import Tags from '@/components/Tags.vue';

export default {
	name: 'ServerSettings',
	props: ['server'],
	components: {
		Tags
	}
};
</script>
