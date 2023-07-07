<template>
	<div>
		<PageHeader title="Servers" subtitle="Your Servers">
			<template v-if="this.$account.team.enabled" v-slot:actions>
				<Dropdown
					v-if="
						$account.team.self_hosted_servers_enabled === 1 &&
						!showAddCardDialog
					"
					:options="dropDownOptions"
				>
					<!-- <template v-slot="{ open }"> -->
					<Button
						appearance="primary"
						iconLeft="plus"
						class="ml-2 hidden sm:inline-flex"
						@click="showBillingDialog"
					>
						New
					</Button>
					<!-- </template> -->
				</Dropdown>
				<Button
					v-else
					appearance="primary"
					iconLeft="plus"
					class="ml-2 hidden sm:inline-flex"
					@click="showBillingDialog"
				>
					New
				</Button>
			</template>
		</PageHeader>

		<div>
			<SectionHeader :heading="serverFilter">
				<template #actions>
					<Input
						v-if="!$resources.serverTags.loading"
						type="select"
						:options="[...serverTypeOptions, ...$resources.serverTags.data.map(tag => ({ label: tag, value: `tag:${tag}` }))]"
						v-model="serverFilter"
						@change="handleChange"
					/>
				</template>
			</SectionHeader>
			<div class="mt-3">
				<LoadingText v-if="$resources.allServers.loading && pageStart === 0" />
				<ServerList v-else :servers="servers" />
			</div>
			<div
				class="py-3"
				v-if="!$resources.allServers.lastPageEmpty && servers.length > 0"
			>
				<Button
					:loading="$resources.allServers.loading"
					loadingText="Loading..."
					@click="pageStart += 10"
				>
					Load more
				</Button>
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
import ServerList from '@/views/server/ServerList.vue';
import PageHeader from '@/components/global/PageHeader.vue';
import Dropdown from 'frappe-ui/src/components/Dropdown.vue';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'Servers',
	components: {
		ServerList,
		PageHeader,
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		),
		Dropdown
	},
	data() {
		return {
			showAddCardDialog: false,
			pageStart: 0,
			serverFilter: 'All Servers',
			serverTypeOptions: [
				{
					label: 'All Servers',
					value: 'All Servers'
				},
				{
					label: 'App Servers',
					value: 'App Servers'
				},
				{
					label: 'Database Servers',
					value: 'Database Servers'
				}
			],
			dropDownOptions: [
				{
					label: 'Frappe Cloud Server',
					handler: () => this.$router.replace('/servers/new')
				},
				{
					label: 'Self Hosted Server',
					handler: () => this.$router.replace('/selfhosted/new')
				}
			],
		};
	},
	resources: {
		allServers() {
			return {
				method: 'press.api.server.all',
				params: { start: this.pageStart, server_filter: this.serverFilter },
				pageLength: 10,
				keepData: true,
				auto: true
			};
		},
		serverTags: 'press.api.server.server_tags',
	},
	methods: {
		handleChange() {
			// wrapping in a timeout to avoid a bug where the previous filter's data is fetched again
			setTimeout(() => {
				this.pageStart = 0;
				this.$resources.allServers.reset();
			}, 1);
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
	},
	computed: {
		servers() {
			if (!this.$resources.allServers.data) {
				return [];
			}
			return this.$resources.allServers.data;
		}
	}
};
</script>
