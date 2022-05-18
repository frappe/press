<script setup>
import { reactive } from 'vue';
import useResource from '@/composables/resource';
import StarRatingInput from '@/components/StarRatingInput.vue';

const props = defineProps({
	marketplaceApp: String
});

const review = reactive({
	app: props.marketplaceApp,
	title: '',
	rating: 5,
	review: ''
});

const submitReview = useResource({
	method: 'press.api.marketplace.submit_user_review',
	validate() {
		if (!review.title) {
			return 'Please add a title to your review';
		}

		if (!review.review) {
			return 'Review cannot be empty';
		}
	},
	onSuccess() {
		window.location.href = `/marketplace/apps/${props.marketplaceApp}`;
	}
});
</script>

<template>
	<div class="px-4 py-4 text-base sm:px-8">
		<div>
			<h1 class="mb-4 text-xl font-semibold">
				Review App: {{ props.marketplaceApp }}
			</h1>
		</div>

		<div class="mt-2 sm:grid sm:grid-cols-2">
			<div>
				<div class="mb-3">
					<span class="mb-2 block text-sm leading-4 text-gray-700">
						Rating
					</span>
					<StarRatingInput v-model="review.rating" />
				</div>

				<Input
					class="mb-3"
					v-model="review.title"
					type="text"
					label="Title"
					placeholder="Review Title"
				/>

				<Input
					v-model="review.review"
					type="textarea"
					label="Review this product"
					placeholder="Write Review"
				/>

				<ErrorMessage class="mt-2" :error="submitReview.error" />
				<Button
					class="mt-4"
					:loading="submitReview.loading"
					type="primary"
					@click="submitReview.submit({ ...review })"
					>Submit</Button
				>
			</div>
		</div>
	</div>
</template>
