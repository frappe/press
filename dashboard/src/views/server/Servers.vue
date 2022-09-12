<template>
	<div>
		<PageHeader title="Servers" subtitle="Your Servers">
			<template v-if="this.$account.team.enabled" v-slot:actions>
				<Button
					appearance="primary"
					iconLeft="plus"
					class="ml-2 hidden sm:inline-flex"
					route="/servers/new"
				>
					New
				</Button>
			</template>
		</PageHeader>

		<div>
			<SectionHeader heading="All Servers">
				<template v-if="!recentServersVisible" v-slot:actions>
					<SiteAndBenchSearch />
				</template>
			</SectionHeader>

			<div class="mt-3">
				<LoadingText v-if="$resources.allServers.loading" />
				<ServerList v-else :servers="servers" />
			</div>
		</div>
	</div>
</template>
<script>
import ServerList from '@/views/server/ServerList.vue';
import SiteAndBenchSearch from '@/components/SiteAndBenchSearch.vue';
import PageHeader from '@/components/global/PageHeader.vue';

export default {
	name: 'Servers',
	components: {
		ServerList,
		SiteAndBenchSearch,
		PageHeader
	},
	data() {
		return {};
	},
	resources: {
		allServers: {
			method: 'press.api.server.all',
			auto: true
		}
	},
	methods: {
		reload() {
			// refresh if currently not loading and have not reloaded in the last 5 seconds
			if (
				!this.$resources.allServers.loading &&
				new Date() - this.$resources.allServers.lastLoaded > 5000
			) {
				this.$resources.allServers.reload();
			}
		}
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
