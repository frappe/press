<template>
	<Card title="Team Actions" subtitle="Actions available for your team">
		<ListItem
			title="Become a Publisher"
			description="Register to publish your apps on Marketplace"
		>
			<template #actions>
				<Button
					@click="showVendorTerms = true"
					v-if="!$account.team.app_publisher"
				>
					<span class="text-sm">
						Sign Up
					</span>
				</Button>
				<Badge color="blue" v-else>Signed Up</Badge>
			</template>
		</ListItem>

		<ListItem
			title="Delete Account"
			description="Delete your account and personal data"
			v-if="$account.team"
		>
			<template #actions>
				<Button @click="showTeamDeletionDialog = true">
					<span class="text-red-600">Delete</span>
				</Button>
			</template>
		</ListItem>

		<Dialog title="Become a Publisher" v-model="showVendorTerms">
			<p class="text-base">
				By accepting this, you agree to have read and accepted all of
				<u
					><a href="/marketplace/terms" target="_blank"
						>Frappe Cloud Marketplace's terms and conditions.</a
					></u
				>
			</p>
			<ErrorMessage class="mt-2" :error="$resources.signupVendor.error" />

			<template slot="actions">
				<Button class="ml-3" @click="showVendorTerms = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					type="primary"
					@click="$resources.signupVendor.submit()"
					:loading="$resources.signupVendor.loading"
				>
					Accept Terms and Conditions
				</Button>
			</template>
		</Dialog>

		<Dialog title="Delete Team" v-model="showTeamDeletionDialog">
			<p class="text-base">
				By proceeding with this, you will delete the accounts of the members in
				your team.
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
import Badge from '../components/global/Badge.vue';
export default {
	components: { Badge },
	name: 'AccountActions',
	resources: {
		deleteTeam() {
			return {
				method: 'press.api.account.request_team_deletion',
				onSuccess() {
					this.notifySuccess({
						title: 'Deletion request recorded',
						message: 'Verify request from email to start the process'
					});
					this.showTeamDeletionDialog = false;
				},
				onError() {
					this.notifyFailure({
						title: 'Deletion request not recorded',
						message:
							this.$resources.deleteTeam.error == 'Internal Server Error'
								? 'An error occured. Please contact Support'
								: ''
					});
				}
			};
		},
		signupVendor() {
			return {
				method: 'press.api.marketplace.signup',
				onSuccess() {
					this.notifySuccess({
						title: 'Signed up as Publisher',
						message: 'Get started from your apps tab'
					});
					this.showVendorTerms = false;
					this.$account.fetchAccount();
				},
				onError() {
					this.notifyFailure({
						title: 'Something went wrong'
					});
				}
			};
		}
	},
	data() {
		return {
			showTeamDeletionDialog: false,
			showVendorTerms: false
		};
	},
	methods: {
		notifySuccess(kwargs) {
			this.$notify({
				...kwargs,
				icon: 'check',
				color: 'green'
			});
		},
		notifyFailure(kwargs) {
			this.$notify({
				...kwargs,
				icon: 'check',
				color: 'red'
			});
		}
	}
};
</script>
