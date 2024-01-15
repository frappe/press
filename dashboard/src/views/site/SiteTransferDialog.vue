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
							name: site?.name || site // site is siteName in d2
						})
				}
			]
		}"
		v-model="show"
	>
		<template #body-content>
			<FormControl
				label="Enter email of the team for transfer of site ownership"
				v-model="emailOfTransferTeam"
				required
			/>
			<ErrorMessage class="mt-3" :message="$resources.transferSite.error" />
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
				onSuccess() {
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
