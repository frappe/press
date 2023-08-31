<template>
	<CardDetails :showDetails="showDetails">
		<div class="px-6 py-5">
			<template v-if="showDetails">
				<div class="flex items-center justify-between">
					<div>
						<h4 class="text-lg font-medium">
							Session: {{ SSHActivity.session_id }}
						</h4>
					</div>
					<div class="justify-end">
						<Badge
							class="pointer-events-none"
							variant="subtle"
							size="lg"
							:label="getLabel(SSHActivity.session_user)"
							:theme="getColor(SSHActivity.session_user)"
						/>
					</div>
				</div>
			</template>
			<div v-else>
				<LoadingText v-if="loading" />
				<span v-else class="text-center text-base text-gray-600">
					No item selected
				</span>
			</div>
		</div>
		<div class="flex-auto overflow-auto px-6" v-if="showDetails">
			<InfoSection
				sectionName="Activity"
				:sectionData="SSHActivity.content"
				:defaultOpen="true"
			/>
		</div>
	</CardDetails>
</template>

<script>
import CardDetails from '@/components/CardDetails.vue';
import InfoSection from './InfoSection.vue';

export default {
	name: 'SSHSessionActivity',
	props: ['showDetails', 'logId', 'server'],
	components: { CardDetails, InfoSection },
	inject: ['viewportWidth'],
	resources: {
		SSHActivity() {
			return {
				url: 'press.api.security.fetch_ssh_session_activity',
				params: {
					server: this.server?.name,
					filename: this.logId
				},
				auto: true
			};
		}
	},
	computed: {
		SSHActivity() {
			return this.$resources.SSHActivity.data;
		}
	},
	methods: {
		getLabel(user) {
			return `User: ${user}`;
		},
		getColor(user) {
			return user === 'root' ? 'red' : 'green';
		}
	}
};
</script>
