<template>
	<div class="mt-8 flex-1">
		<div class="flex items-center justify-between pb-4">
			<h3 class="text-xl font-bold">Apps</h3>
			<Button type="primary" iconLeft="plus"> Add App </Button>
		</div>
		<div
			class="py-2 px-2 sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow"
		>
			<div
				class="py-2 text-base text-gray-600 sm:px-2"
				v-if="apps.length === 0"
			>
				No apps.
			</div>

			<div class="py-2" v-for="app in apps" :key="app.name">
				<router-link
					:to="`/saas/manage/${app.name}/overview`"
					class="block rounded-md py-2 hover:bg-gray-50 sm:px-2"
				>
					<div class="flex items-center justify-between sm:justify-start">
						<div class="text-base sm:w-4/12">
							{{ app.title }}
						</div>
						<div class="text-base sm:w-4/12">
							<Badge class="pointer-events-none" v-bind="appBadge(app)" />
						</div>
						<div class="text-right text-base sm:w-4/12">
							{{ app.count }} sites
						</div>

						<!-- <div class="hidden w-2/12 text-right text-base sm:block">
							SomeStat
						</div> -->
					</div>
				</router-link>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'SaasManage',
	data() {
		return {
			apps: []
		};
	},
	methods: {
		appBadge(app) {
			let status = app.status;
			let color = app.status == 'Draft' ? 'yellow' : 'green';

			return {
				color,
				status
			};
		}
	},
	resources: {
		apps: {
			method: 'press.api.saas.get_apps',
			auto: true,
			onSuccess(r) {
				this.apps = r;
			}
		}
	}
};
</script>
