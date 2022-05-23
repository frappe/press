<template>
	<WizardCard>
		<div class="mb-6 text-center">
			<h1 class="text-2xl font-bold">Add a New App</h1>
			<p class="text-base text-gray-700">Add a new SaaS App</p>
		</div>

		<SelectAppFromGithub @onSelect="d => (app = d)" />

		<div v-if="app">
			<label class="mb-3 text-base" for="version-select"
				>Compatible Frappe Version</label
			>
			<select
				id="version-select"
				class="form-select mb-4 block"
				v-model="version"
			>
				<option v-for="version in versionList" :key="version">
					{{ version }}
				</option>
			</select>

			<ErrorMessage class="mb-3" :error="$resourceErrors" />

			<Button
				:loading="$resources.addApp.loading"
				@click="$resources.addApp.submit()"
				type="primary"
				>Add Saas App</Button
			>
		</div>
	</WizardCard>
</template>

<script>
import WizardCard from '@/components/WizardCard.vue';
import SelectAppFromGithub from '@/components/SelectAppFromGithub.vue';

export default {
	name: 'NewSaasApp',
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
		frappeVersions() {
			return {
				method: 'press.api.marketplace.frappe_versions',
				auto: true,
				onSuccess(data) {
					if (data) {
						this.version = data[0];
					}
				}
			};
		},
		addApp() {
			return {
				method: 'press.api.saas.new_app',
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
					this.$router.push(`/saas/manage/${this.app.name}`);
				}
			};
		}
	},
	computed: {
		versionList() {
			if (
				!this.$resources.frappeVersions.data ||
				this.$resources.frappeVersions.loading
			) {
				return [];
			}
			return this.$resources.frappeVersions.data;
		}
	}
};
</script>
