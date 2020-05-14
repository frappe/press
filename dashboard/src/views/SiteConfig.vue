<template>
	<div>
		<Section
			title="Configuration"
			description="View and edit your site configuration"
		>
			<SectionCard class="px-6 py-4">
				<div
					v-for="(field, i) in fields"
					class="flex items-baseline"
					:class="[i !== 0 && 'mt-4']"
					:key="field.fieldname"
				>
					<label class="w-1/3 text-gray-800">{{ field.label }}</label>
					<div class="w-2/3 px-4 mt-2">
						<input
							:class="{
								'form-input w-full': [
									'text',
									'number',
									'email',
									'password'
								].includes(field.fieldtype),
								'form-checkbox': ['checkbox'].includes(field.fieldtype)
							}"
							:type="field.fieldtype"
							v-model="siteConfig[field.fieldname]"
						/>
					</div>
				</div>
				<div class="mt-6">
					<Button :disabled="!showButton" type="primary" @click="updateConfig">
						Update Configuration
					</Button>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'SiteConfig',
	props: ['site'],
	data() {
		return {
			fields: [
				{
					label: 'Encryption Key',
					fieldname: 'encryption_key',
					fieldtype: 'password'
				},
				{
					label: 'Mail Server',
					fieldname: 'mail_server',
					fieldtype: 'text'
				},
				{
					label: 'Mail Port',
					fieldname: 'mail_port',
					fieldtype: 'number'
				},
				{
					label: 'Mail Login',
					fieldname: 'mail_login',
					fieldtype: 'text'
				},
				{
					label: 'Mail Password',
					fieldname: 'mail_password',
					fieldtype: 'password'
				},
				{
					label: 'Use SSL',
					fieldname: 'use_ssl',
					fieldtype: 'checkbox'
				},
				{
					label: 'Auto Email Address',
					fieldname: 'auto_email_id',
					fieldtype: 'email'
				},
				{
					label: 'Mute Emails',
					fieldname: 'mute_emails',
					fieldtype: 'checkbox'
				},
				{
					label: 'Enable Server Scripts',
					fieldname: 'server_script_enabled',
					fieldtype: 'checkbox'
				},
				{
					label: 'Disable Website Cache',
					fieldname: 'disable_website_cache',
					fieldtype: 'checkbox'
				},
				{
					label: 'Disable Global Search',
					fieldname: 'disable_global_search',
					fieldtype: 'checkbox'
				},
				{
					label: 'Max File Size (Bytes)',
					fieldname: 'max_file_size',
					fieldtype: 'number'
				}
			],
			siteConfig: {
				encryption_key: this.site.config.encryption_key,
				mail_server: this.site.config.mail_server,
				mail_port: this.site.config.mail_port,
				mail_login: this.site.config.mail_login,
				mail_password: this.site.config.mail_password,
				use_ssl: this.site.config.use_ssl,
				auto_email_id: this.site.config.auto_email_id,
				mute_emails: this.site.config.mute_emails,
				server_script_enabled: this.site.config.server_script_enabled,
				disable_website_cache: this.site.config.disable_website_cache,
				disable_global_search: this.site.config.disable_global_search,
				max_file_size: this.site.config.max_file_size
			},
			showButton: false
		};
	},
	methods: {
		async updateConfig() {
			await this.$call('press.api.site.update_config', {
				name: this.site.name,
				config: this.siteConfig
			});
			this.showButton = false;
		}
	},
	watch: {
		siteConfig: {
			handler: function() {
				this.showButton = true;
			},
			deep: true
		}
	}
};
</script>
