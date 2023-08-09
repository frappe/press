<template>
	<CardDetails :showDetails="showDetails">
		<div class="px-6 py-5">
			<template v-if="showDetails">
				<div class="flex justify-between items-center">
					<div>
						<h4 class="text-lg font-medium">
							Package: {{ secUpdateInfo.package }}
						</h4>
						<p class="mt-1 text-sm text-gray-600">
							Version: {{ secUpdateInfo.version }}
						</p>
					</div>
					<div class="justify-end">
						<Badge
							class="pointer-events-none"
							variant="subtle"
							size="lg"
							:label="secUpdateInfo.priority"
							:theme="getColor(secUpdateInfo.priority)"
						/>
					</div>
				</div>
			</template>
			<div v-else>
				<LoadingText v-if="loading" />
				<span v-else class="text-base text-gray-600"> No item selected </span>
			</div>
		</div>
		<div class="flex-auto px-6 overflow-auto" v-if="showDetails">
			<InfoSection
				sectionName="Package Meta"
				:sectionData="secUpdateInfo.package_meta"
			/>
			<InfoSection
				sectionName="Change Log"
				:sectionData="secUpdateInfo.change_log"
			/>
		</div>
	</CardDetails>
</template>
<script>
import CardDetails from '@/components/CardDetails.vue';
import InfoSection from './InfoSection.vue';

export default {
	name: 'SecurityUpdateInfo',
	props: ['updateId', 'showDetails'],
	inject: ['viewportWidth'],
	components: {
		CardDetails,
		InfoSection
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
	},
	methods: {
		getColor(priority) {
			switch (priority) {
				case 'High':
					return 'red';
				case 'Medium':
					return 'orange';
				case 'Low':
					return 'green';
				default:
					return 'gray';
			}
		}
	}
};
</script>
