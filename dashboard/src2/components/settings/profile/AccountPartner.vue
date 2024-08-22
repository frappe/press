<template>
	<Card
		v-if="!$team.doc.erpnext_partner"
		title="Frappe Partner"
		subtitle="Frappe Partner associated with your account"
	>
		<template #actions>
			<Button
				v-if="!$team.doc.partner_email"
				icon-left="edit"
				@click="showAddPartnerCodeDialog = true"
			>
				Add Partner Code
			</Button>
		</template>
		<div class="py-4">
			<span
				class="text-base font-medium text-gray-700"
				v-if="!$team.doc.partner_email"
			>
				Have a Frappe Partner Referral Code? Click on
				<strong>Add Partner Code</strong> to link with your Partner team.
			</span>
			<ListItem
				v-else
				:title="partner_billing_name"
				:subtitle="$team.doc.partner_email"
			/>
		</div>
		<Dialog
			:options="{
				title: 'Partner Code',
				actions: [
					{
						label: 'Submit',
						variant: 'solid',
						onClick: () => $resources.addPartnerCode.submit()
					}
				]
			}"
			v-model="showAddPartnerCodeDialog"
		>
			<template v-slot:body-content>
				<p class="pb-3 text-p-base">
					Enter partner code provided by your Partner
				</p>
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
		FormControl
	},
	data() {
		return {
			showAddPartnerCodeDialog: false,
			code: '',
			partnerExists: false,
			partner: '',
			errorMessage: ''
		};
	},
	resources: {
		addPartnerCode() {
			return {
				url: 'press.api.partner.add_partner',
				params: {
					referral_code: this.code
				},
				onSuccess(res) {
					this.showAddPartnerCodeDialog = false;
					if (res) {
						this.$team.doc.partner_referral_code = res.partner_referral_code;
					}
					toast.success('Approval Request has been sent to Partner');
				},
				onError(res) {
					if (res) {
						throw new DashboardError(res.message);
					} else {
						throw new DashboardError('Error while adding partner');
					}
				}
			};
		},
		partnerName() {
			return {
				url: 'press.api.partner.get_partner_name',
				auto: true,
				params: {
					partner_email: this.$team.doc.partner_email
				}
			};
		}
	},
	methods: {
		referralCodeChange: debounce(async function (e) {
			let code = e.target.value;
			this.partnerExists = false;

			let result = await frappeRequest({
				url: 'press.api.partner.validate_partner_code',
				params: { code: code }
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
		}, 500)
	},
	computed: {
		partner_billing_name() {
			return this.$resources.partnerName.data;
		}
	}
};
</script>
