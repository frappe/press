<template>
	<Card title="Partner Request Status" v-if="!$account.team.erpnext_partner">
		<template #actions>
			<Badge
				:variant="'subtle'"
				:theme="this.partnerRequestStatus === 'Pending' ? 'orange' : 'green'"
				size="lg"
				:label="this.partnerRequestStatus"
			/>
		</template>
		<div class="flex items-center">
			<div v-if="$account.team.partnership_date">
				<span class="text-base">
					Customer Partnership Start Date:
					<span class="font-semibold">{{
						$date($account.team.partnership_date).toLocaleString({
							month: 'long',
							day: 'numeric',
							year: 'numeric'
						})
					}}</span>
				</span>
			</div>
			<div v-else>
				<span class="text-base">
					To set Customer Partnership Start Date, click on Edit button</span
				>
			</div>
			<div class="ml-auto">
				<Button icon-left="edit" @click="showDateEditDialog = true">
					Edit
				</Button>
			</div>
		</div>

		<Dialog
			:options="{
				title: 'Update Customer Partnership Start Date',
				actions: [
					{
						variant: 'solid',
						label: 'Save Changes',
						onClick: () => $resources.updatePartnershipDate.submit()
					}
				]
			}"
			v-model="showDateEditDialog"
		>
			<template v-slot:body-content>
				<FormControl
					label="Enter Partnership Start Date"
					type="date"
					v-model="partnerDate"
					description="This date will be used to calculate your partner's target achievement."
				/>
				<ErrorMessage
					class="mt-2"
					:message="$resources.updatePartnershipDate.error"
				/>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import { DateTime } from 'luxon';

export default {
	name: 'PartnerRequestStatus',
	data() {
		return {
			partnerRequestStatus: null,
			partnershipDate: null,
			showDateEditDialog: false,
			partnerDate: null
		};
	},
	resources: {
		getStatus: {
			url: 'press.api.account.get_partner_request_status',
			params: {
				team: $account.team.name
			},
			onSuccess(data) {
				console.log(data);
				this.partnerRequestStatus = data;
			},
			auto: true
		},
		updatePartnershipDate() {
			return {
				url: 'press.api.account.update_partnership_date',
				params: {
					team: $account.team.name,
					partnership_date: this.partnerDate || this.today
				},
				onSuccess() {
					this.showDateEditDialog = false;
				}
			};
		}
	},
	computed: {
		today() {
			return DateTime.local().toISODate();
		}
	}
};
</script>
