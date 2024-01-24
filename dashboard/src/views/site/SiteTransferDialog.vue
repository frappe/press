<template>
	<Dialog
		:options="{
			title: 'Transfer Site to Team',
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					onClick: () =>
						$resources.transferSite.submit({
							team_mail_id: emailOfTransferTeam,
							name: site?.name,
							reason
						})
				}
			]
		}"
		v-model="show"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					label="Enter email of the team for transfer of site ownership"
					v-model="emailOfTransferTeam"
				/>
				<FormControl
					label="Reason for transfer"
					v-model="reason"
					type="textarea"
				/>
				<ErrorMessage :message="$resources.transferSite.error" />
			</div>
		</template>
	</Dialog>
</template>

<script>
import { notify } from '@/utils/toast';

export default {
	name: 'SiteTransferDialog',
	props: ['site', 'modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			reason: '',
			emailOfTransferTeam: ''
		};
	},
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	},
	resources: {
		transferSite() {
			return {
				url: 'press.api.site.send_change_team_request',
				validate() {
					if (!this.emailOfTransferTeam) {
						return 'Please enter email of the team for transfer of site ownership';
					} else if (!this.reason) {
						return 'Please enter reason for transfer';
					}
				},
				onSuccess() {
					this.reason = '';
					this.emailOfTransferTeam = '';
					this.$emit('update:modelValue', false);
					notify({
						title: 'Site transfer request sent',
						message: `The team ${this.emailOfTransferTeam} will receive a request to accept the site transfer.`,
						color: 'green',
						icon: 'check'
					});
				}
			};
		}
	}
};
</script>
