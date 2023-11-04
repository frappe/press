<template>
	<div class="h-full pt-4 sm:pt-16">
		<div class="relative z-10">
			<div class="flex">
				<slot name="logo">
					<FCLogo
						class="mx-auto inline-block h-12"
						@dblclick="redirectForFrappeioAuth"
					/>
				</slot>
			</div>
			<div
				class="mx-auto bg-white px-4 py-8 sm:mt-6 sm:w-96 sm:rounded-lg sm:px-8 sm:shadow-xl"
			>
				<div class="mb-6 text-center" v-if="title">
					<span class="text-base text-gray-900">{{ title }}</span>
				</div>
				<slot></slot>
			</div>
		</div>
		<div class="fixed bottom-4 z-[1] flex w-full justify-center">
			<FrappeLogo class="h-4" />
		</div>
	</div>
</template>

<script>
import FCLogo from '@/components/icons/FCLogo.vue';
import FrappeLogo from '@/components/icons/FrappeLogo.vue';
import { notify } from '@/utils/toast';

export default {
	name: 'LoginBox',
	props: ['title', 'logo'],
	components: {
		FCLogo,
		FrappeLogo
	},
	mounted() {
		const params = new URLSearchParams(window.location.search);

		if (params.get('showRemoteLoginError')) {
			notify({
				title: 'Token Invalid or Expired',
				color: 'red',
				icon: 'x'
			});
		}
	},
	methods: {
		redirectForFrappeioAuth() {
			window.location = '/f-login';
		}
	}
};
</script>
