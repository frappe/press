<template>
	<div>
		<Button
			v-if="$resources.apps.loading"
			:loading="true"
			loadingText="Loading..."
		></Button>
		<ErrorMessage
			v-else-if="!$resources.apps.data"
			:error="$resources.apps.error"
		/>
		<div v-else-if="$resources.apps.data.length < 1">
			<p class="text-gray-600 text-lg">
				You have not published any app on our Marketplace.
			</p>
		</div>
		<div v-else>
			<div class="grid gap-4 grid-cols-1 md:grid-cols-3 ">
				<SelectableCard
					v-for="app in $resources.apps.data"
					:title="app.title"
					:key="app.name"
					:image="app.image"
					@click.native="routeToAppPage(app.name)"
				>
					<template #secondary-content>
						<span class="text-base text-gray-600">
							{{ app.description }}
						</span>
					</template>
				</SelectableCard>
			</div>
		</div>
	</div>
</template>

<script>
import SelectableCard from '@/components/SelectableCard.vue';

export default {
	name: 'DeveloperApps',
	components: {
		SelectableCard
	},
	resources: {
		apps() {
			return {
				method: 'press.api.marketplace.get_apps',
				auto: true
			};
		}
	},
	methods: {
		routeToAppPage(appName) {
			this.$router.push(`/developer/apps/${appName}`);
		}
	}
};
</script>
