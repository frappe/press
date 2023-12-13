<template>
	<div class="relative flex h-full flex-col">
		<div class="h-full flex-1">
			<div class="flex h-full">
				<div
					class="relative block min-h-0 flex-shrink-0 overflow-hidden hover:overflow-auto"
				>
					<AppSidebar v-if="$session.user" />
				</div>
				<div class="w-full overflow-auto" id="scrollContainer">
					<div
						v-if="!$session.user && !$route.meta.isLoginPage"
						class="border bg-red-200 px-5 py-3 text-base text-red-900"
					>
						You are not logged in.
						<router-link to="/login" class="underline">Login</router-link> to
						access dashboard.
					</div>
					<router-view />
				</div>
			</div>
		</div>
		<Toaster position="top-right" />
		<component v-for="dialog in dialogs" :is="dialog" :key="dialog.id" />
	</div>
</template>

<script setup>
import { Toaster } from 'vue-sonner';
import { dialogs } from './utils/components';
import AppSidebar from './components/AppSidebar.vue';
</script>

<style src="../src/assets/style.css"></style>
