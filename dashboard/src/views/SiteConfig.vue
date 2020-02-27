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
								'form-input w-full': ['text', 'number'].includes(
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
					<Button class="bg-brand text-white">Update Configuration</Button>
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
					fieldtype: 'text'
				},
				{
					label: 'Use SSL',
					fieldname: 'use_ssl',
					fieldtype: 'checkbox'
				},
				{
					label: 'Mute Emails',
					fieldname: 'mute_emails',
					fieldtype: 'checkbox'
				},
				{
					label: 'Disable Website Cache',
					fieldname: 'disable_website_cache',
					fieldtype: 'checkbox'
				},
				{
					label: 'Developer Mode',
					fieldname: 'developer_mode',
					fieldtype: 'checkbox'
				},
				{
					label: 'Max File Size',
					fieldname: 'max_file_size',
					fieldtype: 'number'
				}
			],
			siteConfig: {
				developer_mode: 1,
				mute_emails: 0,
				disable_website_cache: 0,
				max_file_size: 10240
			}
		};
	}
};
</script>
