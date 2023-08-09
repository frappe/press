<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<BreadCrumbs :items="[{ label: 'Servers', route: { name: 'Servers' } }]">
				<template v-if="this.$account.team.enabled" #actions>
					<Dropdown
						v-if="
							$account.team.self_hosted_servers_enabled === 1 &&
							!showAddCardDialog
						"
						:options="dropDownOptions"
					>
						<Button
							variant="solid"
							iconLeft="plus"
							label="Create"
							class="ml-2 hidden sm:inline-flex"
						/>
					</Dropdown>
					<Button
						v-else
						variant="solid"
						iconLeft="plus"
						label="Create"
						class="ml-2 hidden sm:inline-flex"
						@click="showBillingDialog"
					/>
				</template>
			</BreadCrumbs>
		</header>

		<div>
			<SectionHeader class="mx-5 mt-6" :heading="getServerFilterHeading()">
				<template #actions>
					<Dropdown :options="serverFilterOptions()">
						<template v-slot="{ open }">
							<Button
								:class="[
									'rounded-md px-3 py-1 text-base font-medium',
									open ? 'bg-gray-200' : 'bg-gray-100'
								]"
								icon-right="chevron-down"
								>{{ serverFilter.replace('tag:', '') }}</Button
							>
						</template>
					</Dropdown>
				</template>
			</SectionHeader>
			<div class="mx-5 mt-3">
				<LoadingText v-if="$resources.allServers.loading" />
				<div v-else>
					<div class="flex">
						<div class="flex w-full px-3 py-4">
							<div class="w-4/12 text-base font-medium text-gray-900">
								Server Name
							</div>
							<div class="w-2/12 text-base font-medium text-gray-900">
								Status
							</div>
							<div class="w-2/12 text-base font-medium text-gray-900">
								Region
							</div>
							<div class="w-2/12 text-base font-medium text-gray-900">Plan</div>
						</div>
						<div class="w-8" />
					</div>
					<div class="mx-2.5 border-b" />
					<ListView :items="servers" :dropdownItems="dropdownItems" />
				</div>
			</div>
		</div>
		<Dialog
			:options="{ title: 'Add card to create new servers' }"
			v-model="showAddCardDialog"
		>
			<template v-slot:body-content>
				<StripeCard
					class="mb-1"
					v-if="showAddCardDialog"
					@complete="
						showAddCardDialog = false;
						$resources.paymentMethods.reload();
					"
				/>
			</template>
		</Dialog>
	</div>
</template>
<script>
import ListView from '@/components/ListView.vue';
import PageHeader from '@/components/global/PageHeader.vue';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'Servers',
	components: {
		ListView,
		PageHeader,
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		)
	},
	pageMeta() {
		return {
			title: 'Servers - Frappe Cloud'
		};
	},
	data() {
		return {
			showAddCardDialog: false,
			serverFilter: 'All Servers',
			dropDownOptions: [
				{
					label: 'Frappe Cloud Server',
					onClick: () => this.$router.replace('/servers/new')
				},
				{
					label: 'Self Hosted Server',
					onClick: () => this.$router.replace('/selfhosted/new')
				}
			]
		};
	},
	resources: {
		allServers() {
			return {
				method: 'press.api.server.all',
				params: { server_filter: this.serverFilter },
				auto: true
			};
		},
		serverTags: 'press.api.server.server_tags'
	},
	methods: {
		dropdownItems(server) {
			return [
				{
					label: 'Visit Server',
					onClick: () => {
						window.open(`https://${server.name}`, '_blank');
					}
				},
				{
					label: 'New Bench',
					onClick: () => {
						this.$router.push(`/servers/${server.app_server}/bench/new`);
					}
				}
			];
		},
		getServerFilterHeading() {
			if (this.serverFilter.startsWith('tag:'))
				return `Servers with tag ${this.serverFilter.slice(4)}`;
			return this.serverFilter;
		},
		reload() {
			// refresh if currently not loading and have not reloaded in the last 5 seconds
			if (
				!this.$resources.allServers.loading &&
				new Date() - this.$resources.allServers.lastLoaded > 5000
			) {
				this.$resources.allServers.reload();
			}
		},
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				if (this.$account.team.self_hosted_servers_enabled !== 1) {
					this.$router.replace('/servers/new');
				}
				this.showAddCardDialog = false;
			}
		},
		serverFilterOptions() {
			const options = [
				{
					group: 'Types',
					items: [
						{
							label: 'All Servers',
							onClick: () => (this.serverFilter = 'All Servers')
						},
						{
							label: 'App Servers',
							onClick: () => (this.serverFilter = 'App Servers')
						},
						{
							label: 'Database Servers',
							onClick: () => (this.serverFilter = 'Database Servers')
						}
					]
				}
			];

			if (!this.$resources.serverTags?.data?.length) return options;

			return [
				...options,
				{
					group: 'Tags',
					items: this.$resources.serverTags.data.map(tag => ({
						label: tag,
						onClick: () => (this.serverFilter = `tag:${tag}`)
					}))
				}
			];
		}
	},
	computed: {
		servers() {
			if (!this.$resources.allServers.data) {
				return [];
			}

			return this.$resources.allServers.data.map(server => ({
				name: server.name,
				status: server.status,
				server_region_info: server.region_info,
				plan: server.plan,
				link: { name: 'ServerOverview', params: { serverName: server.name } }
			}));
		}
	}
};
</script>
