<template>
	<div>
		<Card
			v-if="profileData && profileData.profile_created"
			title="Publisher Profile"
			subtitle="Visible on the marketplace website"
		>
			<div class="divide-y-2">
				<ListItem
					title="Display Name"
					:description="displayName || 'Not Set'"
				/>
				<ListItem
					title="Contact Email"
					:description="contactEmail || 'Not Set'"
				/>
				<ListItem title="Website" :description="website || 'Not Set'" />
			</div>

			<template #actions>
				<Button icon-left="edit" @click="showEditProfileDialog = true"
					>Edit</Button
				>
			</template>
		</Card>

		<FrappeUIDialog
			:options="{ title: 'Edit Publisher Profile' }"
			v-model="showEditProfileDialog"
		>
			<template v-slot:body-content>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<Input label="Display Name" type="text" v-model="displayName" />
					<Input label="Contact Email" type="email" v-model="contactEmail" />
					<Input label="Website" type="text" v-model="website" />
				</div>

				<ErrorMessage
					class="mt-4"
					:error="$resources.updatePublisherProfile.error"
				/>
			</template>

			<template #actions>
				<div class="space-x-2">
					<Button @click="showEditProfileDialog = false">Cancel</Button>
					<Button
						appearance="primary"
						:loading="$resources.updatePublisherProfile.loading"
						loadingText="Saving..."
						@click="$resources.updatePublisherProfile.submit()"
					>
						Save
					</Button>
				</div>
			</template>
		</FrappeUIDialog>
	</div>
</template>

<script>
export default {
	props: ['profileData'],
	emits: ['profileUpdated'],
	data() {
		return {
			showEditProfileDialog: false,
			displayName: '',
			contactEmail: '',
			website: ''
		};
	},
	resources: {
		updatePublisherProfile() {
			return {
				method: 'press.api.marketplace.update_publisher_profile',
				params: {
					profile_data: {
						display_name: this.displayName,
						contact_email: this.contactEmail,
						website: this.website
					}
				},
				validate() {
					if (!this.displayName) {
						return 'Display Name is required.';
					}
				},
				onSuccess() {
					this.showEditProfileDialog = false;
					this.$emit('profile_updated');
				}
			};
		}
	},
	watch: {
		profileData(data) {
			if (data && data.profile_created) {
				this.displayName = data.profile_info.display_name;
				this.contactEmail = data.profile_info.contact_email;
				this.website = data.profile_info.website;
			}
		}
	}
};
</script>
