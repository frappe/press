<template>
	<div v-if="lead">
		<div class="flex flex-col gap-5 overflow-y-auto px-60 py-6">
			<div class="flex justify-between">
				<div class="flex gap-3">
					<div>
						<h1 class="text-3xl font-semibold">
							{{ lead?.organization_name }}
						</h1>
					</div>
					<div>
						<Badge
							variant="subtle"
							:theme="themeMap[lead?.status]"
							size="lg"
							:label="lead?.status"
						/>
					</div>
				</div>
				<div class="shrink-0">
					<Dropdown :options="statusOptions">
						<template #default="{ open }">
							<Button :label="lead?.status || 'Status'" variant="solid">
								<template #suffix>
									<FeatherIcon
										:name="open ? 'chevron-up' : 'chevron-down'"
										class="h-4"
									/>
								</template>
							</Button>
						</template>
					</Dropdown>
				</div>
			</div>
			<div class="rounded-lg text-base text-gray-900 shadow">
				<div class="p-4">
					<div class="flex items-center justify-between pb-2">
						<div class="font-semibold text-xl">Company Information</div>
						<Button
							variant="subtle"
							@click="
								() => {
									console.log('clicked');
									showLeadDetailsDialog = true;
								}
							"
						>
							Edit
						</Button>
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
		<LeadDetailsDialog
			v-if="showLeadDetailsDialog"
			v-model="showLeadDetailsDialog"
			@success="
				() => {
					$resources.lead.reload();
					showLeadDetailsDialog = false;
				}
			"
		/>
		<UpdateEngagementStageDialog
			v-if="showUpdateEngagementStageDialog"
			v-model="showUpdateEngagementStageDialog"
			:lead_id="lead.name"
			@update="
				() => {
					$resources.lead.reload();
					showUpdateEngagementStageDialog = false;
				}
			"
		/>
		<UpdateWonDialog
			v-if="showUpdateWonDialog"
			v-model="showUpdateWonDialog"
			:lead_id="lead.name"
			@update="
				() => {
					$resources.lead.reload();
					showUpdateWonDialog = false;
				}
			"
		/>
		<UpdateLostDialog
			v-if="showUpdateLostDialog"
			v-model="showUpdateLostDialog"
			:lead_id="lead.name"
			@update="
				() => {
					$resources.lead.reload();
					showUpdateLostDialog = false;
				}
			"
		/>
	</div>
</template>
<script>
import { Badge, FeatherIcon } from 'frappe-ui';
import LeadDetailsDialog from './LeadDetailsDialog.vue';
import UpdateWonDialog from './UpdateWonDialog.vue';
import { h } from 'vue';
import DropdownItem from '../billing/DropdownItem.vue';
import UpdateEngagementStageDialog from './UpdateEngagementStageDialog.vue';
import UpdateLostDialog from './UpdateLostDialog.vue';
export default {
	name: 'PartnerLeadOverview',
	components: {
		Badge,
		LeadDetailsDialog,
		UpdateWonDialog,
		DropdownItem,
		UpdateEngagementStageDialog,
		UpdateLostDialog,
	},
	data() {
		return {
			showLeadDetailsDialog: false,
			showDialog: false,
			showUpdateEngagementStageDialog: false,
			showUpdateWonDialog: false,
			showUpdateLostDialog: false,
		};
	},
	emits: ['success'],
	resources: {
		lead() {
			return {
				type: 'document',
				doctype: 'Partner Lead',
				name: this.$route.params.leadId,
			};
		},
		updateStatus() {
			return {
				url: 'press.api.partner.update_lead_status',
				makeParams: (params) => {
					return {
						lead_name: this.lead.name,
						status: params.status,
					};
				},
				onSuccess: () => {
					this.$resources.lead.reload();
				},
			};
		},
	},
	computed: {
		company_info() {
			return [
				{ label: 'Company Name', value: this.lead?.organization_name },
				{ label: 'Lead Source', value: this.lead?.lead_source },
				{ label: 'Lead Type', value: this.lead?.lead_type },
				{
					label: 'Engagement Stage',
					value: this.lead?.engagement_stage,
					condition: this.lead?.status === 'In Process',
				},
				{ label: 'Industry', value: this.lead?.domain },
				{
					label: 'Conversion Date',
					value: this.lead?.conversion_date,
					condition: this.lead?.status === 'Won',
				},
			].filter((d) => d.condition ?? true);
		},
		contact_info() {
			return [
				{ label: 'Full Name', value: this.lead?.full_name },
				{ label: 'Email', value: this.lead?.email },
				{ label: 'Country', value: this.lead?.country },
				{ label: 'State', value: this.lead?.state },
				{ label: 'Territory', value: this.lead?.territory },
				{ label: 'Contact', value: this.lead?.contact_no },
			];
		},
		lead() {
			return this.$resources.lead.doc;
		},
		statusOptions() {
			return [
				{
					label: 'Open',
					value: 'Open',
					component: () =>
						h(DropdownItem, {
							label: 'Open',
							onClick: () => {
								this._updateStatus('Open');
							},
						}),
				},
				{
					label: 'In Process',
					value: 'In Process',
					component: () =>
						h(DropdownItem, {
							label: 'In Process',
							onClick: () => {
								this._updateStatus('In Process');
							},
						}),
				},
				{
					label: 'Won',
					value: 'Won',
					component: () =>
						h(DropdownItem, {
							label: 'Won',
							onClick: () => {
								this._updateStatus('Won');
							},
						}),
				},
				{
					label: 'Lost',
					value: 'Lost',
					component: () =>
						h(DropdownItem, {
							label: 'Lost',
							onClick: () => {
								this._updateStatus('Lost');
							},
						}),
				},
				{
					label: 'Junk',
					value: 'Junk',
					component: () =>
						h(DropdownItem, {
							label: 'Junk',
							onClick: () => {
								this._updateStatus('Junk');
							},
						}),
				},
				{
					label: 'Passed to Other Partner',
					value: 'Passed to Other Partner',
					component: () =>
						h(DropdownItem, {
							label: 'Passed to Other Partner',
							onClick: () => {
								this._updateStatus('Passed to Other Partner');
							},
						}),
				},
			];
		},
		themeMap() {
			return {
				Open: 'blue',
				'In Process': 'orange',
				Won: 'green',
				Lost: 'red',
				Junk: 'gray',
				'Passed to Other Partner': 'gray',
			};
		},
	},
	methods: {
		_updateStatus(status) {
			if (status === this.lead.status) return;
			if (status === 'In Process') {
				this.showUpdateEngagementStageDialog = true;
			} else if (status === 'Won') {
				this.showUpdateWonDialog = true;
			} else if (status === 'Lost') {
				this.showUpdateLostDialog = true;
			} else {
				this.$resources.updateStatus.submit({ status: status });
			}
		},
	},
};
</script>
