<template>
	<div class="flex flex-col gap-5">
		<div
			v-for="section in sections"
			:key="section.name"
			class="grid gap-5"
			:class="'grid-cols-' + section.columns"
		>
			<div v-for="field in section.fields" :key="field.name">
				<FormControl
					v-model="websiteInfo[field.fieldname]"
					:label="field.label || field.fieldname"
					:type="getInputType(field)"
					:name="field.fieldname"
					:options="field.options"
					:required="field.required"
				/>
			</div>
		</div>
		<div>
			<Button
				class="w-full"
				variant="solid"
				label="Update Website Info"
				@click="_updateWebsiteInfo()"
			/>
		</div>
	</div>
</template>
<script setup>
import { FormControl, createResource } from 'frappe-ui';
import { computed } from 'vue';
import { toast } from 'vue-sonner';

const websiteInfo = defineModel();
const emit = defineEmits(['success']);

const updateWebsiteInfo = createResource({
	url: 'press.api.partner.update_website_info',
	params: {
		website_info: websiteInfo.value,
	},
	onSuccess: () => {
		toast.success('Website info updated successfully');
		emit('success');
	},
});

function _updateWebsiteInfo() {
	updateWebsiteInfo.submit();
}

const sections = computed(() => {
	return [
		{
			name: 'Website & Contact',
			columns: 2,
			fields: [
				{
					fieldname: 'partner_website',
					label: 'Website URL',
					fieldtype: 'Data',
					required: true,
				},
				{
					fieldname: 'phone_number',
					label: 'Contact',
					fieldtype: 'Data',
				},
			],
		},
		{
			name: 'Foundation',
			columns: 2,
			fields: [
				{
					fieldname: 'custom_journey_blog_link',
					label: 'Journey Blog Link',
					fieldtype: 'Data',
				},
				{
					fieldname: 'custom_foundation_date',
					label: 'Foundation Date',
					fieldtype: 'Date',
				},
			],
		},
		{
			name: 'Projects & Team',
			columns: 2,
			fields: [
				{
					fieldname: 'custom_team_size',
					label: 'Team Size',
					fieldtype: 'Int',
				},
				{
					fieldname: 'custom_successful_projects_count',
					label: 'Successfull Projects',
					fieldtype: 'Int',
				},
			],
		},
		{
			name: 'Address',
			columns: 1,
			fields: [
				{
					fieldname: 'address',
					label: 'Address',
					fieldtype: 'Text',
				},
			],
		},
		{
			name: 'Additional Info',
			columns: 2,
			fields: [
				{
					fieldname: 'introduction',
					label: 'Introduction',
					fieldtype: 'Text',
				},
				{
					fieldname: 'customers',
					label: 'Customers',
					fieldtype: 'Text',
				},
			],
		},
	];
});

function getInputType(field) {
	return {
		Data: 'text',
		Int: 'number',
		Select: 'select',
		Check: 'checkbox',
		Password: 'password',
		Text: 'textarea',
		Date: 'date',
	}[field.fieldtype || 'Data'];
}
</script>
