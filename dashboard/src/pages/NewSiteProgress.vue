<template>
	<div class="top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[
					{ label: 'Sites', route: '/sites' },
					{ label: 'New Site', route: '/sites/new' },
					{ label: 'Creating Site' },
				]"
			/>
		</Header>

		<div class="m-12 mx-auto max-w-2xl px-5">
			<div v-if="!siteGroupDeployName" class="py-4 text-base text-gray-600">
				<p>Missing deployment information.</p>
				<router-link to="/sites/new" class="mt-2 text-blue-600 underline">
					Go back to site creation
				</router-link>
			</div>
			<div v-else-if="isLoading" class="py-4 text-base text-gray-600">
				Loading...
			</div>
			<div v-else class="space-y-6">
				<h1 class="text-2xl font-semibold">Creating Your Site</h1>

				<div
					v-if="hasFailed"
					class="flex items-center space-x-2 rounded border border-red-200 bg-red-50 p-4 text-base text-red-700"
				>
					<lucide-alert-circle class="inline-block h-5 w-5" />
					<p>
						Failed to create the site.
						<router-link class="underline" :to="failureRoute">
							{{ failureLinkText }}
						</router-link>
					</p>
				</div>

				<div
					v-if="!hasFailed"
					class="flex items-center space-x-2 rounded border border-blue-100 bg-blue-50 p-4 text-base font-medium text-blue-800"
				>
					<p>
						We're spinning up a private bench and creating your site. This
						process takes a few minutes.
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
								v-if="step.icon === 'loading'"
								class="h-4 w-4 text-gray-900"
							/>
							<FeatherIcon
								v-else
								:name="step.icon"
								class="h-5 w-5 rounded-full p-0.5 text-white"
								:stroke-width="3"
								:class="{
									'bg-green-500': step.icon === 'check',
									'bg-red-500': step.icon === 'x',
									'bg-gray-500': step.icon === 'clock',
								}"
							/>
							<div class="flex flex-col space-y-1">
								<h5 class="text-base">{{ step.title }}</h5>
								<p class="text-sm text-gray-600">{{ step.message }}</p>
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

const STATUS = {
	PENDING: 'Pending',
	DEPLOYING_BENCH: 'Deploying Bench',
	BENCH_DEPLOYED: 'Bench Deployed',
	BENCH_DEPLOY_FAILED: 'Bench Deploy Failed',
	CREATING_SITE: 'Creating Site',
	SITE_CREATED: 'Site Created',
	SITE_CREATION_FAILED: 'Site Creation Failed',
};

const STATUS_ORDER = [
	STATUS.PENDING,
	STATUS.DEPLOYING_BENCH,
	STATUS.BENCH_DEPLOYED,
	STATUS.BENCH_DEPLOY_FAILED,
	STATUS.CREATING_SITE,
	STATUS.SITE_CREATED,
	STATUS.SITE_CREATION_FAILED,
];

const REDIRECT_DELAY_SUCCESS = 1000;
const REDIRECT_DELAY_ERROR = 2000;

export default {
	name: 'NewSiteProgress',
	props: {
		siteGroupDeployName: {
			type: String,
			required: true,
		},
	},
	components: {
		FBreadcrumbs: Breadcrumbs,
		Header,
	},
	mounted() {
		this.$socket.emit(
			'doc_subscribe',
			'Site Group Deploy',
			this.siteGroupDeployName,
		);

		this.$socket.on('doc_update', this.handleDocUpdate);
	},
	beforeUnmount() {
		this.$socket.off('doc_update', this.handleDocUpdate);
	},
	methods: {
		handleDocUpdate() {
			this.$resources.siteGroupDeploy.reload();
		},
		getStatusPosition(status) {
			return STATUS_ORDER.indexOf(status);
		},
		getStepIcon(stepPosition, currentPosition, failedStatus = null) {
			if (failedStatus && this.deployDoc?.status === failedStatus) {
				return 'x';
			}
			if (currentPosition === stepPosition) {
				return 'loading';
			}
			if (currentPosition > stepPosition) {
				return 'check';
			}
			return 'clock';
		},
		redirectOnComplete(doc) {
			const redirectMap = {
				[STATUS.SITE_CREATED]: {
					name: 'Site Detail Overview',
					params: { name: doc.site },
					delay: REDIRECT_DELAY_SUCCESS,
				},
				[STATUS.BENCH_DEPLOY_FAILED]: {
					name: 'Release Group Detail Deploys',
					params: { name: doc.release_group },
					delay: REDIRECT_DELAY_ERROR,
				},
				[STATUS.SITE_CREATION_FAILED]: {
					name: 'Site Jobs',
					params: { name: doc.site },
					delay: REDIRECT_DELAY_ERROR,
				},
			};

			const redirect = redirectMap[doc.status];
			if (redirect) {
				setTimeout(() => {
					this.$router.push({
						name: redirect.name,
						params: redirect.params,
					});
				}, redirect.delay);
			}
		},
	},
	resources: {
		siteGroupDeploy() {
			return {
				type: 'document',
				doctype: 'Site Group Deploy',
				name: this.siteGroupDeployName,
				auto: true,
				onSuccess: this.redirectOnComplete,
			};
		},
	},
	computed: {
		deployDoc() {
			return this.$resources.siteGroupDeploy.doc;
		},
		isLoading() {
			return this.$resources.siteGroupDeploy.loading;
		},
		hasFailed() {
			return [STATUS.SITE_CREATION_FAILED, STATUS.BENCH_DEPLOY_FAILED].includes(
				this.deployDoc?.status,
			);
		},
		failureLinkText() {
			return this.deployDoc?.status === STATUS.BENCH_DEPLOY_FAILED
				? 'View Deploy'
				: 'View Job';
		},
		failureRoute() {
			if (this.deployDoc?.status === STATUS.BENCH_DEPLOY_FAILED) {
				return {
					name: 'Release Group Detail Deploys',
					params: { name: this.deployDoc.release_group },
				};
			}
			if (this.deployDoc?.status === STATUS.SITE_CREATION_FAILED) {
				return {
					name: 'Site Jobs',
					params: { name: this.deployDoc.site },
				};
			}
			return null;
		},
		currentStatusPosition() {
			return this.getStatusPosition(this.deployDoc?.status);
		},
		steps() {
			const pos = this.currentStatusPosition;

			return [
				{
					id: 0,
					title: 'Initializing',
					icon: this.getStepIcon(0, pos),
				},
				{
					id: 1,
					title: pos > 2 ? 'Bench Deployed' : 'Deploying Bench',
					icon: this.getStepIcon(
						[1, 2].includes(pos) ? pos : 1,
						pos,
						STATUS.BENCH_DEPLOY_FAILED,
					),
					message: 'Provisioning your private bench environment',
				},
				{
					id: 2,
					title: pos > 4 ? 'Site Created' : 'Creating Site',
					icon: this.getStepIcon(4, pos, STATUS.SITE_CREATION_FAILED),
					message: 'Installing apps and setting up your site',
				},
			];
		},
	},
};
</script>
