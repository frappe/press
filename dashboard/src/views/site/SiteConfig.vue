<template>
	<ConfigEditor
		v-if="site"
		title="Site Config"
		subtitle="Add and update key value pairs to your site's site_config.json"
		configName="site_config.json"
		:configData="siteConfig"
		:updateConfigMethod="updateSiteConfig"
	/>
</template>

<script>
import ConfigEditor from '@/components/ConfigEditor.vue';

export default {
	name: 'SiteConfig',
	components: {
		ConfigEditor
	},
	props: ['site'],
	data() {
		return {
			editMode: false,
			isDirty: false
		};
	},
	methods: {
		siteConfig() {
			return {
				url: 'press.api.site.site_config',
				params: { name: this.site?.name },
				auto: true,
				initialData: []
			};
		},
		updateSiteConfig(updatedConfig) {
			return {
				url: 'press.api.site.update_config',
				params: {
					name: this.site?.name,
					config: JSON.stringify(updatedConfig)
				}
			};
		}
	}
};
</script>
