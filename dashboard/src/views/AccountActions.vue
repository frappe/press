<template>
	<Card title="Account Actions" subtitle="Actions available for your account">
		<!-- TODO: Edit Events -->
		<ListItem
			title="Become Marketplace Developer"
			subtitle="Become a marketplace app publisher"
			v-if="showBecomePublisherButton && !isSaasLogin"
		>
			<template #actions>
				<Button @click="confirmPublisherAccount()">
					<span>Become a Publisher</span>
				</Button>
			</template>
		</ListItem>
		<ListItem
			v-if="$account.team.enabled"
			title="Disable Account"
			subtitle="Disable your account and stop billing"
		>
			<template #actions>
				<Button @click="showDisableAccountDialog = true">
					<span class="text-red-600">Disable</span>
				</Button>
			</template>
		</ListItem>
		<ListItem
		v-if="!$account.team.enabled"
			title="Enable Account"
			subtitle="Enable your account and resume billing"
		>
			<template #actions>
				<Button @click="showEnableAccountDialog = true">
					Enable
				</Button>
			</template>
		</ListItem>
		<Dialog title="Disable Account" v-model="showDisableAccountDialog">
			<p class="text-base prose">
				By confirming this action:
				<ul>
					<li>Your account will be disabled</li>
					<li>Your active sites will be suspended immediately and will be deleted after a week.</li>
					<li>Your account billing will be stopped</li>
				</ul>
				You can enable your account later anytime. Do you want to
				continue?
			</p>
			<ErrorMessage class="mt-2" :error="$resources.disableAccount.error" />

			<template v-slot:actions>
				<Button @click="showDisableAccountDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					type="danger"
					@click="$resources.disableAccount.submit()"
					:loading="$resources.disableAccount.loading"
				>
					Disable Account
				</Button>
			</template>
		</Dialog>
		<Dialog title="Enable Account" v-model="showEnableAccountDialog">
			<p class="text-base prose">
				By confirming this action:
				<ul>
					<li>Your account will be enabled</li>
					<li>Your suspended sites will become active</li>
					<li>Your account billing will be resumed</li>
				</ul>
				Do you want to continue?
			</p>
			<ErrorMessage class="mt-2" :error="$resources.enableAccount.error" />

			<template v-slot:actions>
				<Button @click="showEnableAccountDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					type="primary"
					@click="$resources.enableAccount.submit()"
					:loading="$resources.enableAccount.loading"
				>
					Enable Account
				</Button>
			</template>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'AccountActions',
	resources: {
		disableAccount: {
			method: 'press.api.account.disable_account',
			onSuccess() {
				this.$notify({
					title: 'Account disabled',
					message: 'Your account was disabled successfully',
					icon: 'check',
					color: 'green'
				});
				this.$account.fetchAccount();
				this.showDisableAccountDialog = false;
			}
		},
		enableAccount: {
			method: 'press.api.account.enable_account',
			onSuccess() {
				this.$notify({
					title: 'Account enabled',
					message: 'Your account was enabled successfully',
					icon: 'check',
					color: 'green'
				});
				this.$account.fetchAccount();
				this.showEnableAccountDialog = false;
			}
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
					this.$router.push('/marketplace');
				}
			};
		}
	},
	computed: {
		isSaasLogin() {
			return localStorage.getItem("saas_login");
		}
	},
	data() {
		return {
			showDisableAccountDialog: false,
			showEnableAccountDialog: false,
			showBecomePublisherButton: false
		};
	},
	methods: {
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
