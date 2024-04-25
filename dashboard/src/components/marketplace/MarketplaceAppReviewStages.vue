<template>
	<CardWithDetails
		v-if="reviewStages"
		title="Review Steps"
		:subtitle="
			app.review_stage === 'Not Started'
				? 'Complete all the steps before submitting for a review'
				: 'App is sent for review'
		"
	>
		<ListItem v-for="step in reviewStages" :key="step.step" :title="step.step">
			<template #actions>
				<GreenCheckIcon v-if="step.completed" class="h-5 w-5" />
				<GrayCheckIcon v-else class="h-5 w-5" />
			</template>
		</ListItem>
		<template #actions>
			<Button
				v-if="app.status === 'Draft' && app.review_stage === 'Not Started'"
				:disabled="reviewStages.some(step => !step.completed)"
				:loading="$resources.startReview.isLoading"
				@click="$resources.startReview.submit()"
				class="py-5"
			>
				Submit for Review
			</Button>
		</template>
		<template #details>
			<CardDetails>
				<div class="h-full px-6 py-5">
					<div class="flex justify-between">
						<div>
							<h2 class="text-xl font-semibold">Review Communication</h2>
							<p class="mt-1.5 text-base text-gray-600">
								Chat with the developer assigned for review
							</p>
						</div>

						<div>
							<Button @click="showReplyDialog = true"> Reply </Button>
						</div>
					</div>
					<div class="mt-4 h-full overflow-auto py-5">
						<div
							v-for="message in communication"
							class="mb-4 overflow-auto rounded-lg bg-gray-50 p-4"
						>
							<div class="flex justify-between">
								<div class="flex pb-4">
									<Avatar
										class="mr-2"
										:label="message.sender"
										:image="message.user_image"
									/>
									<span class="self-center text-lg font-semibold">{{
										message.sender
									}}</span>
								</div>
								<span class="text-base text-gray-600">{{
									getFormattedDateTime(message.communication_date)
								}}</span>
							</div>
							<div class="text-base" v-html="message.content"></div>
						</div>
					</div>
				</div>
			</CardDetails>
		</template>
	</CardWithDetails>
	<Dialog
		v-model="showReplyDialog"
		:options="{
			title: 'Reply',
			actions: [
				{
					label: 'Send',
					variant: 'solid',
					onClick: () => $resources.addReply.submit()
				}
			]
		}"
	>
		<template v-slot:body-content>
			<FormControl label="Message" v-model="message" type="textarea" required />
		</template>
	</Dialog>
</template>

<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import CardDetails from '@/components/CardDetails.vue';
import { notify } from '@/utils/toast';

export default {
	name: 'MarketplaceAppReviewStages',
	components: { CardWithDetails, CardDetails },
	props: ['appName', 'app', 'reviewStages'],
	data() {
		return {
			showReplyDialog: false,
			message: null
		};
	},
	methods: {
		getFormattedDateTime(time) {
			const date = new Date(time);
			return date.toLocaleString(undefined, {
				dateStyle: 'medium',
				timeStyle: 'short'
			});
		}
	},
	resources: {
		startReview() {
			return {
				url: 'press.api.marketplace.mark_app_ready_for_review',
				params: {
					name: this.appName
				},
				onSuccess() {
					window.location.reload();
				}
			};
		},
		communication() {
			return {
				url: 'press.api.marketplace.communication',
				params: {
					name: this.appName
				}
			};
		},
		addReply() {
			return {
				url: 'press.api.marketplace.add_reply',
				params: {
					name: this.appName,
					message: this.message
				},
				onSuccess() {
					this.showReplyDialog = false;
					notify({
						title: 'Reply Queued',
						message: 'Message reply is queued for sending',
						icon: 'check',
						color: 'green'
					});
				}
			};
		}
	},
	mounted() {
		this.$resources.communication.submit();
	},
	computed: {
		communication() {
			return this.$resources.communication.data;
		}
	}
};
</script>
