<template>
	<CardWithDetails :title="getTitle()" :subtitle="getSubTitle()">
		<div>
			<router-link
				v-for="sec_update in $resources.updates.data"
				class="block cursor-pointer rounded-md px-2.5"
				:class="
					updateId === sec_update.name ? 'bg-gray-100' : 'hover:bg-gray-50'
				"
				:key="sec_update.name"
				:to="updateRoute(sec_update.name)"
			>
				<ListItem
					:title="sec_update.package"
					:description="formatDate(sec_update.datetime)"
				>
					<template v-slot:actions>
						<Badge
							:label="sec_update.priority"
							:theme="getColor(sec_update.priority)"
						/>
					</template>
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
import { formatDate } from '@vueuse/core';

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
			return `/security/${this.server.name}/security_update/${sec_update}`;
		},

		getTitle() {
			return 'Security Updates';
		},

		getSubTitle() {
			return 'Pending security updates';
		},
		getColor(priority) {
			switch (priority) {
				case 'High':
					return 'red';
				case 'Medium':
					return 'orange';
				case 'Low':
					return 'green';
				default:
					return 'gray';
			}
		},
		getDescription(priority) {
			switch (priority) {
				case 'High':
					return 'Critical';
				case 'Medium':
					return 'Important';
				case 'Low':
					return 'Minor';
				default:
					return 'Unknown';
			}
		}
	},
	computed: {
		updates() {
			return this.$resources.updates.data;
		}
	}
};
</script>
