<template>
	<Card
		title="Frappe Partner"
		subtitle="Frappe Partner associated with your account"
	>
		<div>
			<ListItem
				:title="$account.partner_billing_name"
				:subtitle="$account.partner_email"
				v-if="$account.partner_email && !$account.team.erpnext_partner"
			>
			</ListItem>
		</div>
		<template #actions>
			<Button @click="showSelectPartnerDialog = true"> Change Partner </Button>
		</template>
		<Dialog
			:options="{ title: 'Add Partner' }"
			v-model="showSelectPartnerDialog"
		>
			<template v-slot:body-content>
				<Input
					label="Select Frappe Partner"
					type="select"
					:options="partners"
					v-model="selectedPartner"
				/>
				<ErrorMessage class="mt-2" :message="$resources.selectPartner.error" />
			</template>
			<template #actions>
				<Button
					appearance="primary"
					:loading="$resources.selectPartner.loading"
					loadingText="Saving..."
					@click="$resources.selectPartner.submit()"
				>
					Add partner
				</Button>
			</template>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'AccountPartner',
	data() {
		return {
			showSelectPartnerDialog: false,
			partners: [],
			selectedPartner: null,
			partner_email: null
		};
	},
	resources: {
		selectPartner() {
			return {
				method: 'press.api.account.add_partner',
				params: {
					partner_email: this.selectedPartner
				},
				onSuccess(res) {
					this.showSelectPartnerDialog = false;
				}
			};
		},
		getPartners() {
			return {
				method: 'press.api.account.get_frappe_partners',
				auto: true,
				cache: ['partners'],
				onSuccess(data) {
					this.partners = data.map(d => {
						return {
							label: d.billing_name,
							value: d.partner_email
						};
					});
				}
			};
		}
	}
};
</script>
