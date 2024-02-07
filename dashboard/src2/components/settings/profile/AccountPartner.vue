<template>
	<Card
		v-if="$team.doc.erpnext_partner"
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
				:title="partner_billing_name"
				:subtitle="$team.doc.partner_email"
				v-else="$team.doc.partner_email"
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
				<p class="text-p-base pb-3">
					Enter partner code provided by your Partner
				</p>
				<FormControl
					placeholder="e.g. rGjw3hJ81b"
					v-model="code"
					@input="referralCodeChange"
				/>
				<ErrorMessage class="mt-2" :message="errorMessage" />
			</template>
		</Dialog>
	</Card>
</template>
<script>
import { Card, FormControl } from 'frappe-ui';
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
				url: 'press.api.account.add_partner',
				params: {
					referral_code: this.code
				},
				onSuccess(res) {
					this.showAddPartnerCodeDialog = false;
					this.$team.doc.partner_referral_code = res.partner_referral_code;
					toast.success('Approval Request has been sent to Partner');
				},
				onError(res) {
					this.errorMessage = 'Partner with code not found';
				}
			};
		},
		partnerName() {
			return {
				url: 'press.api.account.get_partner_name',
				auto: true,
				params: {
					partner_email: this.$team.doc.partner_email
				}
			};
		}
	},
	methods: {
		async referralCodeChange(e) {
			let code = e.target.value;
			this.partnerExists = false;

			let result = await this.$call('press.api.account.validate_partner_code', {
				code: code
			});

			let [isValidCode, partnerName] = result;

			if (isValidCode) {
				this.partnerExists = true;
				this.referralCode = code;
				this.partner = partnerName;
			} else {
				this.errorMessage = `${code} is Invalid Referral Code`;
			}
		}
	},
	computed: {
		partner_billing_name() {
			return this.$resources.partnerName.data;
		}
	}
};
</script>
