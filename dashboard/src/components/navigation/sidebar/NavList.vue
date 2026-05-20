<script setup lang="ts">
import { computed, getCurrentInstance, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { unreadNotificationsCount } from "@/data/notifications";
import { session } from "@/data/session";
import { getTeam } from "@/data/team";
import Activity from "~icons/lucide/activity";
import Boxes from "~icons/lucide/boxes";
import Code from "~icons/lucide/code";
import DatabaseZap from "~icons/lucide/database-zap";
import DoorOpen from "~icons/lucide/door-open";
import FileSearch from "~icons/lucide/file-search";
import Globe from "~icons/lucide/globe";
import App from "~icons/lucide/layout-grid";
import PanelTopInactive from "~icons/lucide/panel-top-inactive";
import Logs from "~icons/lucide/scroll-text";
import Server from "~icons/lucide/server";
import Settings from "~icons/lucide/settings";
import WalletCards from "~icons/lucide/wallet-cards";
import Item from "./Item.vue";
import ItemGroup from "./ItemGroup.vue";
import NotificationPanel from "./Notifications.vue";
import SearchItem from "./SearchItem.vue";

import { useRealtimeNotifs } from './useRealtimeNotifs'

const $route = useRoute();
const $team = getTeam();
const $session = session;

const navigation = computed(() => {
	if (!$team?.doc) return [];

	const routeName = String($route?.name || "");
	const onboardingComplete = $team.doc.onboarding.complete;
	const isSaasUser = $team.doc.is_saas_user;
	const enforce2FA = Boolean(
		!$team.doc.is_desk_user &&
			$team.doc.enforce_2fa &&
			!$team.doc.user_info?.is_2fa_enabled,
	);

	return [
		{
			name: "Welcome",
			icon: DoorOpen,
			route: "/welcome",
			isActive: routeName === "Welcome",
			condition: !onboardingComplete,
		},

		{
			customComponent: SearchItem,
			condition: onboardingComplete,
		},

		{
			name: "Notifications",
			condition: onboardingComplete && !isSaasUser,
			customComponent: NotificationPanel,
			disabled: enforce2FA,
		},
		{
			name: "Sites",
			icon: PanelTopInactive,
			route: "/sites",
			class: "mt-1.5",
			isActive:
				["Site List", "Site Detail", "New Site"].includes(routeName) ||
				routeName.startsWith("Site Detail"),
			disabled: enforce2FA,
		},
		/* {
      name: 'Benches',
      icon: (Package),
      route: '/benches',
      isActive: routeName.startsWith('Bench'),
      condition: $team.doc?.is_desk_user,
      disabled: !onboardingComplete || enforce2FA,
    }, */
		{
			name: "Benches",
			icon: Boxes,
			route: onboardingComplete ? "/groups" : "/enable-bench-groups",
			isActive:
				[
					"Release Group List",
					"Release Group Detail",
					"New Release Group",
					"Release Group New Site",
					"Deploy Candidate",
				].includes(routeName) ||
				routeName.startsWith("Release Group Detail") ||
				routeName === "Enable Benches",
			disabled: enforce2FA,
		},
		{
			name: "Servers",
			icon: Server,
			route: onboardingComplete ? "/servers" : "/enable-servers",
			isActive:
				["New Server"].includes(routeName) ||
				routeName.startsWith("Server") ||
				routeName === "Enable Servers",
			disabled: enforce2FA,
		},
		{
			name: "Dev Tools",
			icon: Code,
			route: "/devtools",
			condition: onboardingComplete && !isSaasUser,
			disabled: enforce2FA,
			children: [
				{
					name: "Log Browser",
					icon: Logs,
					route: "/log-browser",
					isActive: routeName === "Log Browser",
				},
				{
					name: "DB Analyzer",
					icon: Activity,
					route: "/database-analyzer",
					isActive: routeName === "DB Analyzer",
				},
				{
					name: "SQL Playground",
					icon: DatabaseZap,
					route: "/sql-playground",
					isActive: routeName === "SQL Playground",
				},
				{
					name: "Binlog Browser",
					icon: FileSearch,
					route: "/binlog-browser",
					isActive: routeName === "Binlog Browser",
					condition: $team.doc.is_binlog_indexer_enabled ?? false,
				},
			].filter((item) => item.condition ?? true),
			isActive: [
				"SQL Playground",
				"DB Analyzer",
				"Log Browser",
				"Binlog Browser",
			].includes(routeName),
		},
		{
			name: "Marketplace",
			icon: App,
			route: "/apps",
			isActive: routeName.startsWith("Marketplace"),
			class: "-mt-1",
			condition:
				$team.doc?.is_desk_user ||
				(!!$team.doc.is_developer && $session.hasAppsAccess),
			disabled: enforce2FA,
		},
		{
			name: "Billing",
			icon: WalletCards,
			route: "/billing",
			isActive: routeName.startsWith("Billing"),
			condition: $team.doc?.is_desk_user || $session.hasBillingAccess,
			disabled: enforce2FA,
		},
		{
			name: "Partnership",
			icon: Globe,
			route: "/partners",
			isActive: routeName === "Partnership",
			condition: Boolean($team.doc.erpnext_partner),
			disabled: enforce2FA,
		},
		{
			name: "Settings",
			icon: Settings,
			route: "/settings",
			isActive: routeName.startsWith("Settings"),
			disabled: enforce2FA,
		},
		{
			name: "Status",
			icon: LucideActivity,
			route: "/status",
			isActive: routeName === "Status",
			disabled: enforce2FA,
		},
	].filter((item) => item.condition ?? true);
});

useRealtimeNotifs((data) => {
	if (data.team === $team.doc.name) {
		unreadNotificationsCount.setData((data) => data + 1)
	}
})

</script>

<template>
  <template v-for="(item, _) in navigation" :key="item.name">
    <ItemGroup v-if="item.children" v-bind="item" />
    <component v-else-if="item.customComponent" :is="item.customComponent" :disabled="item.disabled" />
    <Item v-else v-bind="item" />
  </template>
</template>
