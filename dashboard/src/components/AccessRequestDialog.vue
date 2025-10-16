<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Access Request',
			actions: [
				{
					label: 'Cancel',
					variant: 'outline',
					onClick: () => (open = false),
				},
				{
					label: 'Request',
					variant: 'solid',
					onClick: () => request.submit(),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<p>Are you sure you want to request access to this resource?</p>
				<div class="space-y-2">
					<p><span class="font-medium">Type:</span> {{ props.doctype }}</p>
					<p><span class="font-medium">Resource:</span> {{ props.docname }}</p>
				</div>
				<Textarea
					size="sm"
					placeholder="Why do you need access?"
					v-model="extra.reason"
				/>
				<div class="space-y-2">
					<p class="font-medium">Permissions:</p>
					<div class="grid grid-cols-2 gap-2">
						<Checkbox
							label="Login as Administrator"
							v-model="extra.loginAsAdministrator"
						/>
						<Checkbox label="Site Domains" v-model="extra.siteDomains" />
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { createResource } from 'frappe-ui';
import { reactive, ref } from 'vue';
import { toast } from 'vue-sonner';
import { Checkbox, Textarea } from 'frappe-ui';

const props = defineProps<{
	doctype: string;
	docname: string;
}>();

const open = ref(true);

const extra = reactive({
	reason: '',
	loginAsAdministrator: false,
	siteDomains: false,
});

const request = createResource({
	url: 'press.api.client.insert',
	makeParams: () => ({
		doc: {
			doctype: 'Support Access',
			reason: extra.reason,
			login_as_administrator: extra.loginAsAdministrator,
			site_domains: extra.siteDomains,
			resources: [
				{
					document_type: props.doctype,
					document_name: props.docname,
				},
			],
		},
	}),
	onSuccess: () => {
		open.value = false;
		toast.success('Access request submitted');
	},
	onError: () => toast.error('There was an error submitting your request'),
});
</script>
