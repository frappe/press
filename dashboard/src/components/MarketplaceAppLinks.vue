<template>
	<Card title="Links" subtitle="Will be shown in marketplace">
		<template #actions>
			<Button icon-left="edit" @click="showEditLinksDialog = true">Edit</Button>
		</template>
		<Dialog :options="{ title: 'Update Links' }" v-model="showEditLinksDialog">
			<template v-slot:body-content>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<Input label="Website" type="text" v-model="app.website" />
					<Input label="Support" type="text" v-model="app.support" />
					<Input
						label="Documentation"
						type="text"
						v-model="app.documentation"
					/>
					<Input
						label="Privacy Policy"
						type="text"
						v-model="app.privacy_policy"
					/>
					<Input
						label="Terms of Service"
						type="text"
						v-model="app.terms_of_service"
					/>
				</div>

				<ErrorMessage class="mt-4" :error="$resources.updateAppLinks.error" />
			</template>

			<template #actions>
				<div class="space-x-2">
					<Button @click="showEditLinksDialog = false">Cancel</Button>
					<Button
						appearance="primary"
						:loading="$resources.updateAppLinks.loading"
						loadingText="Saving..."
						@click="$resources.updateAppLinks.submit()"
					>
						Save changes
					</Button>
				</div>
			</template>
		</Dialog>
		<div class="divide-y" v-if="app">
			<ListItem title="Website" :description="app.website || 'N/A'" />
			<ListItem title="Support" :description="app.support || 'N/A'" />
			<ListItem
				title="Documentation"
				:description="app.documentation || 'N/A'"
			/>
			<ListItem
				title="Privacy Policy"
				:description="app.privacy_policy || 'N/A'"
			/>
			<ListItem
				title="Terms of Service"
				:description="app.terms_of_service || 'N/A'"
			/>
		</div>
	</Card>
</template>

<script>
export default {
	name: 'MarketplaceAppLinks',
	props: {
		app: Object
	},
	data() {
		return {
			showEditLinksDialog: false
		};
	},
	resources: {
		updateAppLinks() {
			return {
				method: 'press.api.marketplace.update_app_links',
				params: {
					name: this.app.name,
					links: {
						website: this.app.website,
						support: this.app.support,
						documentation: this.app.documentation,
						privacy_policy: this.app.privacy_policy,
						terms_of_service: this.app.terms_of_service
					}
				},
				onSuccess() {
					this.showEditLinksDialog = false;
					this.$notify({
						title: 'Links Updated!',
						icon: 'check',
						color: 'green'
					});
				}
			};
		}
	}
};
</script>
