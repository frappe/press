<template>
	<div class="space-y-10" v-if="site">
		<Card
			title="Site Config"
			subtitle="Add and update key value pairs to your site's site_config.json"
		>
			<template #actions>
				<Button
					icon-left="edit"
					v-if="['Active', 'Broken'].includes(site.status) && !editMode"
					@click="editMode = true"
				>
					Edit Config
				</Button>
				<Button
					v-if="editMode"
					:loading="$resources.siteConfig.loading"
					@click="
						() => {
							$resources.siteConfig.reload().then(() => {
								editMode = false;
								isDirty = false;
							});
						}
					"
				>
					Discard changes
				</Button>
				<Button
					appearance="primary"
					v-if="editMode"
					@click="updateSiteConfig"
					:loading="$resources.updateSiteConfig.loading"
				>
					Save changes
				</Button>
			</template>
			<ConfigEditor
				:configData="$resources.siteConfig.data"
				:standardConfigKeys="$resources.standardConfigKeys.data"
				:editMode="editMode"
				@isDirty="val => (isDirty = val)"
			/>
		</Card>
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
	resources: {
		siteConfig() {
			return {
				method: 'press.api.site.site_config',
				params: { name: this.site?.name },
				auto: true,
				default: []
			};
		},
		standardConfigKeys: 'press.api.config.standard_keys',
		updateSiteConfig() {
			let updatedConfig = this.$resources.siteConfig.data.map(d => {
				let value = d.value;
				if (d.type === 'Number') {
					value = Number(d.value);
				} else if (d.type == 'JSON') {
					try {
						value = JSON.parse(d.value || '{}');
					} catch (error) {}
				}
				return {
					key: d.key,
					value,
					type: d.type
				};
			});

			return {
				method: 'press.api.site.update_config',
				params: {
					name: this.site?.name,
					config: JSON.stringify(updatedConfig)
				},
				async validate() {
					let keys = updatedConfig.map(d => d.key);
					if (keys.length !== [...new Set(keys)].length) {
						return 'Duplicate key';
					}
					let invalidKeys = await this.$call('press.api.config.is_valid', {
						keys: JSON.stringify(keys)
					});
					if (invalidKeys?.length > 0) {
						return `Invalid key: ${invalidKeys.join(', ')}`;
					}
					for (let config of updatedConfig) {
						if (config.type === 'JSON') {
							try {
								JSON.parse(JSON.stringify(config.value));
							} catch (error) {
								return `Invalid JSON -- ${error}`;
							}
						} else if (config.type === 'Number') {
							try {
								Number(config.value);
							} catch (error) {
								return 'Invalid Number';
							}
						}
					}
				},
				onSuccess() {
					this.editMode = false;
					this.isDirty = false;
				}
			};
		}
	},
	methods: {
		updateSiteConfig() {
			if (this.isDirty) {
				this.$resources.updateSiteConfig.submit();
			} else {
				this.editMode = false;
				this.isDirty = false;
			}
		}
	}
};
</script>
