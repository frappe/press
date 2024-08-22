<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Steps to complete before the app can be published',
			size: '2xl'
		}"
	>
		<template #body-content>
			<div v-if="appDoc.doc.review_stage === 'Ready for Review'">
				<p class="text-p-base text-gray-700">
					Your app is sent for review to our team. Please wait for the review to
					be completed.
				</p>
			</div>
			<ObjectList v-else :options="listOptions" />
		</template>
		<template #actions v-if="appDoc.doc.review_stage !== 'Ready for Review'">
			<Button
				class="w-full"
				variant="solid"
				label="Mark app ready for review"
				:loading="appDoc.markAppReadyForReview.loading"
				:disabled="$resources.reviewSteps.data.some(step => !step.completed)"
				@click="appDoc.markAppReadyForReview.submit"
			/>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import ObjectList from '../ObjectList.vue';

export default {
	props: ['app'],
	components: {
		ObjectList
	},
	data() {
		return {
			show: true
		};
	},
	resources: {
		reviewSteps() {
			return {
				url: 'press.api.marketplace.review_steps',
				params: {
					name: this.app
				},
				cache: ['Marketplace App Review Steps', this.app],
				auto: true,
				initialData: []
			};
		}
	},
	computed: {
		appDoc() {
			return getCachedDocumentResource('Marketplace App', this.app);
		},
		listOptions() {
			return {
				data: () => this.$resources.reviewSteps.data,
				hideControls: true,
				columns: [
					{
						label: 'Step',
						fieldname: 'step'
					},
					{
						label: 'Completed',
						fieldname: 'completed',
						type: 'Icon',
						width: 0.3,
						align: 'center',
						Icon(value) {
							return value ? 'check' : '';
						}
					},
					{
						label: '',
						type: 'Button',
						width: 0.2,
						align: 'right',
						Button: ({ row }) => {
							let route = `/apps/${this.app}/`;
							route += row.step.includes('Publish') ? 'versions' : 'listing';

							return {
								label: 'View',
								variant: 'ghost',
								route
							};
						}
					}
				]
			};
		}
	}
};
</script>
