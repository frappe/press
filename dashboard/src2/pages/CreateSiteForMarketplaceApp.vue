<template>
	<div class="top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[
					{
						label: 'Install App'
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
				<div>
					<Progress
						size="md"
						:value="setupProgressValue"
						:label="progressLabel"
						:hint="true"
					/>
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
			setupProgressValue: 0,
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
					if (doc.status === 'Pending') {
						this.setupProgressValue = 10;
					} else if (doc.status === 'Deploying Bench') {
						this.setupProgressValue = 30;
					} else if (doc.status === 'Bench Deployed') {
						this.setupProgressValue = 50;
					} else if (doc.status === 'Site Created') {
						this.setupProgressValue = 100;
						setTimeout(() => {
							this.$router.push({
								name: 'Site Detail Jobs',
								params: { name: doc.site }
							});
						}, 1000);
					}
				}
			};
		}
	},
	computed: {
		appDoc() {
			return this.$resources.app.data || {};
		},
		progressLabel() {
			const status = this.$resources.siteGroupDeploy.doc.status;
			return `${status}... This should take a few minutes...`;
		}
	}
};
</script>
