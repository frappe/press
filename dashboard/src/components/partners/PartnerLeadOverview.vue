<template>
	<div>
		<div
			v-if="
				lead && (lead.partner_team == $team.doc.name || $team.doc.is_desk_user)
			"
		>
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
				<div class="rounded-lg text-base text-gray-900 border">
					<div class="p-4">
						<div class="flex items-center justify-between pb-2">
							<div class="font-semibold text-xl">Company Information</div>
							<Button
								variant="subtle"
								@click="
									() => {
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
									<div
										v-if="item.label === 'Plan Type' && item.value"
										class="py-1"
									>
										<Badge
											variant="outline"
											theme="blue"
											size="lg"
											label="Starter Pack"
										/>
									</div>
									<div v-else class="text-lg font-medium py-2">
										{{ item.value || '-' }}
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="rounded-lg text-base text-gray-900 border">
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
										{{ item.value || '-' }}
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="rounded-lg text-base text-gray-900 border">
					<div class="p-4">
						<div class="flex items-center justify-between pb-2">
							<div class="font-semibold text-xl">Deal Info</div>
						</div>
						<div class="my-1 h-px bg-gray-100" />
						<div class="pt-2">
							<div class="grid grid-cols-2 gap-4">
								<div v-for="item in deal_info" class="flex-1">
									<div class="text-sm text-gray-600">
										{{ item.label }}
									</div>
									<div v-if="item.label === 'Probability'" class="py-1">
										<Badge
											variant="outline"
											:theme="probabilityTheme[item.value]"
											size="lg"
											:label="item.value"
										/>
									</div>
									<div v-else class="text-lg font-medium py-2">
										{{ item.value || '-' }}
									</div>
								</div>
							</div>
							<!-- <div class="my-1 h-px bg-gray-100" /> -->
							<div class="pt-2">
								<div class="text-sm text-gray-600">Requirement</div>
								<div class="text-base leading-6 font-normal py-2">
									<div v-html="lead?.requirement"></div>
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
				:status="status"
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
		<div
			v-else
			class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
		>
			<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
			<ErrorMessage message="You aren't permitted to view the this page" />
		</div>
	</div>
</template>
<script>
import { Badge } from 'frappe-ui';
import LeadDetailsDialog from './LeadDetailsDialog.vue';
import UpdateWonDialog from './UpdateWonDialog.vue';
import { h } from 'vue';
import DropdownItem from '../billing/DropdownItem.vue';
import UpdateEngagementStageDialog from './UpdateEngagementStageDialog.vue';
import UpdateLostDialog from './UpdateLostDialog.vue';
import { toast } from 'vue-sonner';
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
			errorMessage: null,
			status: null,
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
				onError: (e) => {
					this.errorMessage = e.messages[0] || 'Failed to update status';
					toast.error(this.errorMessage);
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
				{ label: 'Industry', value: this.lead?.domain },
				{
					label: 'Conversion Date',
					value: this.lead?.conversion_date,
					condition: this.lead?.status === 'Won',
				},
				{
					label: 'Lost Reason',
					value: this.lead?.lost_reason,
					condition: this.lead?.status === 'Lost',
				},
				{
					label: 'Other Reason',
					value: this.lead?.lost_reason_specify,
					condition:
						this.lead?.status === 'Lost' && this.lead?.lost_reason === 'Other',
				},
				{
					label: 'Partner',
					value: this.lead?.company_name,
					condition: this.$team.doc.is_desk_user,
				},
				{
					label: 'Lead Owner',
					value: this.lead?.lead_owner,
				},
				{
					label: 'Plan Type',
					value: this.lead?.is_starter_pack,
					condition: this.lead?.is_starter_pack !== undefined,
				},
			].filter((d) => d.condition ?? true);
		},
		contact_info() {
			return [
				{
					label: 'Full Name',
					value: this.lead?.full_name || this.lead?.lead_name,
				},
				{ label: 'Email', value: this.lead?.email },
				{ label: 'Country', value: this.lead?.country },
				{ label: 'State', value: this.lead?.state },
				{ label: 'Territory', value: this.lead?.territory },
				{ label: 'Contact', value: this.lead?.contact_no },
			];
		},
		deal_info() {
			return [
				{
					label: 'Plan Proposed',
					value: this.lead?.plan_proposed,
					condition: ['Won', 'In Process'].includes(this.lead?.status),
				},
				{ label: 'Probability', value: this.lead?.probability },
				{
					label: 'Expected Close Date',
					value: this.lead?.estimated_closure_date,
					condition: this.lead?.status === 'In Process',
				},
				{
					label: 'Hosting',
					value: this.lead?.hosting,
					condition: this.lead?.status === 'Won',
				},
				{
					label: 'Site URL',
					value: this.lead?.site_url,
					condition: this.lead?.status === 'Won',
				},
			].filter((d) => d.condition ?? true);
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
					label: 'Qualification',
					value: 'Qualification',
					component: () =>
						h(DropdownItem, {
							label: 'Qualification',
							onClick: () => {
								this._updateStatus('Qualification');
							},
						}),
				},
				{
					label: 'Demo/Making',
					value: 'Demo/Making',
					component: () =>
						h(DropdownItem, {
							label: 'Demo/Making',
							onClick: () => {
								this._updateStatus('Demo/Making');
							},
						}),
				},
				{
					label: 'Follow Up',
					value: 'Follow Up',
					component: () =>
						h(DropdownItem, {
							label: 'Follow Up',
							onClick: () => {
								this._updateStatus('Follow Up');
							},
						}),
				},
				{
					label: 'Proposal/Quotation',
					value: 'Proposal/Quotation',
					component: () =>
						h(DropdownItem, {
							label: 'Proposal/Quotation',
							onClick: () => {
								this._updateStatus('Proposal/Quotation');
							},
						}),
				},
				{
					label: 'Negotiation',
					value: 'Negotiation',
					component: () =>
						h(DropdownItem, {
							label: 'Negotiation',
							onClick: () => {
								this._updateStatus('Negotiation');
							},
						}),
				},
				{
					label: 'Ready to Close',
					value: 'Ready to Close',
					component: () =>
						h(DropdownItem, {
							label: 'Ready to Close',
							onClick: () => {
								this._updateStatus('Ready to Close');
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
					label: 'Closed',
					value: 'Closed',
					component: () =>
						h(DropdownItem, {
							label: 'Closed',
							onClick: () => {
								this._updateStatus('Closed');
							},
						}),
				},
			];
		},
		themeMap() {
			return {
				Open: 'blue',
				Qualification: 'blue',
				'Demo/Making': 'orange',
				'Follow Up': 'blue',
				'Proposal/Quotation': 'orange',
				Negotiation: 'orange',
				'Ready to Close': 'blue',
				Won: 'green',
				Lost: 'red',
				Junk: 'gray',
				Closed: 'gray',
			};
		},
		probabilityTheme() {
			return {
				Hot: 'red',
				Warm: 'orange',
				Cold: 'blue',
			};
		},
	},
	methods: {
		_updateStatus(status) {
			if (status === this.lead.status && status !== 'In Process') return;
			if (['Ready to Close', 'Proposal/Quotation'].includes(status)) {
				this.status = status;
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
