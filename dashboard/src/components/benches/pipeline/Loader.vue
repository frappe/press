<template>
	<div class="sk-fade flex flex-col gap-4 p-3 md:px-5 w-full md:mt-1.5">
		<div class="flex gap-2 items-center">
			<div class="sk size-7" />
			<div class="sk h-7 w-44" />
			<div class="sk h-7 w-16 mr-auto" />
			<div class="sk h-7 w-20 hidden md:block" />
			<div class="sk size-7" />
		</div>

		<section class="grid grid-cols-2 md:grid-cols-4 gap-3">
			<div
				v-for="i in 4"
				:key="i"
				class="border rounded p-3 flex flex-col gap-1.5"
			>
				<div class="sk h-3 w-14" />
				<div class="sk h-3.5 w-24" />
			</div>
		</section>

		<div
			class="flex flex-col md:flex-row rounded border p-3 pt-0.5 gap-3 min-h-0 md:h-[calc(100dvh-18rem)]"
		>
			<div class="w-full md:w-[30rem] shrink-0 flex flex-col py-3">
				<div class="flex gap-4 pb-3 mb-1 border-b">
					<div class="sk h-5 w-16" />
					<div class="sk h-5 w-16" />
				</div>

				<div
					v-for="i in 4"
					:key="i"
					class="flex items-center gap-3 py-3 border-b border-surface-gray-2 last:border-b-0"
				>
					<div class="sk size-4 shrink-0" />

					<div
						class="sk h-3.5"
						:style="{ width: ['55%','70%','45%','60%'][i - 1] }"
					/>

					<div class="flex-1" />

					<div class="sk size-4 !rounded-sm" />
				</div>
			</div>

			<div
				class="flex-1 bg-surface-gray-1 dark:bg-surface-elevation-1 rounded p-3 hidden md:flex flex-col gap-3 mt-1"
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
	animation: sk-fade-in 0.25s ease-out both;
}

@keyframes sk-fade-in {
	from {
		opacity: 0;
	}
	to {
		opacity: 1;
	}
}
</style>
