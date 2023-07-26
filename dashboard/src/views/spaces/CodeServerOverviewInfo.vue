<template>
	<Card
		title="Code Server info"
		subtitle="General information about your code server"
	>
		<div class="divide-y">
			<ListItem
				v-if="codeServer.status === 'Running'"
				title="Show Password"
				description="The password for your code server"
			>
				<template v-slot:actions>
					<Button @click="" class="shrink-0"> Show </Button>
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
					<Button @click="showDialog">
						<span class="text-red-600">Drop</span>
					</Button>
				</template>
			</ListItem>
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
		}
	}
};
</script>
