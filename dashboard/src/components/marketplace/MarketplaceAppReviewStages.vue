<template>
	<Card v-if="reviewStages" title="Review Steps" subtitle="Complete all the steps before submitting for a review">
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
			<Button
				v-if="showButton()"
				@click="$resources.startReview.submit()"
			>
				Ready for Review
			</Button>
		</template>
	</Card>
</template>

<script>
export default {
	name: 'MarketplaceAppReviewStages',
	props: ['appName', 'app', 'reviewStages'],
	methods: {
		showButton() {
			return !Object.values(this.reviewStages).some(val => val === false) && this.app.status === 'Draft'
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
					window.location.reload()
				}
			}
		}
	},
	computed: {
		steps() {
			return [
				{
					'key': 'logo',
					'title': 'Add a Logo',
					'description': "Make sure it's atleast 300x300 in dimension"
				},
				{
					'key': 'description',
					'title': 'Add Description',
					'description': "Add Short and Long description for your app"
				},
				{
					'key': 'links',
					'title': 'Add Links',
					'description': "Make sure you add all the links for your app"
				},
				{
					'key': 'publish',
					'title': 'Publish a Release',
					'description': "Publish your first release from the Releases tab"
				}
			]
		}
	}
}
</script>
