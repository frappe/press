<template>
	<Dialog
		:options="{
			title: 'App Versions',
			size: '2xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<div
				v-if="$resources?.deployedAppVersions?.loading"
				class="flex h-80 w-full items-center justify-center gap-2 text-base text-gray-700"
			>
				<Spinner class="w-4" /> Fetching app versions ...
			</div>
			<div
				v-else-if="$resources?.deployedAppVersions?.error"
				class="flex h-80 w-full items-center justify-center text-red-600"
			>
				Failed to fetch app versions
			</div>
			<Button
				variant="solid"
				iconLeft="trash-2"
				theme="red"
				@click="onCleanup()"
				class="w-full rounded"
			>
				Redeploy
			</Button>
		</template>
	</Dialog>
</template>

<script>
import { Spinner } from 'frappe-ui';

export default {
	name: 'RedeployDialog',
	props: ['dc_name'],
	components: { Spinner },
	data() {
		return {
			show: true,
		};
	},
	resources: {
		deployedAppVersions() {
			return {
				url: 'press.api.bench.show_app_versions',
				makeParams: () => {
					return {
						name: this.dc_name,
					};
				},
				auto: false,
			};
		},
	},
	methods: {
		onRedeploy() {
			console.log('Redeploying!');
		},
	},
};
</script>
