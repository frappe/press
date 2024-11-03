<template>
	<Dialog :options="{ title: 'Drop Active Servers' }" v-model="showDialog">
		<template #body-content>
			<div class="prose text-base">
				Please drop the following active servers before disabling the account:
				<ul class="pt-2">
					<li
						class="font-semibold"
						v-for="server in $resources.activeServers.data"
					>
						{{ server.title }} - {{ server.name }}
					</li>
				</ul>
			</div>
		</template>
		<template #actions>
			<Button variant="solid" class="w-full" @click="redirectToServer"
				>Drop Servers</Button
			>
		</template>
	</Dialog>
</template>
<script>
export default {
	name: 'ActiveServersDialog',
	data() {
		return {
			showDialog: true
		};
	},
	resources: {
		activeServers: {
			url: 'press.api.account.active_servers',
			auto: true
		}
	},
	methods: {
		redirectToServer() {
			window.location = '/servers';
		}
	}
};
</script>
