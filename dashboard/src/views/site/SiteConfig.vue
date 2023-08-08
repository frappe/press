<template>
	<div class="space-y-6" v-if="site">
		<ConfigEditor
			title="Site Config"
			subtitle="Add and update key value pairs to your site's site_config.json"
			configName="site_config.json"
			:configData="siteConfig"
			:updateConfigMethod="updateSiteConfig"
		/>
	</div>
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
				method: 'press.api.site.site_config',
				params: { name: this.site?.name },
				auto: true,
				default: []
			};
		},
		updateSiteConfig(updatedConfig) {
			return {
				method: 'press.api.site.update_config',
				params: {
					name: this.site?.name,
					config: JSON.stringify(updatedConfig)
				}
			};
		}
	}
};
</script>
