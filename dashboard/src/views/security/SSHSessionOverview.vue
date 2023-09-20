<template>
	<Card class="h-full max-h-96 min-h-full" title="SSH Activity Log">
		<div class="divide-y">
			<router-link
				v-for="log in $resources.sshLogs.data"
				class="block cursor-pointer rounded-md px-2.5"
				:key="log.name"
				:to="updateRoute(log.name)"
			>
				<ListItem :title="getTitle(log)" :description="getDescription(log)">
					<template v-slot:actions>
						<Badge :label="getLabel(log.user)" :theme="getColor(log.user)" />
					</template>
				</ListItem>
			</router-link>
		</div>
		<template #actions>
			<router-link
				class="text-base text-blue-500 hover:text-blue-600"
				:to="`/security/${server.name}/ssh_session_logs`"
			>
				View details →
			</router-link>
		</template>
	</Card>
</template>

<script>
import { Card } from 'frappe-ui';

export default {
	name: 'SSHSessionsOverview',
	props: ['server'],
	components: { Card },
	resources: {
		sshLogs() {
			return {
				url: 'press.api.security.fetch_ssh_session_logs',
				params: {
					server: this.server?.name
				},
				auto: true
			};
		}
	},
	computed: {
		sshLogs() {
			return this.$resources.sshLogs.data;
		}
	},
	methods: {
		getTitle(log) {
			return `SSH Session Id: ${log.session_id}`;
		},
		getDescription(log) {
			return `Created On: ${this.formatDate(log.created)} <br> Size: ${
				log.size
			} Kb`;
		},
		updateRoute(name) {
			return `/security/${this.server.name}/ssh_session_logs/${name}`;
		},
		getLabel(user) {
			return `User: ${user}`;
		},
		getColor(user) {
			return user === 'root' ? 'red' : 'green';
		}
	}
};
</script>
