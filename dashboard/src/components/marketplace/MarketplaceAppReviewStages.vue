<template>
	<CardWithDetails
		v-if="reviewStages"
		title="Review Steps"
		subtitle="Complete all the steps before submitting for a review"
	>
		<ListItem
			v-for="step in steps"
			:key="step.key"
			:title="step.title"
			:subtitle="step.description"
		>
			<template #actions>
				<GreenCheckIcon v-if="reviewStages[step.key]" class="h-5 w-5" />
				<GrayCheckIcon v-else class="h-5 w-5" />
			</template>
		</ListItem>
		<template #actions>
			<Button v-if="showButton()" @click="$resources.startReview.submit()">
				Ready for Review
			</Button>
		</template>
		<template #details>
			<CardDetails>
				<div class="px-6 py-5 h-full">
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
					<div class="overflow-auto h-full py-5 mt-4">
						<div
							v-for="message in communication"
							class="overflow-auto p-4 mb-4 rounded-lg bg-gray-50"
						>
							<div class="flex justify-between">
								<div class="flex pb-4">
									<Avatar
										class="mr-2"
										:label="message.sender"
										:imageURL="message.user_image"
									/>
									<span class="text-lg font-semibold self-center">{{
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
			<Input label="Message" v-model="message" type="textarea" required />
		</template>
	</Dialog>
</template>

<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import CardDetails from '@/components/CardDetails.vue';

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
		showButton() {
			return (
				!Object.values(this.reviewStages).some(val => val === false) &&
				this.app.status === 'Draft'
			);
		},
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
				method: 'press.api.marketplace.start_review',
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
				method: 'press.api.marketplace.communication',
				params: {
					name: this.appName
				}
			};
		},
		addReply() {
			return {
				method: 'press.api.marketplace.add_reply',
				params: {
					name: this.appName,
					message: this.message
				},
				onSuccess() {
					this.showReplyDialog = false;
					this.$notify({
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
		steps() {
			return [
				{
					key: 'logo',
					title: 'Add a Logo',
					description: "Make sure it's atleast 300x300 in dimension"
				},
				{
					key: 'description',
					title: 'Add Description',
					description: 'Add Short and Long description for your app'
				},
				{
					key: 'links',
					title: 'Add Links',
					description: 'Make sure you add all the links for your app'
				},
				{
					key: 'publish',
					title: 'Publish a Release',
					description: 'Publish your first release from the Releases tab'
				}
			];
		},
		communication() {
			return this.$resources.communication.data;
		}
	}
};
</script>
