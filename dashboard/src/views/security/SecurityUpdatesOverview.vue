<template>
	<Card
		class="h-full max-h-96 min-h-full"
		title="Security Updates"
		subtitle="Pedning security updates"
	>
		<div class="divide-y">
			<router-link
				v-for="sec_update in securityUpdates.data"
				class="block cursor-pointer rounded-md px-2.5"
				:key="sec_update.name"
				:to="updateRoute(sec_update.name)"
			>
				<ListItem
					:title="`Package: ${sec_update.package}`"
					:description="getDescription(sec_update)"
				>
					<template v-slot:actions>
						<Badge
							:label="sec_update.priority"
							:theme="getColor(sec_update.priority)"
						/>
					</template>
				</ListItem>
			</router-link>
		</div>

		<template #actions>
			<router-link
				class="text-base text-blue-500 hover:text-blue-600"
				:to="`/security/${server.name}/security_update`"
			>
				View details →
			</router-link>
		</template>
	</Card>
</template>
<script>
export default {
	name: 'SecurityUpdatesOverview',
	props: ['server'],
	inject: ['viewportWidth'],
	resources: {
		securityUpdates() {
			return {
				type: 'list',
				doctype: 'Security Update',
				url: 'press.api.security.fetch_security_updates',
				filters: { server: this.server?.name },
				orderBy: 'priority_level asc',
				pageLength: 3,
				start: 0,
				auto: true
			};
		}
	},
	computed: {
		securityUpdates() {
			return this.$resources.securityUpdates;
		}
	},
	methods: {
		getDescription(a) {
			return `Version: ${a.version} | ${this.formatDate(a.datetime)}`;
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
		updateRoute(sec_update) {
			return `/security/${this.server.name}/security_update/${sec_update}`;
		}
	}
};
</script>
