<template>
	<div class="relative flex h-full flex-col">
		<div class="h-full flex-1">
			<div class="flex h-full">
				<div
					class="relative block min-h-0 flex-shrink-0 overflow-hidden hover:overflow-auto"
				>
					<AppSidebar />
				</div>
				<div class="w-full overflow-auto" id="scrollContainer">
					<router-view v-if="$session.user" />
					<div v-else class="py-20 text-center text-base">
						You are not logged in.
						<a href="/login" class="underline">Login</a> to access dashboard.
					</div>
				</div>
			</div>
		</div>
		<Toaster position="top-right" />
	</div>
</template>

<script setup>
import { Toaster } from 'vue-sonner';
</script>

<style src="../src/assets/style.css"></style>
