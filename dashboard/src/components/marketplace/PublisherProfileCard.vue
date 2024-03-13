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
					:description="$sanitize(displayName || 'Not Set')"
				/>
				<ListItem
					title="Contact Email"
					:description="$sanitize(contactEmail || 'Not Set')"
				/>
				<ListItem
					title="Website"
					:description="$sanitize(website || 'Not Set')"
				/>
			</div>

			<template #actions>
				<Button icon-left="edit" @click="showEditProfileDialog = true"
					>Edit</Button
				>
			</template>
		</Card>

		<Dialog
			:options="{
				title: 'Edit Publisher Profile',
				actions: [
					{
						variant: 'solid',
						label: 'Save Changes',
						loading: $resources.updatePublisherProfile.loading,
						onClick: () => $resources.updatePublisherProfile.submit()
					}
				]
			}"
			v-model="showEditProfileDialog"
		>
			<template v-slot:body-content>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl label="Display Name" v-model="displayName" />
					<FormControl
						label="Contact Email"
						type="email"
						v-model="contactEmail"
					/>
					<FormControl label="Website" v-model="website" />
				</div>

				<ErrorMessage
					class="mt-4"
					:message="$resources.updatePublisherProfile.error"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script>
export default {
	props: ['profileData', 'showEditDialog'],
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
				url: 'press.api.marketplace.update_publisher_profile',
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
					this.$emit('profileUpdated');
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
		},
		showEditDialog(value) {
			if (value) {
				this.showEditProfileDialog = true;
			}
		}
	}
};
</script>
