<template>
	<WizardCard>
		<div class="mb-6 text-center ">
			<h1 class="text-2xl font-bold">Add a New App</h1>
			<p class="text-base text-gray-700">
				{{
					benchName ? 'Add an app to your bench' : 'Add an app to marketplace'
				}}
			</p>
		</div>
		<div class="flex justify-center">
			<Loading v-if="$resources.options.loading" />
			<div v-if="needsAuthorization">
				<Button
					type="primary"
					icon-left="github"
					:link="options.installation_url + '?state=' + state"
				>
					Connect To GitHub
				</Button>
			</div>
		</div>
		<div v-if="options">
			<div v-if="options.authorized && options.installations.length > 0">
				<div class="flex items-baseline justify-between pb-1 border-b">
					<label class="text-lg font-semibold">
						Select a repository
					</label>
					<span class="text-sm text-gray-600">
						Don't see your organization?
						<Link
							:to="options.installation_url + '?state=' + state"
							class="font-medium"
						>
							Add from GitHub
						</Link>
					</span>
				</div>
				<div class="mt-2">
					<NewAppRepositories
						:options="options"
						:repositoryResource="$resources.repository"
						:selectedRepo.sync="selectedRepo"
						:selectedInstallation.sync="selectedInstallation"
						:selectedBranch.sync="selectedBranch"
					/>
					<div v-if="validateApp.data" class="mt-4 text-base text-medium">
						<div v-if="validatedApp" class="flex">
							<GreenCheckIcon class="w-4 mr-2" />
							Found {{ validatedApp.title }} ({{ validatedApp.name }})
						</div>
						<ErrorMessage v-else error="Not a valid frappe application" />
					</div>
				</div>
				<div class="flex items-center mt-4">
					<ErrorMessage :error="$resourceErrors" />
					<Button
						type="primary"
						v-if="selectedRepo && selectedBranch && !validatedApp"
						@click="$resources.validateApp.submit()"
						:loading="$resources.validateApp.loading"
					>
						Validate App
					</Button>
					<Button
						type="primary"
						v-if="validatedApp"
						@click="addApp.submit()"
						:loading="addApp.loading"
					>
						{{ benchName ? 'Add app to bench' : 'Add app to marketplace' }}
					</Button>
				</div>
			</div>
		</div>
	</WizardCard>
</template>

<script>
import GreenCheckIcon from '@/components/global/GreenCheckIcon.vue';
import NewAppRepositories from './NewAppRepositories.vue';
import ErrorMessage from '@/components/global/ErrorMessage.vue';
import WizardCard from '@/components/WizardCard.vue';
export default {
	name: 'NewApp',
	components: {
		NewAppRepositories,
		GreenCheckIcon,
		ErrorMessage,
		WizardCard
	},
	props: ['benchName'],
	data() {
		return {
			selectedRepo: null,
			selectedInstallation: null,
			selectedBranch: null
		};
	},
	resources: {
		options: 'press.api.github.options',
		repository() {
			let auto = this.selectedInstallation && this.selectedRepo;
			let params = {
				installation: this.selectedInstallation?.id,
				owner: this.selectedInstallation?.login,
				name: this.selectedRepo?.name
			};

			return {
				method: 'press.api.github.repository',
				params,
				auto,
				onSuccess(repository) {
					this.selectedBranch = repository.default_branch;
				}
			};
		},
		validateApp() {
			let params = {
				installation: this.selectedInstallation?.id,
				owner: this.selectedInstallation?.login,
				repository: this.selectedRepo?.name,
				branch: this.selectedBranch
			};
			return {
				method: 'press.api.github.app',
				params
			};
		},
		addApp() {
			return {
				method: this.benchName
					? 'press.api.app.new'
					: 'press.api.developer.new_app',
				params: {
					app: {
						name: this.validatedApp?.name,
						title: this.validatedApp?.title,
						group: this.benchName,
						repository_url: this.selectedRepo?.url,
						branch: this.selectedBranch,
						github_installation_id: this.selectedInstallation?.id
					}
				},
				onSuccess() {
					if (this.benchName) {
						this.$router.push(`/benches/${this.benchName}`);
					} else {
						this.$router.push('/developer/apps');
					}
				}
			};
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		needsAuthorization() {
			if (this.$resources.options.loading) return false;
			return (
				this.$resources.options.data &&
				(!this.$resources.options.data.authorized ||
					this.$resources.options.data.installations.length === 0)
			);
		},
		state() {
			let location = window.location.href;
			let state = { team: this.$account.team.name, url: location };
			return btoa(JSON.stringify(state));
		},
		validatedApp() {
			if (
				this.$resources.validateApp.loading ||
				!this.$resources.validateApp.data
			) {
				return null;
			}
			if (
				this.$resources.validateApp.data &&
				this.$resources.validateApp.data.name
			) {
				return this.$resources.validateApp.data;
			}
			return null;
		}
	}
};
</script>
