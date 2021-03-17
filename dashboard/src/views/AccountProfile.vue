<template>
	<Card title="Profile" subtitle="Your profile information">
		<div class="flex items-center">
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
								class="absolute inset-0 grid w-full text-xs font-semibold text-white bg-black rounded-full opacity-0 focus:outline-none focus:opacity-50 hover:opacity-50 place-items-center"
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
		<div class="pt-2">
			<Button @click="showTeamDeletionDialog = true">
				<span class="text-red-600">Delete Account</span>
			</Button>
		</div>
		<Dialog title="Delete Team" v-model="showTeamDeletionDialog">
			<div>
				With this, all of your and your team members' personal data will be deleted.
			By proceeding with this, you will delete the accounts of the members in your team, if they aren't a part of any other team.
			</div>
			<Button
				class="ml-3"
				type="danger"
				@click="$resources.deleteTeam.submit()"
				:loading="$resources.deleteTeam.loading"
			>
				Delete Account
			</Button>
		</Dialog>
		<Dialog title="Update Profile Information" v-model="showProfileEditDialog">
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
			<ErrorMessage class="mt-4" :error="$resources.updateProfile.error" />

			<template #actions>
				<div class="space-x-2">
					<Button @click="showProfileEditDialog = false">Cancel</Button>
					<Button
						type="primary"
						:loading="$resources.updateProfile.loading"
						loadingText="Saving..."
						@click="$resources.updateProfile.submit()"
					>
						Save changes
					</Button>
				</div>
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
		deleteTeam() {
			return {
				method: 'press.api.account.request_team_deletion',
				onSuccess() {
					this.notifySuccess();
				}
			}
		}
	},
	data() {
		return {
			showProfileEditDialog: false,
			showTeamDeletionDialog: false
		};
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
		}
	}
};
</script>
