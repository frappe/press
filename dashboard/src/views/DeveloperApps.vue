<template>
	<div>
		<Button
			v-if="$resources.apps.loading"
			:loading="true"
			loadingText="Loading..."
		></Button>
		<div v-else>
			<div class="grid grid-cols-3">
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
				method: 'press.api.developer.get_apps',
				auto: true
			};
		}
	},
	methods: {
		routeToAppPage(appName) {
			this.$router.replace('/developer/profile');
		}
	}
};
</script>
