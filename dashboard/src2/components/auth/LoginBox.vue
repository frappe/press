<template>
	<div class="relative h-full">
		<div class="relative z-10 mx-auto py-8 sm:w-max sm:py-24">
			<div class="flex flex-col px-4" @dblclick="redirectForFrappeioAuth">
				<slot name="logo">
					<div class="flex items-center space-x-2">
						<FCLogo class="inline-block h-[38px] w-[38px]" />
					</div>
				</slot>
			</div>
			<div class="mx-auto w-full bg-white px-4 py-6 sm:w-96 sm:rounded-lg">
				<div class="mb-2" v-if="title">
					<span
						class="text-2xl font-bold leading-5 tracking-tight text-gray-900"
					>
						{{ title }}
					</span>
				</div>
				<p
					class="mb-6 break-words text-base font-normal leading-[21px] text-gray-700"
					v-if="subtitle"
				>
					{{ subtitle }}
				</p>
				<slot></slot>
			</div>
			<slot name="footer"></slot>
		</div>
	</div>
</template>

<script>
import { toast } from 'vue-sonner';
import FCLogo from '@/components/icons/FCLogo.vue';

export default {
	name: 'LoginBox',
	props: ['title', 'logo', 'subtitle'],
	components: {
		FCLogo,
	},
	mounted() {
		const params = new URLSearchParams(window.location.search);

		if (params.get('showRemoteLoginError')) {
			toast.error('Token Invalid or Expired');
		}
	},
	methods: {
		redirectForFrappeioAuth() {
			window.location = '/f-login';
		},
	},
};
</script>
