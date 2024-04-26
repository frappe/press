<template>
	<Dialog v-if="doc" v-model="show">
		<!-- Title -->
		<template v-slot:body-title>
			<h1 class="font-semibold">
				{{ doc.title }}
			</h1>
		</template>

		<!-- Message and Traceback -->
		<template v-slot:body-content>
			<div
				:if="doc.message"
				v-html="doc.message"
				class="flex flex-col gap-2 whitespace-pre-wrap text-p-base text-gray-700"
			></div>

			<div v-if="doc.traceback" class="relative mt-6">
				<button
					class="absolute right-2 top-2 rounded-sm border border-gray-200 bg-white p-1 text-xs text-gray-600"
					variant="outline"
					@click="copyTraceback"
				>
					{{ copied ? 'copied' : 'copy' }}
				</button>
				<div
					class="max-h-48 w-full overflow-scroll rounded-sm border border-gray-200 bg-gray-100 p-3 text-xs text-gray-600"
				>
					<pre>{{ doc.traceback }}</pre>
				</div>
			</div>

			<ErrorMessage :message="error" class="mt-2"></ErrorMessage>
		</template>

		<!-- Help and Done -->
		<template v-slot:actions>
			<div class="flex justify-end gap-5">
				<Link v-if="doc.assistance_url" class="cursor-pointer" @click="help">
					Help
				</Link>

				<Button
					v-if="!doc.is_addressed"
					variant="solid"
					class="w-40"
					@click="done"
				>
					Done
				</Button>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { Button, Dialog, FeatherIcon } from 'frappe-ui';
import ErrorMessage from 'frappe-ui/src/components/ErrorMessage.vue';

export default {
	props: {
		name: String
	},
	components: {
		Dialog,
		Button,
		FeatherIcon
	},
	emits: ['done'],
	data() {
		return {
			helpViewed: false,
			show: true,
			copied: false,
			error: ''
		};
	},
	resources: {
		notification() {
			return {
				type: 'document',
				doctype: 'Press Notification',
				name: this.name,
				whitelistedMethods: {
					markAsAddressed: 'mark_as_addressed'
				}
			};
		}
	},
	computed: {
		doc() {
			return this.$resources.notification.doc ?? null;
		}
	},
	methods: {
		async copyTraceback() {
			await navigator.clipboard.writeText(this.doc.traceback);
			this.copied = true;
			setTimeout(() => (this.copied = false), 4000);
		},
		async done() {
			if (this.doc.assistance_url && !this.helpViewed) {
				this.error =
					'Please follow the steps mentioned in <i>Help</i> before clicking Done';
				return;
			}

			await this.$resources.notification.markAsAddressed.submit();
			this.show = false;
			this.$emit('done');
		},
		help() {
			this.error = '';
			this.helpViewed = true;
			window.open(this.doc.assistance_url, '_blank');
		}
	}
};
</script>
