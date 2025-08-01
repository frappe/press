<template>
	<div class="mx-auto mt-12 max-w-xl px-5 text-base sm:px-8">
		<div v-if="$app" class="mb-4 flex items-center space-x-4">
			<img
				:src="$app.image"
				class="h-12 w-12 rounded-lg border"
				:alt="$app.name"
			/>
			<h1 class="text-xl font-semibold">
				{{ $app.title }}
			</h1>
		</div>

		<div>
			<FormControl v-model="reply.reply" type="textarea" label="Write Reply" />

			<ErrorMessage class="mt-2" :message="$resources.submitReply.error" />
			<Button
				class="mt-4 w-full"
				:loading="$resources.submitReply.loading"
				variant="solid"
				@click="$resources.submitReply.submit({ ...reply })"
			>
				Submit
			</Button>
		</div>
	</div>
</template>

<script>
import { getTeam } from '../../data/team';
import { getDocResource } from '../../utils/resource';
import { DashboardError } from '../../utils/error';

export default {
	props: {
		marketplaceApp: { type: String, required: true },
		reviewId: { type: String, required: true },
	},
	data() {
		return {
			reply: {
				review: this.reviewId,
				reply: '',
			},
		};
	},
	computed: {
		$app() {
			let appDoc = getDocResource({
				doctype: 'Marketplace App',
				name: this.marketplaceApp,
			});

			return appDoc?.doc;
		},
	},
	resources: {
		submitReply: {
			url: 'press.api.marketplace.submit_developer_reply',
			validate() {
				if (!this.reply.reply) {
					throw new DashboardError('Reply cannot be empty');
				}
				const team = getTeam();
				if (!team.doc.is_developer) {
					throw new DashboardError(
						'You must be a developer to reply to reviews',
					);
				}
			},
			onSuccess() {
				window.location.href = `/marketplace/apps/${this.marketplaceApp}`;
			},
		},
	},
};
</script>
