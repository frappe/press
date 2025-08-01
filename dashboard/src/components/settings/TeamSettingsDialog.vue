<template>
	<Dialog
		:options="{
			title: 'Settings',
		}"
		v-model="show"
	>
		<template #body-content>
			<div class="mt-8 flex flex-col gap-4">
				<Switch
					v-model="enforce2FA"
					label="Enforce 2FA"
					description="Require all team members to enable 2FA"
				/>
				<Switch
					v-model="enableBenchGroups"
					label="Enable Bench Groups"
					description="Enable bench groups for your team"
				/>
				<Switch
					v-model="enableServers"
					label="Enable Servers"
					description="Enable servers for your team"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Switch } from 'frappe-ui';

export default {
	data() {
		return {
			show: true,
		};
	},
	components: { Switch },
	computed: {
		enforce2FA: {
			get() {
				return Boolean(this.$team?.doc.enforce_2fa);
			},
			set(value) {
				this.$team.setValue.submit({ enforce_2fa: value });
			},
		},
		enableBenchGroups: {
			get() {
				return Boolean(this.$team?.doc.benches_enabled);
			},
			set(value) {
				this.$team.setValue.submit({ benches_enabled: value });
			},
		},
		enableServers: {
			get() {
				return Boolean(this.$team?.doc.servers_enabled);
			},
			set(value) {
				this.$team.setValue.submit({ servers_enabled: value });
			},
		},
	},
};
</script>
