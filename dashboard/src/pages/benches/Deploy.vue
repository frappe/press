<script setup lang='ts'>
import { createResource, getCachedDocumentResource, Button, Dropdown, Badge } from 'frappe-ui';
import { h, computed } from 'vue';
import { getTeam } from "@/data/team"
import Collapsable from '@/components/common/Collapsable.vue'

const team = getTeam()

const dropdownOptions = computed(() => {
  const list = [
    {
      label: 'View in Desk',
      icon: 'external-link',
      condition: () => team?.doc?.is_desk_user,
      onClick: () => {
        window.open(
          `${window.location.protocol}//${window.location.host}/app/deploy-candidate-build/${this.id}`,
          '_blank',
        );
      },
    },
    {
      label: 'View App Versions',
      icon: 'package',
      onClick: () => {
        // this.appVersions();
      },
    }
  ]

  return list.filter((option) => option.condition?.() ?? true);
})

const cardLabels = {
  'Created by': 'sidhanth@frappe.io',
  Start: '2026-05-13T06:19:38.866Z',
  End: undefined,
  Duration: '20s'
}

</script>
<template>

  <main class='flex flex-col gap-5 py-3 px-5'>

    <!-- header -->
    <div class="flex gap-2 items-center">
      <button>
        <lucide-chevron-left class='size-4' />
      </button>

      <h2 class="text-ink-gray-9">
        deploy blablablab
      </h2>
      <Badge :label="'Running'" />

      <Button theme="red" class='ml-auto'>
        Stop Deploy
      </Button>

      <Button>
        <lucide-refresh-ccw class="h-4 w-4" />
      </Button>

      <Dropdown v-if="dropdownOptions?.length" :options="dropdownOptions">
        <template v-slot="{ open }">
          <Button>
            <template #icon>
              <lucide-more-horizontal class="h-4 w-4" />
            </template>
          </Button>
        </template>
      </Dropdown>
    </div>

    <!-- status cards -->
    <section class='grid grid-cols-4 gap-5'>
      <div v-for="(label, key) in cardLabels" :key="key" class="flex flex-col gap-2 border p-3 rounded">
        <span class="text-sm font-medium text-ink-gray-4">
          {{ key }}
        </span>

        <span class="text-sm text-ink-gray-9">
          {{ label || '-' }}
        </span>
      </div>
    </section>


    <!-- deploy steps + output -->
    <div class='flex gap-3 rounded border p-3'>
      <aside class='w-1/4'>
        <Collapsable  v-for='x in ["abc", "xyz"]'  headerCss="py-3 border-b" :key='x' :peerId='x'>
          <template #header>
            <lucide-circle-check class='size-3.5' />
            <span>Preparing builds</span>
          </template>

          <div class='p-2'>
            something
          </div>
        </Collapsable>
      </aside>

      <div class='bg-surface-gray-2 p-3 rounded w-full'>
        <span>Output</span>

        <pre> </pre>
      </div>



    </div>
  </main>
</template>
