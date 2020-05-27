<template>
	<div>
		<Section
			title="Configuration"
			description="View and edit your site configuration"
		>
			<SectionCard class="px-6 py-6 space-y-4">
				<Form :fields="fields" v-model="siteConfig" />
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
import Form from '@/components/Form';

export default {
	name: 'SiteConfig',
	components: {
		Form
	},
	props: ['site'],
	data() {
		return {
			fields: [
				{
					label: 'Encryption Key',
					fieldname: 'encryption_key',
					fieldtype: 'Password'
				},
				{
					label: 'Mail Server',
					fieldname: 'mail_server',
					fieldtype: 'Data'
				},
				{
					label: 'Mail Port',
					fieldname: 'mail_port',
					fieldtype: 'Int'
				},
				{
					label: 'Mail Login',
					fieldname: 'mail_login',
					fieldtype: 'Data'
				},
				{
					label: 'Mail Password',
					fieldname: 'mail_password',
					fieldtype: 'Password'
				},
				{
					label: 'Use SSL',
					fieldname: 'use_ssl',
					fieldtype: 'Check'
				},
				{
					label: 'Auto Email Address',
					fieldname: 'auto_email_id',
					fieldtype: 'Data'
				},
				{
					label: 'Mute Emails',
					fieldname: 'mute_emails',
					fieldtype: 'Check'
				},
				{
					label: 'Enable Server Scripts',
					fieldname: 'server_script_enabled',
					fieldtype: 'Check'
				},
				{
					label: 'Disable Website Cache',
					fieldname: 'disable_website_cache',
					fieldtype: 'Check'
				},
				{
					label: 'Disable Global Search',
					fieldname: 'disable_global_search',
					fieldtype: 'Check'
				},
				{
					label: 'Max File Size (Bytes)',
					fieldname: 'max_file_size',
					fieldtype: 'Int'
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
