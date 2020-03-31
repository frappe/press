<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Configuration</h2>
			<p class="text-gray-600">View and edit your site configuration</p>
			<div class="w-full sm:w-1/2 mt-6 shadow rounded border border-gray-100 px-6 py-4">
				<div
					v-for="(field, i) in fields"
					class="flex items-baseline"
					:class="[i !== 0 && 'mt-4']"
					:key="field.fieldname"
				>
					<label class="w-1/3 text-gray-800">{{ field.label }}</label>
					<div class="mt-2 w-2/3 px-4">
						<input
							:class="{
								'form-input w-full': ['text', 'number', 'email', 'password'].includes(
									field.fieldtype
								),
								'form-checkbox': ['checkbox'].includes(field.fieldtype)
							}"
							:type="field.fieldtype"
							v-model="siteConfig[field.fieldname]"
						/>
					</div>
				</div>
				<div class="mt-6">
					<Button class="text-white" 
						:class="showButton? 'bg-blue-500' : 'bg-blue-300 pointer-events-none'"
						:disabled="!showButton"
						@click="updateConfig">Update Configuration</Button>
				</div>
			</div>
		</section>
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
					label: 'Max File Size',
					fieldname: 'max_file_size',
					fieldtype: 'number'
				}
			],
			siteConfig: {
				mail_server: null,
				mail_port: null,
				mail_login: null,
				mail_password: null,
				use_ssl: null,
				auto_email_id: null,
				mute_emails: 0,
				server_script_enabled: 0,
				disable_website_cache: 0,
				disable_global_search: 0,
				max_file_size: 10240
			},
			showButton: false
		};
	},
	methods: {
		async updateConfig() {
			await this.$call('press.api.site.update_site', {
				name: this.site.name,
				config: this.siteConfig
			});
		}
	},
	watch: {
		siteConfig: {
			handler: function (value) {
				this.showButton = true;
			},
			deep: true
		}
	},
};
</script>
