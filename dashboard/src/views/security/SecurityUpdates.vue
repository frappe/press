<template>
	<CardWithDetails :title="getTitle()" :subtitle="getSubTitle()">
		<div>
			<router-link
				v-for="sec_update in $resources.updates.data"
				class="block cursor-pointer rounded-md px-2.5"
				:key="sec_update.name"
				:to="updateRoute(sec_update.name)"
			>
				<ListItem
					:title="sec_update.package"
					:description="formatDate(sec_update.datetime)"
				>
				</ListItem>
				<div class="border-b"></div>
			</router-link>
			<div class="py-3" v-if="!$resources.updates.lastPageEmpty">
				<Button
					:loading="$resources.updates.loading"
					loadingText="Loading..."
					@click="pageStart += 10"
				>
					Load more
				</Button>
			</div>
		</div>
		<template #details>
			<SecurityUpdateInfo :showDetails="updateId" :updateId="updateId" />
		</template>
	</CardWithDetails>
</template>
<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import SecurityUpdateInfo from './SecurityUpdateInfo.vue';

export default {
	name: 'SecurityUpdates',
	props: ['server', 'updateId'],
	inject: ['viewportWidth'],
	components: {
		CardWithDetails,
		SecurityUpdateInfo
	},
	data() {
		return {
			pageStart: 0
		};
	},
	resources: {
		updates() {
			return this.securityUpdateResource(this.pageStart);
		}
	},
	methods: {
		securityUpdateResource(start) {
			return {
				method: 'press.api.security.fetch_security_updates',
				params: { server: this.server?.name, start },
				pageLength: 10,
				keepData: true,
				auto: true
			};
		},
		updateRoute(sec_update) {
			return `/servers/${this.server.name}/security_updates/${sec_update}`;
		},

		getTitle() {
			return 'Security Updates';
		},

		getSubTitle() {
			return 'Pending security updates';
		}
	},
	computed: {
		updates() {
			return this.$resources.updates.data;
		}
	}
};
</script>
