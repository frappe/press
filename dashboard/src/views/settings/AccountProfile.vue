<template>
	<Card title="Profile" subtitle="Your profile information">
		<div class="flex items-center border-b pb-5">
			<div class="relative">
				<Avatar
					size="lg"
					:label="$account.user.first_name"
					:imageURL="$account.user.user_image"
				/>
				<FileUploader
					@success="onProfilePhotoChange"
					fileTypes="image/*"
					:upload-args="{
						doctype: 'User',
						docname: $account.user.name,
						method: 'press.api.account.update_profile_picture'
					}"
				>
					<template v-slot="{ openFileSelector, uploading, progress, error }">
						<div class="ml-4">
							<button
								@click="openFileSelector()"
								class="absolute inset-0 grid w-full place-items-center rounded-full bg-black text-xs font-semibold text-white opacity-0 hover:opacity-50 focus:opacity-50 focus:outline-none"
								:class="{ 'opacity-50': uploading }"
							>
								<span v-if="uploading">{{ progress }}%</span>
								<span v-else>Edit</span>
							</button>
						</div>
					</template>
				</FileUploader>
			</div>
			<div class="ml-4">
				<h3 class="text-lg font-semibold">
					{{ $account.user.first_name }} {{ $account.user.last_name }}
				</h3>
				<p class="text-sm text-gray-600">{{ $account.user.email }}</p>
			</div>
			<div class="ml-auto">
				<Button icon-left="edit" @click="showProfileEditDialog = true">
					Edit
				</Button>
			</div>
		</div>
		<div>
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
				:title="teamEnabled ? 'Disable Account' : 'Enable Account'"
				:subtitle="teamEnabled ? 'Disable your account and stop billing': 'Enable your account and resume billing'"
			>
				<template #actions>
					<Button @click="() => {
						if (teamEnabled) {
							showDisableAccountDialog = true
						} else {
							showEnableAccountDialog = true
						}
					}">
						<span :class="{ 'text-red-600': teamEnabled }">{{ teamEnabled ? 'Disable' : 'Enable' }}</span>
					</Button>
				</template>
			</ListItem>
		</div>
		<Dialog
			:options="{ title: 'Update Profile Information' }"
			v-model="showProfileEditDialog"
		>
			<template v-slot:body-content>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<Input
						label="First Name"
						type="text"
						v-model="$account.user.first_name"
					/>
					<Input
						label="Last Name"
						type="text"
						v-model="$account.user.last_name"
					/>
				</div>
				<ErrorMessage class="mt-4" :message="$resources.updateProfile.error" />
			</template>

			<template #actions>
				<div class="space-x-2">
					<Button @click="showProfileEditDialog = false">Cancel</Button>
					<Button
						appearance="primary"
						:loading="$resources.updateProfile.loading"
						loadingText="Saving..."
						@click="$resources.updateProfile.submit()"
					>
						Save changes
					</Button>
				</div>
			</template>
		</Dialog>

		<Dialog :options="{title: 'Disable Account'}" v-model="showDisableAccountDialog">
			<template v-slot:body-content>
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
			<ErrorMessage class="mt-2" :message="$resources.disableAccount.error" />
			</template>

			<template v-slot:actions>
				<Button @click="showDisableAccountDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					appearance="danger"
					@click="$resources.disableAccount.submit()"
					:loading="$resources.disableAccount.loading"
				>
					Disable Account
				</Button>
			</template>
		</Dialog>

		<Dialog :options="{title: 'Enable Account'}" v-model="showEnableAccountDialog">
			<template v-slot:body-content>
				<p class="text-base prose">
					By confirming this action:
					<ul>
						<li>Your account will be enabled</li>
						<li>Your suspended sites will become active</li>
						<li>Your account billing will be resumed</li>
					</ul>
					Do you want to continue?
				</p>
				<ErrorMessage class="mt-2" :message="$resources.enableAccount.error" />
			</template>

			<template v-slot:actions>
				<Button @click="showEnableAccountDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					appearance="primary"
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
import FileUploader from '@/components/FileUploader.vue';
export default {
	name: 'AccountProfile',
	components: {
		FileUploader
	},
	data() {
		return {
			showProfileEditDialog: false,
			showEnableAccountDialog: false,
			showDisableAccountDialog: false,
			showBecomePublisherButton: false
		};
	},
	computed: {
		teamEnabled() {
			return $account.team.enabled;
		}
	},
	resources: {
		updateProfile() {
			let { first_name, last_name, email } = this.$account.user;
			return {
				method: 'press.api.account.update_profile',
				params: {
					first_name,
					last_name,
					email
				},
				onSuccess() {
					this.showProfileEditDialog = false;
					this.notifySuccess();
				}
			};
		},
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
	methods: {
		onProfilePhotoChange() {
			this.$account.fetchAccount();
			this.notifySuccess();
		},
		notifySuccess() {
			this.$notify({
				title: 'Updated profile information',
				icon: 'check',
				color: 'green'
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
