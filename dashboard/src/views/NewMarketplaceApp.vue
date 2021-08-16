<template>
	<WizardCard>
		<div class="mb-6 text-center ">
			<h1 class="text-2xl font-bold">Add a New App</h1>
			<p class="text-base text-gray-700">
				Add an app to marketplace
			</p>
		</div>

		<SelectAppFromGithub @onSelect="d => (app = d)" />

		<Button v-if="app" @click="this.$resources.addApp.submit()"
			>Add to marketplace</Button
		>
	</WizardCard>
</template>

<script>
import WizardCard from '@/components/WizardCard.vue';
import SelectAppFromGithub from '@/components/SelectAppFromGithub.vue';

export default {
	name: 'NewMarketplaceApp',
	components: {
		WizardCard,
		SelectAppFromGithub
	},
	data() {
		return {
			app: null,
			version: null
		};
	},
	resources: {
		addApp() {
			return {
				method: 'press.api.developer.new_app',
				params: {
					app: {
						name: this.app?.name,
						title: this.app?.title,
						repository_url: this.app?.repository_url,
						branch: this.app?.branch,
						github_installation_id: this.app?.github_installation_id,
						version: this.version
					}
				},
				onSuccess() {
					this.$router.push(`/developer/apps/${this.app.name}`);
				}
			};
		}
	}
};
</script>
