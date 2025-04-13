<template>
	<div class="top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[
					{
						label: 'Install App',
						route: { name: 'InstallApp', params: { app: app } }
					}
				]"
			/>
		</Header>

		<div class="m-12 mx-auto max-w-2xl px-5">
			<div v-if="$resources.app.loading" class="py-4 text-base text-gray-600">
				Loading...
			</div>
			<div v-else class="space-y-6">
				<div class="mb-12 flex">
					<img
						:src="appDoc.image"
						class="h-12 w-12 rounded-lg border"
						:alt="appDoc.name"
					/>
					<div class="my-1 ml-4 flex flex-col justify-between">
						<h1 class="text-lg font-semibold">{{ appDoc.title }}</h1>
						<p class="text-sm text-gray-600">{{ appDoc.description }}</p>
					</div>
				</div>

				<div
					v-if="failure"
					class="flex items-center space-x-2 rounded border border-gray-200 bg-gray-100 p-4 text-base text-gray-700"
				>
					<i-lucide-alert-circle class="inline-block h-5 w-5" />
					<p>
						Failed to install the app.
						<router-link class="underline" :to="failureRoute">
							{{
								$resources.siteGroupDeploy.doc?.status === 'Bench Deploy Failed'
									? 'View Deploy'
									: 'View Job'
							}}
						</router-link>
						.
					</p>
				</div>
				<div class="divide-y rounded-lg bg-gray-50 px-4">
					<div
						v-for="step in steps"
						:key="step.id"
						class="flex items-center border-gray-200 px-1 py-3"
					>
						<div class="flex items-center space-x-4">
							<LoadingIndicator
								class="h-4 w-4 text-gray-900"
								v-if="step.icon() === 'loading'"
							/>
							<FeatherIcon
								v-else
								:name="step.icon()"
								class="h-5 w-5 rounded-full p-0.5 text-white"
								:stroke-width="3"
								:class="{
									'bg-green-500': step.icon() === 'check',
									'bg-red-500': step.icon() === 'x',
									'bg-gray-500': step.icon() === 'clock'
								}"
							/>
							<div class="flex flex-col space-y-1">
								<h5 class="text-base">{{ step.title }}</h5>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import { Breadcrumbs } from 'frappe-ui';
import Header from '../components/Header.vue';

export default {
	props: {
		app: {
			type: String,
			required: true
		}
	},
	pageMeta() {
		return {
			title: `Install ${this.appDoc.title} - Frappe Cloud`
		};
	},
	components: {
		FBreadcrumbs: Breadcrumbs,
		Header
	},
	data() {
		return {
			siteGroupDeployName: this.$route.query.siteGroupDeployName
		};
	},
	mounted() {
		this.$socket.emit(
			'doc_subscribe',
			'Site Group Deploy',
			this.siteGroupDeployName
		);

		this.$socket.on('doc_update', () => {
			this.$resources.siteGroupDeploy.reload();
		});
	},
	resources: {
		app() {
			return {
				url: 'press.api.marketplace.get',
				params: {
					app: this.app
				},
				auto: true
			};
		},
		siteGroupDeploy() {
			return {
				type: 'document',
				doctype: 'Site Group Deploy',
				name: this.siteGroupDeployName,
				onSuccess: doc => {
					if (doc.status === 'Site Created') {
						setTimeout(() => {
							this.$router.push({
								name: 'Site Detail Overview',
								params: { name: doc.site }
							});
						}, 1000);
					}
				}
			};
		}
	},
	computed: {
		failure() {
			return ['Site Creation Failed', 'Bench Deploy Failed'].includes(
				this.$resources.siteGroupDeploy.doc?.status
			);
		},
		failureRoute() {
			if (this.$resources.siteGroupDeploy.doc?.status === 'Bench Deploy Failed')
				return {
					name: 'Release Group Detail Deploys',
					params: {
						name: this.$resources.siteGroupDeploy.doc.release_group
					}
				};
			else if (
				this.$resources.siteGroupDeploy.doc?.status === 'Site Creation Failed'
			)
				return {
					name: 'Site Jobs',
					params: { name: this.$resources.siteGroupDeploy.doc.site }
				};
		},
		steps() {
			const statusPosition = status => {
				if (!status) return -1;

				return [
					'Pending',
					'Deploying Bench',
					'Bench Deployed',
					'Bench Deploy Failed',
					'Creating Site',
					'Site Created',
					'Site Creation Failed'
				].indexOf(status);
			};
			const status = this.$resources.siteGroupDeploy?.doc?.status;

			return [
				{
					id: 0,
					title: 'Initializing',
					description: 'Initializing the setup',
					status: 'Pending',
					icon: () => {
						if (statusPosition(status) === 0) {
							return 'loading';
						} else if (statusPosition(status) > 0) {
							return 'check';
						}
					},
					message: 'This should take a few minutes'
				},
				{
					id: 1,
					title:
						statusPosition(status) <= 1 ? 'Deploying Bench' : 'Bench Deployed',
					description: 'Deploying bench on the server',
					status: 'Deploying Bench',
					icon: () => {
						if (status === 'Bench Deploy Failed') {
							return 'x';
						} else if (statusPosition(status) === 1) {
							return 'loading';
						} else if (statusPosition(status) > 1) {
							return 'check';
						} else {
							return 'clock';
						}
					},
					message: 'This should take a few minutes'
				},
				{
					id: 2,
					title: statusPosition(status) <= 4 ? 'Creating Site' : 'Site Created',
					description: 'Creating site on the server',
					status: 'Creating Site',
					icon: () => {
						if (status === 'Site Creation Failed') {
							return 'x';
						} else if (statusPosition(status) === 4) {
							return 'loading';
						} else if (statusPosition(status) > 4) {
							return 'check';
						} else {
							return 'clock';
						}
					},
					message: 'This should take a few minutes'
				}
			];
		},
		appDoc() {
			return this.$resources.app.data || {};
		}
	}
};
</script>
