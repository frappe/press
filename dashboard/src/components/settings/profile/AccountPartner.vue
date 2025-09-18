<template>
	<Card
		v-if="!$team.doc?.erpnext_partner"
		title="Frappe Partner"
		subtitle="Frappe Partner associated with your account"
		class="mx-auto max-w-3xl"
	>
		<template #actions>
			<Button
				v-if="!$team.doc?.partner_email"
				icon-left="edit"
				@click="showAddPartnerCodeDialog = true"
			>
				Add Partner Code
			</Button>
			<Button
				v-else
				icon-left="trash-2"
				@click="showRemovePartnerDialog = true"
			>
				Unlink Partner
			</Button>
		</template>
		<div class="py-4">
			<span
				class="text-base font-medium text-gray-700"
				v-if="!$team.doc?.partner_email"
			>
				Have a Frappe Partner Referral Code? Click on
				<strong>Add Partner Code</strong> to link with your Partner team.
			</span>
			<ListItem
				v-else
				:title="partner_billing_name"
				:subtitle="$team.doc?.partner_email"
			/>
		</div>
		<Dialog
			:options="{
				title: 'Link Partner Account',
				actions: [
					{
						label: 'Submit',
						variant: 'solid',
						onClick: () => $resources.addPartnerCode.submit(),
					},
				],
			}"
			v-model="showAddPartnerCodeDialog"
		>
			<template v-slot:body-content>
				<p class="pb-2 text-p-base">
					Enter the partner code provided by your Partner
				</p>
				<div class="rounded border border-gray-200 bg-gray-100 p-2 mb-4">
					<span class="text-sm leading-[1.5] text-gray-700">
						<strong>Note</strong>: After linking with Partner, following details
						shall be shared with your partner team:
						<br />
						<li>Billing name</li>
						<li>Monthly billing amount</li>
					</span>
				</div>
				<FormControl
					placeholder="e.g. rGjw3hJ81b"
					v-model="code"
					@input="referralCodeChange"
				/>
				<div class="mt-1">
					<div v-if="partnerExists" class="text-sm text-green-600" role="alert">
						Referral Code {{ code }} belongs to {{ partner }}
					</div>
				</div>
			</template>
		</Dialog>

		<Dialog
			v-model="showRemovePartnerDialog"
			:options="{
				title: 'Remove Partner',
				actions: [
					{
						label: 'Remove',
						variant: 'solid',
						theme: 'red',
						onClick: () => {
							$resources.removePartner.submit();
						},
					},
				],
			}"
		>
			<template v-slot:body-content>
				<div class="text-p-base pb-2">
					This will remove the Partner associated with your account. Are you
					sure you want to remove the Partner? <br /><br />
					<div class="text-gray-800 bg-gray-200 p-2 rounded-md">
						Your partner will no longer have access to your sites and servers
						and will be removed as team member from your team.
					</div>
				</div>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import { Card, FormControl, frappeRequest, debounce } from 'frappe-ui';
import { DashboardError } from '../../../utils/error';
import { toast } from 'vue-sonner';
export default {
	name: 'AccountPartner',
	components: {
		Card,
		FormControl,
	},
	data() {
		return {
			showAddPartnerCodeDialog: false,
			showRemovePartnerDialog: false,
			code: '',
			partnerExists: false,
			partner: '',
			errorMessage: '',
		};
	},
	resources: {
		addPartnerCode() {
			return {
				url: 'press.api.partner.add_partner',
				params: {
					referral_code: this.code,
				},
				onSuccess(data) {
					this.showAddPartnerCodeDialog = false;
					if (data === 'Request already sent') {
						toast.error('Approval Request has already been sent to Partner');
					} else {
						toast.success(
							'Approval Request has been sent to Partner. Please wait for Partner to accept the request',
						);
					}
				},
				onError() {
					throw new DashboardError('Failed to add Partner Code');
				},
			};
		},
		partnerName() {
			return {
				url: 'press.api.partner.get_partner_name',
				auto: true,
				params: {
					partner_email: this.$team.doc?.partner_email,
				},
			};
		},
		removePartner() {
			return {
				url: 'press.api.partner.remove_partner',
				onSuccess() {
					this.showRemovePartnerDialog = false;
					toast.success('Partner removed successfully');
				},
				onError() {
					throw new DashboardError('Failed to remove Partner');
				},
			};
		},
	},
	methods: {
		referralCodeChange: debounce(async function (e) {
			let code = e.target.value;
			this.partnerExists = false;

			let result = await frappeRequest({
				url: 'press.api.partner.validate_partner_code',
				params: { code: code },
			});

			let isValidCode = result[0];
			let partnerName = result[1];

			if (isValidCode) {
				this.partnerExists = true;
				this.referralCode = code;
				this.partner = partnerName;
			} else {
				this.errorMessage = `${code} is Invalid Referral Code`;
			}
		}, 500),
	},
	computed: {
		partner_billing_name() {
			return this.$resources.partnerName.data;
		},
	},
};
</script>
