<template>
	<Card
		title="Code Server Info"
		subtitle="General information about your code server"
	>
		<div class="divide-y">
			<ListItem
				title="Bench Version"
				description="Bench version for which this code server is created"
			>
				<template v-slot:actions>
					<router-link
						:to="`/benches/${codeServer.group}/versions/${codeServer.bench}`"
						class="text-base text-blue-600"
					>
						{{ codeServer.bench }} →
					</router-link>
				</template>
			</ListItem>
			<ListItem
				v-if="codeServer.status === 'Running'"
				title="Copy Password"
				description="Copy the password for your code server"
			>
				<template v-slot:actions>
					<Button @click="$resources.showPassword.submit()" class="shrink-0">
						Copy
					</Button>
				</template>
			</ListItem>

			<ListItem
				v-if="codeServer.status === 'Running'"
				title="Stop Code Server"
				description="The code server will go inactive and won't be publicly accessible"
			>
				<template v-slot:actions>
					<Button @click="$resources.stopCodeServer.submit()" class="shrink-0">
						Stop
					</Button>
				</template>
			</ListItem>

			<ListItem
				v-if="codeServer.status === 'Stopped'"
				title="Start Code Server"
				description="The code server will go active and will be publicly accessible"
			>
				<template v-slot:actions>
					<Button @click="$resources.startCodeServer.submit()" class="shrink-0">
						Start
					</Button>
				</template>
			</ListItem>

			<ListItem
				v-if="codeServer.status !== 'Pending'"
				title="Drop Code Server"
				description="Once you drop your code server, there is no going back"
			>
				<template v-slot:actions>
					<Button @click="showDialog = true">
						<span class="text-red-600">Drop</span>
					</Button>
				</template>
			</ListItem>

			<Dialog
				v-model="showDialog"
				:options="{
					title: 'Drop Code Server',
					actions: [
						{
							label: 'Drop Code Server',
							variant: 'solid',
							theme: 'red',
							onClick: () => $resources.dropCodeServer.submit()
						}
					]
				}"
			>
				<template v-slot:body-content>
					<p class="text-base">
						Are you sure you want to drop your code-server? Once you drop your
						code-server, there is no going back.
					</p>
					<ErrorMessage
						class="mt-2"
						:message="$resources.dropCodeServer.error"
					/>
				</template>
			</Dialog>
		</div>
	</Card>
</template>

<script>
export default {
	name: 'CodeServerOverviewInfo',
	props: {
		codeServer: {
			type: Object,
			default: () => {}
		}
	},
	data() {
		return {
			showDialog: false
		};
	},
	resources: {
		stopCodeServer() {
			return {
				method: 'press.api.spaces.stop_code_server',
				params: {
					name: this.codeServer.name
				},
				onSuccess(r) {
					this.$router.push(`/codeservers/${this.codeServer.name}/jobs`);
				}
			};
		},
		startCodeServer() {
			return {
				method: 'press.api.spaces.start_code_server',
				params: {
					name: this.codeServer.name
				},
				onSuccess(r) {
					this.$router.push(`/codeservers/${this.codeServer.name}/jobs`);
				}
			};
		},
		showPassword() {
			return {
				method: 'press.api.spaces.code_server_password',
				params: {
					name: this.codeServer.name
				},
				onSuccess(r) {
					const clipboard = window.navigator.clipboard;
					clipboard.writeText(r).then(() => {
						this.$notify({
							title: 'Password copied to clipboard!',
							icon: 'check',
							color: 'green'
						});
					});
				}
			};
		},
		dropCodeServer() {
			return {
				method: 'press.api.spaces.drop_code_server',
				params: {
					name: this.codeServer.name
				},
				onSuccess() {
					this.$router.push('/spaces');
				}
			};
		}
	}
};
</script>
