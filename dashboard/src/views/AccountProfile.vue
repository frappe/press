<template>
	<div>
		<Section title="Profile" description="Your profile information">
			<div class="w-full mt-6 sm:w-1/2">
				<div>
					<span class="block mb-2 text-sm leading-4 text-gray-700">Photo</span>
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
					<Input
						label="First Name"
						type="text"
						v-model="account.user.first_name"
					/>
					<Input
						label="Last Name"
						type="text"
						v-model="account.user.last_name"
					/>
				</div>
				<Input
					class="mt-4"
					label="Email Address"
					type="email"
					v-model="account.user.email"
				/>
			</div>
		</Section>
		<div class="py-4">
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
			let { first_name, last_name, email } = this.$account.user;
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
