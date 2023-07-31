<script setup>
import { reactive } from 'vue';
import useResource from '@/composables/resource';
import StarRatingInput from '@/components/StarRatingInput.vue';

const props = defineProps({
	marketplaceApp: String,
	reviewId: String
});

const params = new Proxy(new URLSearchParams(window.location.search), {
	get: (searchParams, prop) => searchParams.get(prop)
});
let appTitle = params.title;

const reply = reactive({
	review: props.reviewId,
	reply: ''
});

const submitReply = useResource({
	method: 'press.api.marketplace.submit_developer_reply',
	validate() {
		if (!reply.reply) {
			return 'Reply cannot be empty';
		}
		if (!$account.team.is_developer) {
			return 'You must be a developer to reply to reviews';
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
			<h1 class="mb-4 text-xl font-semibold">Reply App: {{ appTitle }}</h1>
		</div>

		<div class="mt-2 sm:grid sm:grid-cols-2">
			<div>
				<Input v-model="reply.reply" type="textarea" label="Write Reply" />

				<ErrorMessage class="mt-2" :message="submitReply.error" />
				<Button
					class="mt-4"
					:loading="submitReply.loading"
					appearance="primary"
					@click="submitReply.submit({ ...reply })"
					>Submit</Button
				>
			</div>
		</div>
	</div>
</template>
