<template>
	<div
		class="text-sm cursor-pointer w-fit mb-4"
		v-on:click="$emit('update:step', 1)"
	>
		← Back to Apps
	</div>
	<div class="text-center">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width="48"
			height="48"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			class="feather feather-mail mx-auto mb-6"
		>
			<path
				d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"
			></path>
			<polyline points="22,6 12,13 2,6"></polyline>
		</svg>
		<h2 class="font-size-base mt-0">Verification Email Sent!</h2>
		<span class="text-base">
			We have sent an email to <span class="font-semibold">{{ email }}</span
			>. Please click on the link received to verify your login request.
		</span>
	</div>
</template>

<script>
export default {
	name: 'CheckoutConfirmEmail',
	props: ['email', 'step'],
	emits: ['update:step']
};
</script>
