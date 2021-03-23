<template>
	<Card title="Team Actions" subtitle="Actions available for your team">
		<div class="flex items-center justify-between py-3">
			<h3 class="text-base font-medium text-gray-900">
				Account Deletion
			</h3>
			<div class="ml-auto">
				<Button @click="showTeamDeletionDialog = true">
					<span class="text-red-600">Delete</span>
				</Button>
			</div>
		</div>
		<Dialog title="Delete Team" v-model="showTeamDeletionDialog">
			<p class="text-base">
				With this, all of your and your team members' personal data will be
				deleted. By proceeding with this, you will delete the accounts of the
				members in your team, if they aren't a part of any other team.
			</p>
			<ErrorMessage class="mt-2" :error="$resources.deleteTeam.error" />

			<template slot="actions">
				<Button class="ml-3" @click="showTeamDeletionDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					type="danger"
					@click="$resources.deleteTeam.submit()"
					:loading="$resources.deleteTeam.loading"
				>
					Delete Account
				</Button>
			</template>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'AccountActions',
	resources: {
		deleteTeam() {
			return {
				method: 'press.api.account.request_team_deletion',
				onSuccess() {
					this.notifySuccess();
					this.showTeamDeletionDialog = false;
				},
				onError() {
					this.notifyFailure();
				}
			};
		}
	},
	data() {
		return {
			showTeamDeletionDialog: false
		};
	},
	methods: {
		notifySuccess() {
			this.$notify({
				title: 'Deletion request recorded',
				message: 'Verify request from email to start the process',
				icon: 'check',
				color: 'green'
			});
		},
		notifyFailure() {
			this.$notify({
				title: 'Deletion request not recorded',
				message: this.$resources.deleteTeam.error == 'Internal Server Error' ? 'An error occured. Please contact Support' : '',
				icon: 'check',
				color: 'red'
			});
		}
	}
};
</script>
