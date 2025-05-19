<template>
	<div class="">
		<div class="flex flex-col gap-5 overflow-y-auto px-60 py-6">
			<div class="flex justify-between">
				<div class="flex gap-3">
					<div>
						<h1 class="text-3xl font-semibold">
							{{ 'BlueChip corp' || lead?.name }}
						</h1>
					</div>
					<div>
						<Badge variant="subtle" theme="blue" size="lg" label="Open" />
					</div>
				</div>
				<div>
					<Button variant="solid">Update Status</Button>
				</div>
			</div>
			<div class="rounded-lg text-base text-gray-900 shadow">
				<div class="p-4">
					<div class="flex items-center justify-between pb-2">
						<div class="font-semibold text-xl">Company Information</div>
						<Button variant="subtle">Edit</Button>
					</div>
					<div class="my-1 h-px bg-gray-100" />
					<div class="pt-2">
						<div class="grid grid-cols-2 gap-4">
							<div v-for="item in company_info" class="flex-1">
								<div class="text-sm text-gray-600">
									{{ item.label }}
								</div>
								<div class="text-lg font-medium py-2">
									{{ item.value }}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="rounded-lg text-base text-gray-900 shadow">
				<div class="p-4">
					<div class="flex items-center justify-between pb-2">
						<div class="font-semibold text-xl">Contact Info</div>
						<Button variant="subtle">Edit</Button>
					</div>
					<div class="my-1 h-px bg-gray-100" />
					<div class="pt-2">
						<div class="grid grid-cols-2 gap-4">
							<div v-for="item in contact_info" class="flex-1">
								<div class="text-sm text-gray-600">
									{{ item.label }}
								</div>
								<div class="text-lg font-medium py-2">
									{{ item.value }}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import { Badge } from 'frappe-ui';
export default {
	name: 'PartnerLeadOverview',
	components: {
		Badge,
	},
	resources: {
		lead() {
			return {
				type: 'document',
				doctype: 'Partner Lead',
				name: this.$route.params.leadId,
			};
		},
	},
	computed: {
		company_info() {
			// console.log(this.$route.params);
			return [
				{ label: 'Company Name', value: 'BlueChip Corp' },
				{ label: 'Lead Source', value: 'ERPNext Contact Us' },
				{ label: 'Lead Type', value: 'Frappe HR' },
				{ label: 'Engagement Stage', value: 'Demo' },
				{ label: 'Industry', value: 'Manufacturing' },
			];
		},
		contact_info() {
			return [
				{ label: 'Full Name', value: 'Brian Pod' },
				{ label: 'Email', value: 'brian@gmail.com' },
				{ label: 'Country', value: 'United States' },
				{ label: 'State', value: 'California' },
				{ label: 'Territory', value: 'US' },
				{ label: 'Contact', value: '892346181' },
			];
		},
		lead() {
			console.log(this.$resources.lead);
			return this.$resources.lead.doc;
		},
	},
};
</script>
