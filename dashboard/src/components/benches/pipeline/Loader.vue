<template>
	<div class="sk-fade flex flex-col gap-4 py-3 px-5 w-full mt-1.5">
		<div class="flex gap-2 items-center">
			<div class="sk size-7" />
			<div class="sk h-7 w-44" />
			<div class="sk h-7 w-16 !rounded-full mr-auto" />
			<div class="sk h-7 w-20" />
			<div class="sk h-7 w-7" />
		</div>

		<section class="grid grid-cols-4 gap-3">
			<div
				v-for="i in 4"
				:key="i"
				class="border rounded p-4 flex flex-col gap-2"
			>
				<div class="sk h-3 w-16" />
				<div class="sk h-4 w-28" />
			</div>
		</section>

		<div
			class="flex rounded border p-3 pt-1 gap-3 min-h-0"
			style="height: calc(100dvh - 18rem)"
		>
			<div class="w-[30rem] shrink-0 flex flex-col py-3">
				<div class="flex gap-4 pb-3 mb-3 border-b">
					<div class="sk h-5 w-16" />
					<div class="sk h-5 w-16" />
				</div>

				<div
					v-for="i in 4"
					:key="i"
					class="flex items-center gap-2.5 py-3.5 border-b last:border-b-0"
				>
					<div class="sk size-5 !rounded-full shrink-0" />
					<div
						class="sk h-4"
						:style="{ width: ['140px', '170px', '110px', '90px'][i - 1] }"
					/>
					<div class="sk h-4 w-10 !rounded-full ml-auto" />
				</div>
			</div>

			<div
				class="flex-1 bg-surface-gray-1 dark:bg-surface-cards rounded p-3 flex flex-col gap-3 mt-1"
			>
				<div class="flex items-center gap-2 pb-2 border-b">
					<div class="sk h-4 w-12" />
					<div class="sk h-6 w-6 ml-auto" />
					<div class="sk h-6 w-6" />
				</div>
				<div class="sk h-3.5 w-full" />
				<div class="sk h-3.5 w-5/6" />
				<div class="sk h-3.5 w-11/12" />
				<div class="sk h-3.5 w-3/4" />
			</div>
		</div>
	</div>
</template>

<style scoped>
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
