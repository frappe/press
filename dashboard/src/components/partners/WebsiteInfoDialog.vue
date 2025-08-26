<template>
	<div class="flex flex-col gap-5">
		<div class="flex flex-col gap-4">
			<div v-for="field in fields" :key="field.fieldname">
				<FormControl
					v-model="websiteInfo[field.fieldname]"
					:label="field.label"
					:type="getInputType(field)"
					:name="field.fieldname"
					:required="field.required"
					:rows="10"
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

const fields = computed(() => {
	return [
		{
			fieldname: 'partner_website',
			label: 'Website URL',
			fieldtype: 'Data',
			required: true,
		},
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
