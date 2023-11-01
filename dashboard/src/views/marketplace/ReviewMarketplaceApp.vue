<script setup>
import { reactive } from 'vue';
import { createResource } from 'frappe-ui';
import StarRatingInput from '@/components/StarRatingInput.vue';

const props = defineProps({
	marketplaceApp: String
});

const params = new Proxy(new URLSearchParams(window.location.search), {
	get: (searchParams, prop) => searchParams.get(prop)
});
let appTitle = params.title;

const review = reactive({
	app: props.marketplaceApp,
	title: '',
	rating: 5,
	review: ''
});

const submitReview = createResource({
	url: 'press.api.marketplace.submit_user_review',
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
			<h1 class="mb-4 text-xl font-semibold">Review App: {{ appTitle }}</h1>
		</div>

		<div class="mt-2 sm:grid sm:grid-cols-2">
			<div>
				<div class="mb-3">
					<span class="mb-2 block text-sm leading-4 text-gray-700">
						Rating
					</span>
					<StarRatingInput v-model="review.rating" />
				</div>

				<FormControl
					class="mb-3"
					v-model="review.title"
					label="Title"
					placeholder="Review Title"
				/>

				<FormControl
					v-model="review.review"
					type="textarea"
					label="Review this product"
					placeholder="Write Review"
				/>

				<ErrorMessage class="mt-2" :message="submitReview.error" />
				<Button
					class="mt-4 w-full"
					:loading="submitReview.loading"
					variant="solid"
					@click="submitReview.submit({ ...review })"
					>Submit</Button
				>
			</div>
		</div>
	</div>
</template>
