<template>
	<div>
		<Section title="Profile" description="Your profile information">
			<div class="w-full mt-6 text-sm sm:w-1/2">
				<div>
					<span class="text-gray-800">Photo</span>
					<div class="flex items-center mt-2">
						<Avatar
							size="lg"
							:label="account.user.first_name"
							:imageURL="account.user.user_image"
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
							<template
								v-slot="{ openFileSelector, uploading, progress, error }"
							>
								<div class="ml-4">
									<Button :loading="uploading" @click="openFileSelector()">
										<span v-if="uploading">Uploading {{ progress }}%</span>
										<span v-else>Change</span>
									</Button>
									<ErrorMessage class="mt-1" :error="error" />
								</div>
							</template>
						</FileUploader>
					</div>
				</div>
				<div class="grid grid-cols-1 gap-4 mt-4 sm:grid-cols-2">
					<label class="block">
						<span class="text-gray-800">First Name</span>
						<input
							class="block w-full mt-2 shadow form-input"
							type="text"
							v-model="account.user.first_name"
						/>
					</label>
					<label class="block">
						<span class="text-gray-800">Last Name</span>
						<input
							class="block w-full mt-2 shadow form-input"
							type="text"
							v-model="account.user.last_name"
						/>
					</label>
				</div>
				<label class="block mt-4">
					<span class="text-gray-800">Email Address</span>
					<input
						class="block w-full mt-2 shadow form-input"
						type="text"
						v-model="account.user.email"
					/>
				</label>
			</div>
		</Section>
		<div class="py-4 mt-10 border-t">
			<ErrorMessage class="mb-4" :error="$resources.updateProfile.error" />
			<Button
				type="primary"
				:loading="$resources.updateProfile.loading"
				loadingText="Saving..."
				@click="$resources.updateProfile.submit()"
			>
				Save changes
			</Button>
		</div>
	</div>
</template>

<script>
import FileUploader from '@/components/FileUploader';

export default {
	name: 'AccountProfile',
	props: ['account'],
	components: {
		FileUploader
	},
	resources: {
		updateProfile() {
			let { first_name, last_name, email } = this.$store.account.user;
			return {
				method: 'press.api.account.update_profile',
				params: {
					first_name,
					last_name,
					email
				},
				onSuccess() {
					this.notifySuccess();
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
		}
	}
};
</script>
