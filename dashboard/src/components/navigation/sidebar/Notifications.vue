<script setup lang="ts">
import {
  Badge,
  Button,
  createListResource,
  frappeRequest,
  Popover,
  Tabs,
  Tooltip,
} from "frappe-ui";

import { h, nextTick, ref, watch, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { toast } from "vue-sonner";

import Scrollbar from "@/components/common/Scrollbar.vue";
import SupportAccessDialog from "@/components/SupportAccessDialog.vue";

import {
  unreadNotificationsCount,
  unreadSupportNotificationsCount,
} from "@/data/notifications";

import { useRealtimeNotifs } from './useRealtimeNotifs'

import { dayjsLocal } from "@/utils/dayjs";
import { getDocResource } from "@/utils/resource";
import { renderDialog } from "@/utils/components";
import { isMobile } from "@/utils/device";
import { getTeam } from "@/data/team";

import Item from "./Item.vue";

const formatHtml = (str: string) => {
  return str.replace(/<(?!\/?b\b)[^>]*>/g, "").split("\n")[0];
};

const scrollRef = ref(null);
const router = useRouter();
const team = getTeam();

const loadMore = async () => {
  await resource.next();
  await nextTick();

  const el = scrollRef.value?.$el;
  if (el) {
    const scrollable = el.querySelector("[data-reka-scroll-area-viewport]");
    scrollable.scrollBy({
      top: 500,
      behavior: "smooth",
    });
  }
};
const resource = createListResource({
  doctype: "Press Notification",
  url: "press.api.notifications.get_notifications",
  auto: true,
  cache: ["Notifications"],
  start: 0,
  pageLength: 10,
});

const markAsRead = (row, togglePopover) => {
  const docres = getDocResource({
    doctype: "Press Notification",
    name: row.name,
    whitelistedMethods: {
      markNotificationAsRead: "mark_as_read",
    },
  });

  docres.markNotificationAsRead.submit().then(() => {
    // requests tab needs to show both read/unread
    // so dont set local state!!!
    if (row.type !== "Support Access") {
      if (row.read === 0) unreadNotificationsCount.setData((data) => data - 1);

      resource.setData((data) => {
        const newData = data.filter((d) => d.name !== row.name);
        resource.originalData = newData;
        return newData;
      });
    }

    if (row.type === "Support Access") {
      if (row.read === 0)
        unreadSupportNotificationsCount.setData((data) => data - 1);

      openSupportAccess(null, row.document_name);
    }

    if (row.route && row.type !== "Support Access") {
      togglePopover();
      router.push("/" + row.route);
    }
  });
};

const markAllAsRead = (togglePopover) => {
  toast.promise(
    frappeRequest({
      url: "/api/method/press.api.notifications.mark_all_notifications_as_read",
    }),
    {
      success: () => {
        resource.reload();
        togglePopover();

        return "All notifications marked as read";
      },
      loading: "Marking all notifications as read...",
      error: (error) =>
        error.messages?.length ? error.messages.join("\n") : error.message,
    },
  );
};

const openSupportAccess = (e, name) => {
  e?.stopPropagation();
  renderDialog(
    h(SupportAccessDialog, {
      name,
    }),
  );
};

// tile icons & classes
const iconCss = {
  "Site Update": {
    icon: LucideRefreshCw,
    txt: "text-ink-green-2",
    bg: "bg-surface-green-1",
  },
  "Site Migrate": {
    icon: LucideArrowUpCircle,
    txt: "text-ink-green-2",
    bg: "bg-surface-green-1",
  },
  "Version Upgrade": {
    icon: LucideArrowUpCircle,
    txt: "text-ink-green-2",
    bg: "bg-surface-green-1",
  },
  "Bench Deploy": {
    icon: LucideRocket,
    txt: "text-ink-green-2",
    bg: "bg-surface-green-1",
  },
  "Site Recovery": {
    icon: LucideShieldCheck,
    txt: "text-ink-green-2",
    bg: "bg-surface-green-1",
  },
  "Agent Job Failure": {
    icon: LucideAlertTriangle,
    txt: "text-ink-red-4",
    bg: "bg-surface-red-1",
  },
  "Downtime/Performance": {
    icon: LucideActivity,
    txt: "text-ink-red-4",
    bg: "bg-surface-red-1",
  },
  "Support Access": {
    icon: LucideKey,
    txt: "text-ink-amber-3",
    bg: "bg-surface-amber-1",
  },
  "Auto Scale": {
    icon: LucideTrendingUp,
    txt: "text-ink-red-4",
    bg: "bg-surface-red-1",
  },
};

// Reload resource on tab switch
const activeTab = ref(0);

watch(activeTab, (x) => {
  const filters: any = {};
  if (x == 0) {
    //
  } else if (x == 1) {
    filters.type = "Support Access";
    delete filters.read;
  } else {
    filters.read = "Unread";
  }

  resource.update({ filters, start: 0, pageLength: 10 });
  resource.reload();
});

const tabs = [
  { label: "All", icon: LucideRows2 },
  { label: "Requests", icon: LucideKeySquare },
  { label: "Unread", icon: LucideMessageSquareDot },
];

useRealtimeNotifs((data) => {
	if (data.team === team.doc.name) resource.reload()
})
</script>

<template>
  <Popover :placement="isMobile() ? 'top-start' : 'right-start'" popover-class="-mt-[15%] md:-mt-2.5">
    <!-- sidebar item -->
    <template #target="{ togglePopover }">
      <Item is='BUTTON' v-bind='$attrs' aria-label="Notifications btn" name='Notifications' @click="togglePopover">
        <template #prefix>

          <span class="flex relative">
            <LucideBell class="size-4 text-ink-gray-6" />
            <span v-if="unreadNotificationsCount.data > 0"
              class="size-1 bg-surface-blue-3 rounded-full absolute right-0 -top-0.5" />
          </span>
        </template>

        <template #suffix>
          <span class="text-xs text-ink-gray-6" v-if="unreadNotificationsCount.data > 0">
            {{
              unreadNotificationsCount.data > 99
                ? '99+'
                : unreadNotificationsCount.data
            }}
          </span>
        </template>
      </Item>
    </template>

    <!-- floating drawer  -->
    <template #body="{ togglePopover }">
      <div
        class="text-ink-gray-9 bg-surface-white h-screen -ml-2.5 w-screen md:ml-2 shadow-xl md:w-[430px] flex flex-col dark:border-x">
        <!-- header -->
        <div class="text-base flex items-center py-2 pl-4 pr-2 border-b">
          <span class="font-medium mr-auto"> Notifications</span>

          <Button @click="markAllAsRead(togglePopover)" variant="ghost">
            <template #icon>
              <LucideCheckCheck class="size-3.5" />
            </template>
          </Button>
          <Button variant="ghost" @click="togglePopover">
            <template #icon>
              <LucideX class="size-4" />
            </template>
          </Button>
        </div>

        <Tabs v-model="activeTab"
          class="w-full flex-none [&_[role=tablist]]:pr-2 [&_[role=tab]]:justify-center [&_role=tab]]:w-full" :tabs>
          <template #tab-item="{ tab }">
            <button class="w-full flex items-center gap-2 py-2 text-ink-gray-5 aria-selected:text-ink-gray-9">
              <span class="text-sm">{{ tab.label }}</span>
              <Badge v-if="tab.label != 'All'">{{
                tab.label == 'Unread'
                  ? unreadNotificationsCount.data
                  : unreadSupportNotificationsCount.data
              }}</Badge>
            </button>
          </template>
        </Tabs>

        <!-- body -->
        <Scrollbar ref="scrollRef" v-if="resource.data.length > 0" class='max-h-[67%] md:max-h-full'>

          <!-- notif tiles = icon + info -->
          <div v-for="x in resource.data"
            class="[&_b]:font-semibold p-2 md:p-4 flex gap-4 items-center relative cursor-pointer border-b last:border-0 hover:bg-surface-gray-1"
            @click="markAsRead(x, togglePopover)" title="Click to mark as read">
            <!-- type icon -->
            <div class="size-8 flex-shrink-0 flex items-center p-2 rounded mb-auto mt-1 relative
              dark:bg-surface-gray-1" :class="[iconCss[x.type].bg || 'bg-surface-gray-1']">
              <span v-if="x.read == 0"
                class="p-0.5 ring-outline-gray-2 ring-2 bg-surface-gray-7 absolute rounded top-0 left-0" />
              <component :is="iconCss[x.type].icon || LucideCircleAlert" class="size-4"
                :class="iconCss[x.type].txt || 'text-ink-gray-6'" />
            </div>


            <!-- info -->
            <div class="text-base leading-relaxed flex flex-wrap gap-2 w-full min-w-0">
              <p v-html="formatHtml(x.message)" class="w-full" />

              <Badge class="text-xs mr-auto">
                {{ x.title }}

                <Tooltip text="This notification requires your attention" :hoverDelay="0"
                  v-if="x.is_actionable && !x.is_addressed">
                  <LucideCircleAlert class="size-3" />
                </Tooltip>
              </Badge>

              <span class="text-ink-gray-5 text-xs">
                {{ dayjsLocal(x.creation).fromNow() }}
              </span>
            </div>
          </div>
        </Scrollbar>

        <div v-else class="text-center text-ink-gray-6 text-sm py-10">
          No notifications to show
        </div>

        <Button @click="loadMore" v-if="resource.hasNextPage" label="Load More" size="sm" class="ml-auto my-3 mr-3" />
      </div>
    </template>
  </Popover>
</template>
