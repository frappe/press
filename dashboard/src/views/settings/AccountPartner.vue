<template>
	<Card
		title="Frappe Partner"
		subtitle="Frappe Partner associated with your account"
		v-if="!$account.team.erpnext_partner"
	>
		<div>
			<ListItem
				:title="$account.partner_billing_name"
				:subtitle="$account.partner_email"
				v-if="$account.partner_email"
			>
			</ListItem>

			<div class="py-4">
				<h3 class="text-base text-gray-700" v-if="!$account.partner_email">
					Have a Frappe Partner Referral Code? Click on
					<strong>Add Partner Code</strong> to link with your Partner team.
				</h3>
			</div>
		</div>
		<template #actions>
			<Button
				@click="showPartnerReferralDialog = true"
				v-if="!$account.partner_email"
			>
				Add Partner Code
			</Button>
		</template>
		<Dialog
			:options="{ title: 'Partner Referral Code' }"
			v-model="showPartnerReferralDialog"
		>
			<template v-slot:body-content>
				<FormControl
					label="Enter Partner Referral Code"
					type="input"
					v-model="referralCode"
					placeholder="e.g. rGjw3hJ81b"
					@input="referralCodeChange"
				/>
				<ErrorMessage class="mt-2" :message="$resources.addPartner.error" />
				<div class="mt-1">
					<div v-if="partnerExists" class="text-sm text-green-600" role="alert">
						Referral Code {{ referralCode }} belongs to {{ partner }}
					</div>
					<ErrorMessage :message="errorMessage" />
				</div>
			</template>
			<template #actions>
				<Button
					variant="solid"
					:loading="$resources.addPartner.loading"
					loadingText="Saving..."
					@click="$resources.addPartner.submit()"
				>
					Add partner
				</Button>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import { notify } from '@/utils/toast';

export default {
	name: 'AccountPartner',
	data() {
		return {
			showPartnerReferralDialog: false,
			referralCode: null,
			partnerExists: false,
			errorMessage: null,
			partner: null
		};
	},
	resources: {
		addPartner() {
			return {
				url: 'press.api.account.add_partner',
				params: {
					referral_code: this.referralCode
				},
				onSuccess(res) {
					this.showPartnerReferralDialog = false;
					notify({
						title: 'Email sent to Partner',
						icon: 'check',
						color: 'green'
					});
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
				this.partnerExists = true;
			} else {
				this.errorMessage = `${code} is Invalid Referral Code`;
			}
		}
	}
};
</script>
