<template>
	<Card class="min-h-full h-full max-h-96" title="SSH Sessions">
		<div class="divide-y"></div>
	</Card>
</template>

<script>
import { Card } from 'frappe-ui';

export default {
	name: 'SSHOverview',
	props: ['server'],
	components: { Card },
	resources: {
		getSSHSessions() {
			return {
				method: 'press.api.security.fetch_ssh_sessions',
				params: {
					server: this.server?.name,
					start: 0,
					limit: 3
				}
			};
		}
	}
};
</script>
