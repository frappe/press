<template>
	<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
		<Tags
			v-if="site"
			:name="site.name"
			doctype="Site"
			:resourceTags="site.site_tags"
			:tags="site.tags"
		/>
	</div>
</template>

<script>
import Tags from '@/components/Tags.vue';

export default {
	name: 'SiteSetting',
	props: ['site'],
	components: {
		Tags
	}
};
</script>
