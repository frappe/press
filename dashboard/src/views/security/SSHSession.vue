<template>
	<CardWithDetails
		title="Server SSH Session Logs"
		subtitle="Log of commands executed in session"
	>
		<div>
			<router-link
				v-for="log in $resources.sshLogs.data"
				class="block cursor-pointer rounded-md px-2.5"
				:class="logId === log.name ? 'bg-gray-100' : 'hover:bg-gray-50'"
				:key="log.name"
				:to="updateRoute(log.name)"
			>
				<ListItem :title="getTitle(log)" :description="getDescription(log)">
					<template v-slot:actions>
						<Badge :label="getLabel(log.user)" :theme="getColor(log.user)" />
					</template>
				</ListItem>
				<div class="border-b"></div>
			</router-link>
		</div>
		<template #details>
			<SSHSessionActivity
				:showDetails="logId"
				:logId="logId"
				:server="server"
			/>
		</template>
	</CardWithDetails>
</template>

<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import SSHSessionActivity from './SSHSessionActivity.vue';

export default {
	name: 'SSHSession',
	props: ['server', 'logId'],
	components: { CardWithDetails, SSHSessionActivity },
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
			return `SSH Session: ${log.session_id}`;
		},
		getDescription(log) {
			return `Created On: ${log.created_at} <br> Size: ${log.size} Kb`;
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
