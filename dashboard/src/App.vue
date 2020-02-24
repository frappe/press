<template>
    <div>
        <div class="flex h-screen overflow-hidden font-sans text-gray-900 antialiased">
            <Sidebar class="w-56 flex-shrink-0" v-if="$store.auth.isLoggedIn" />
            <div class="flex-1">
                <router-view />
            </div>
        </div>
        <portal-target name="popovers" multiple></portal-target>
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
