<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui";
import { defineAsyncComponent, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { session } from "@/data/session";
import { getTeam } from "@/data/team";
import { mobileNav } from "@/data/ui";
import { isMobile } from "@/utils/device";
import { setTheme } from "@/utils/useTheme";
import LucideBookText from "~icons/lucide/book-text";
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideSupport from "~icons/lucide/life-buoy";
import LucideMessageSquareCode from "~icons/lucide/message-square-code";
import LucideMoon from "~icons/lucide/moon";
import LucideAlert from "~icons/lucide/notebook-text";
import DarkModeLabel from "./DarkModeLabel.vue";
import NavList from "./NavList.vue";

const $team = getTeam();
const $session = session;
const router = useRouter();

const showTeamSwitcher = ref(false);
const collapsed = ref(false);

const SwitchTeamDialog2 = defineAsyncComponent(
  () => import("../../SwitchTeamDialog.vue"),
);

const support = () => {
  window.open("https://support.frappe.io/helpdesk/my-tickets/new", "_blank");
};
const docs = () => {
  window.open("https://docs.frappe.io/cloud", "_blank");
};

const feedback = () => {
  window.open("https://frappecloud.com/frappe-cloud-feedback/new", "_blank");
};

const releaseNotes = () => {
  window.open("https://github.com/frappe/press/releases/", "_blank");
};

watch(router.currentRoute, () => {
  if (isMobile() && mobileNav.value) mobileNav.value = false;
});

const userDropdownOptions = [
  {
    label: "Change Team",
    icon: "command",
    condition: () =>
      $team?.doc?.valid_teams?.length > 1 || $team?.doc?.is_desk_user,
    onClick: () => (showTeamSwitcher.value = true),
  },

  {
    label: "Theme",
    icon: LucideMoon,
    submenu: [
      { label: "Light Mode", icon: "sun", onClick: () => setTheme("light") },
      // dropdown component as per this frappe-ui version doesnt support suffix slot
      // so make the icon itself icon+label+beta badge
      { icon: DarkModeLabel, onClick: () => setTheme("dark") },
    ],
  },

  { label: "Logout", icon: "log-out", onClick: $session.logout.submit },
];

const helpDropdownOptions = [
  { label: "Docs", icon: LucideBookText, onClick: docs },
  { label: "Get Support", icon: LucideSupport, onClick: support },
  { label: "Share Feedback", icon: LucideMessageSquareCode, onClick: feedback },
  { label: "Release Notes", icon: LucideAlert, onClick: releaseNotes },
];
</script>

<template>
  <aside class="relative flex md:min-h-screen w-full p-2 gap-1 flex-col border-r
    bg-surface-white  md:bg-surface-gray-1 dark:bg-transparent"
    :class='collapsed ? "md:w-fit [&_.collapsed]:hidden !p-1" : "md:w-auto md:min-w-[220px]"'>

    <div class='flex gap-2 items-center border-y md:border-0 p-2 md:p-0 -m-2 md:m-0 h-[44px]'>
      <FCLogo class="size-6 md:hidden mr-auto" />

      <Dropdown :options="userDropdownOptions">
        <template v-slot="{ open }">
          <button
            class="flex gap-2 w-fit md:w-full p-1.5 md:p-1 items-center rounded md:mb-1 bg-surface-gray-2 md:bg-transparent   hover:bg-surface-gray-2"
            :class="open ? 'md:bg-surface-white dark:bg-surface-gray-2 shadow-sm' : ''
              ">
            <FCLogo class="size-8  hidden md:flex shrink-0 rounded" />
            <LucideUser class='size-3.5 -mr-1.5 md:hidden' />

<<<<<<< HEAD
            <div class="flex flex-col gap-0.5 ml-1 min-w-0 md:m-0">
              <div class="text-base font-medium hidden md:flex text-ink-gray-9">
                Frappe Cloud
              </div>

              <div
                class="text-sm text-left text-ink-gray-7 truncate">
=======
            <div class="flex flex-col gap-1 ml-1 min-w-0 md:m-0 collapsed">
              <div class="text-base font-medium leading-none hidden md:flex text-ink-gray-9">
                Frappe Cloud
              </div>

              <div class="text-sm text-left leading-none text-ink-gray-7 truncate">
>>>>>>> f721a5238 (feat(sidebar): Allow collaps/expand)
                {{ $team?.get.loading ? 'Loading...' : $team?.doc?.user }}
              </div>
            </div>

            <LucideChevronDown class="md:ml-auto size-4 collapsed" />
          </button>
        </template>
      </Dropdown>

      <button class="p-2 md:hidden bg-surface-gray-2 rounded" @click="mobileNav = !mobileNav">
        <lucide-x v-if="mobileNav" class="size-3" />
        <lucide-menu v-else class="size-3" />
      </button>
    </div>

    <nav class='flex-col flex-1 gap-1 md:flex py-3 md:p-0 md:mt-1'
      :class="[mobileNav ? 'flex border-b' : 'hidden', collapsed ? '*:mx-auto *:w-fit' : '']">

      <NavList>
        <template v-slot="{ list }">
          <template v-for="(item, _) in list" :key="item.name">
            <ItemGroup v-if="item.children" v-bind="item" />
            <component v-else-if="item.customComponent" :is="item.customComponent" :disabled="item.disabled" />
            <Item v-else v-bind="item" />
          </template>
        </template>
      </NavList>

      <div :class='collapsed ? "flex-col" : "flex-row"' class='flex gap-1 justify-between items-center  mt-auto'>
        <Dropdown :options="helpDropdownOptions">
          <Button variant="ghost">
            <template #prefix v-if="!collapsed">
              <LucideCircleQuestionMark class="size-4" />
            </template>

            <LucideCircleQuestionMark v-if="collapsed" class="size-4" />

            <template v-if="!collapsed">Help</template>
          </Button>
        </Dropdown>

        <Button variant="ghost" class='hidden md:flex' :class='collapsed ? "mb-2" : ""' @click='collapsed = !collapsed'>
          <template #icon>
            <LucidePanelLeft class="size-4 transition-transform duration-300" :class='collapsed ? "rotate-180" : ""' />
          </template>
        </Button>
      </div>
    </nav>

    <!-- TODO: update component name after dashboard-beta merges -->
    <SwitchTeamDialog2 v-model="showTeamSwitcher" :key="String(showTeamSwitcher)" />
  </aside>
</template>
