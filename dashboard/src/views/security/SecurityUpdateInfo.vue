<template>
	<CardDetails :showDetails="showDetails">
		<div class="px-6 py-5">
			<template v-if="showDetails">
				<!-- <summary
					class="inline-flex w-full items-center py-2 focus:outline-none"
				> -->
				<div class="flex items-center">
					<div>
						<h4 class="text-lg font-medium">
							Package Name: {{ secUpdateInfo.package }}
						</h4>
						<p class="mt-1 text-sm text-gray-600">
							Version: {{ secUpdateInfo.version }}
						</p>
					</div>
				</div>

				<div class="mt-10">
					<div>
						<h4 class="text-lg font-medium">Package Meta</h4>

						<div
							class="rounded-md bg-gray-100 px-2 py-2.5 font-mono text-xs text-gray-900 overflow-auto mt-2"
							:style="{
								width: viewportWidth < 768 ? 'calc(100vw - 6rem)' : ''
							}"
						>
							<div class="max-w-md">
								<pre>{{ secUpdateInfo.package_meta || 'No output' }}</pre>
							</div>
						</div>
					</div>
				</div>
				<!-- </summary> -->
			</template>
			<div v-else>
				<LoadingText v-if="loading" />
				<span v-else class="text-base text-gray-600"> No item selected </span>
			</div>
		</div>
	</CardDetails>
</template>
<script>
import CardDetails from '@/components/CardDetails.vue';

export default {
	name: 'SecurityUpdateInfo',
	props: ['updateId', 'showDetails'],
	inject: ['viewportWidth'],
	components: {
		CardDetails
	},
	resources: {
		secUpdateInfo() {
			return {
				method: 'press.api.security.get_security_update_details',
				params: { update_id: this.updateId },
				keepData: true,
				auto: true
			};
		}
	},
	computed: {
		secUpdateInfo() {
			return this.$resources.secUpdateInfo.data;
		}
	}
};
</script>
