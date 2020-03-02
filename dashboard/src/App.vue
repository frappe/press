<template>
    <div class="font-sans text-gray-900 antialiased">
        <div class="flex h-screen overflow-hidden">
            <Sidebar class="w-64 flex-shrink-0 hidden sm:block" v-if="$store.auth.isLoggedIn" />
            <div class="flex flex-1 overflow-y-auto" :class="{'bg-gray-100': $route.meta.isLoginPage}">
                <div class="flex-1 container mx-auto">
                    <router-view />
                </div>
            </div>
        </div>
        <portal-target name="popovers" multiple></portal-target>
        <portal-target name="modals" multiple></portal-target>
    </div>
</template>
<script>
import Sidebar from "@/components/Sidebar";
export default {
    name: 'App',
    components: {
        Sidebar
    }
};
</script>
<style src="./assets/style.css">
