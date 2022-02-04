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
		}
	},
	data() {
		return {
			showProfileEditDialog: false
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
