<template>
	<section
		class="sk-fade border rounded shadow-sm overflow-hidden  bg-surface-cards"
		v-for="_ in 3"
	>
		<div class="flex gap-3 items-center p-4">
			<div class="sk size-8 !rounded" />
			<div class="flex flex-col gap-1.5">
				<div class="flex gap-2 items-center">
					<div class="sk h-4 w-48" />
					<div class="sk h-3 w-3 !rounded-full" />
					<div class="sk h-3 w-10" />
				</div>
				<div class="sk h-3 w-36" />
			</div>
			<div class="flex items-center gap-2 ml-auto">
				<div class="sk h-4 w-4" />
				<div class="sk h-4 w-20" />
				<div class="sk h-7 w-7" />
			</div>
		</div>

		<div
			v-for="(bench, i) in 3"
			:key="bench"
			class="grid grid-cols-[1.5rem_1fr_0.5fr_0.7fr_2rem] gap-3 px-4 py-2.5 items-center border-t"
		>
			<div class="sk h-4 w-4" />
			<div class="flex gap-2 items-center">
				<div class="sk h-4 w-4" />
				<div class="sk h-4" :style="{ width: ['9rem', '7rem', '11rem'][i] }" />
			</div>
			<div class="flex gap-2 items-center">
				<div class="sk h-2.5 w-2.5 !rounded-full" />
				<div class="sk h-3.5 w-20" />
			</div>
			<div class="sk h-3.5 w-16" />
			<div class="sk h-7 w-7" />
		</div>
	</section>
</template>

<style scoped>
.bordered {
	@apply border-b dark:border-outline-gray-2
}

.sk {
	@apply rounded animate-pulse bg-surface-gray-3 dark:bg-surface-gray-2;
}
.sk-fade {
	animation: sk-fade-in 0.35s cubic-bezier(0.4, 0, 0.2, 1) both;
}
@keyframes sk-fade-in {
	from {
		opacity: 0;
		transform: translateY(5px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}
</style>
