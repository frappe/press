<template>
	<div class="pb-10 sm:mt-5">
		<div class="sm:px-8">
			<div
				class="mx-auto mb-20 w-auto space-y-8 rounded-lg p-4 sm:w-wizard sm:border sm:p-8 sm:shadow-md"
			>
				<slot />
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'WizardCard'
};
</script>
