<template>
	<Dialog :options="{ title: 'Drop Active Servers' }" v-model="showDialog">
		<template #body-content>
			<div class="prose text-base">
				Please drop the following active servers before disabling the account:
				<ul class="pt-2">
					<li v-for="server in $resources.activeServers.data">
						<a
							class="cursor-pointer font-semibold"
							@click="openServer(server.name)"
							>{{ server.title ? `${server.title} - ` : '' }}{{ server.name }}</a
						>
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
import router from '../router';

export default {
	name: 'ActiveServersDialog',
	data() {
		return {
			showDialog: true,
		};
	},
	resources: {
		activeServers: {
			url: 'press.api.account.active_servers',
			auto: true,
		},
	},
	methods: {
		redirectToServer() {
			this.showDialog = false;
			router.push({ name: 'Server List' });
		},
		openServer(name) {
			this.showDialog = false;
			router.push({ name: 'Server Detail', params: { name } });
		},
	},
};
</script>
