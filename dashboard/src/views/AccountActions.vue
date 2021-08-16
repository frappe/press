<template>
	<Card title="Team Actions" subtitle="Actions available for your team">
		<!-- TODO: Edit Events -->
		<ListItem
			title="Become Marketplace Developer"
			subtitle="Become a marketplace app publisher"
			v-if="showBecomePublisherButton"
		>
			<template #actions>
				<Button @click="confirmPublisherAccount()">
					<span>Become a Publisher</span>
				</Button>
			</template>
		</ListItem>
		<ListItem
			title="Delete Account"
			subtitle="Delete your account and personal data"
		>
			<template #actions>
				<Button @click="showTeamDeletionDialog = true">
					<span class="text-red-600">Delete</span>
				</Button>
			</template>
		</ListItem>
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
		},
		isDeveloperAccountAllowed() {
			return {
				method: 'press.api.marketplace.developer_toggle_allowed',
				auto: true,
				onSuccess(data) {
					if (data) {
						this.showBecomePublisherButton = true;
					}
				}
			};
		},
		becomePublisher() {
			return {
				method: 'press.api.marketplace.become_publisher',
				onSuccess() {
					this.$router.push('/developer');
				}
			};
		}
	},
	data() {
		return {
			showTeamDeletionDialog: false,
			showBecomePublisherButton: false
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
				message:
					this.$resources.deleteTeam.error == 'Internal Server Error'
						? 'An error occured. Please contact Support'
						: '',
				icon: 'check',
				color: 'red'
			});
		},
		confirmPublisherAccount() {
			this.$confirm({
				title: 'Become a marketplace app developer?',
				message:
					'You will be able to publish apps to our Marketplace upon confirmation.',
				actionLabel: 'Yes',
				actionType: 'primary',
				action: closeDialog => {
					this.$resources.becomePublisher.submit();
					closeDialog();
				}
			});
		}
	}
};
</script>
