<template>
	<Card
		class="min-h-full h-full max-h-96"
		title="Security Updates"
		:subtitle="'Pedning security updates'"
	>
		<div class="divide-y">
			<ListItem
				v-for="a in securityUpdates.data"
				:title="`Package: ${a.package}`"
				:description="getDescription(a)"
			>
				<template v-slot:actions>
					<Badge :label="a.priority" :theme="getColor(a.priority)" />
				</template>
			</ListItem>
		</div>

		<template #actions>
			<router-link
				class="text-base text-blue-500 hover:text-blue-600"
				:to="`/servers/${server.name}/security_updates`"
			>
				View details →
			</router-link>
		</template>
	</Card>
</template>
<script>
export default {
	name: 'SecurityUpdates',
	props: ['server'],
	inject: ['viewportWidth'],
	resources: {
		securityUpdates() {
			return {
				method: 'press.api.security.fetch_security_updates',
				params: {
					server: this.server?.name,
					start: 0,
					limit: 3
				},
				auto: true,
				pageLength: 3,
				keepData: true
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
			return `Version: ${a.version} <br> ${this.formatDate(a.datetime)}`;
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
		}
	}
};
</script>
