<template>
	<div class="sm:mt-5">
		<div class="sm:px-8">
			<div
				class="w-auto p-4 mx-auto mb-20 space-y-8 rounded-lg sm:shadow-md sm:p-8 sm:border sm:w-wizard"
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
