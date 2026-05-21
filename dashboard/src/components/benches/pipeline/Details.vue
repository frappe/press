<script setup lang="ts">
import {
  createResource,
  createListResource,
  createDocumentResource,
  Button,
  Dropdown,
  Badge,
} from 'frappe-ui'

import { toast } from 'vue-sonner';
import Tabs from '@/components/common/Tabs.vue'

import Stages from './Stages.vue'
import CopyBtn from '@/components/utils/CopyBtn.vue'
import Scrollbar from '@/components/common/Scrollbar.vue'
import Collapsable from '@/components/common/Collapsable.vue'
import StatusIcon from './StatusIcon.vue'
import AppVersionsDialog from '@/dialogs/AppVersionsDialog.vue';

import { h, ref, reactive, computed, provide, watch, onMounted, onBeforeUnmount } from 'vue'
import { confirmDialog, renderDialog } from '@/utils/components';
import { getTeam } from '@/data/team'

import { secsToDuration, date, duration } from '@/utils/format'

const team = getTeam()
const socket = window.$socket

interface Props {
  deployview: boolean
  id?: string

  // bench  name
  name?: string
}

const props = withDefaults(defineProps<Props>(), {
  deployview: false
})

const output = reactive({
  val: null,
  status: null,
  selectedIndex: null
})

const setOutput = (opts: String | null) => {
  output.val = opts.val
  output.status = opts.status
  output.selectedIndex = opts.selectedIndex
}

provide('setOutput', setOutput)
provide('output', output)

const dropdownOptions = computed(() => {
  const list = [
    {
      label: 'View in Desk',
      icon: 'external-link',
      condition: () => team?.doc?.is_desk_user,
      onClick: () => {
        const pathname = props.deployview ? 'deploy-candidate-build' : 'release-pipeline'

        window.open(
          `${window.location.protocol}//${window.location.host}/app/${pathname}/${props.id}`,
          '_blank',
        )
      },
    },
    {
      label: 'View App Versions',
      icon: 'package',
      onClick: appVersions,
      condition: () => props.deployview
    }
  ]

  return list.filter((option) => option.condition?.() ?? true)
})

const activeBuildId = ref(props.deployview ? props.id : null)
const buildIds = computed(() => {
  if (props.deployview) return [props.id]

  const ids = pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => x.name)
  if (!activeBuildId.value && ids) activeBuildId.value = ids[0]
  return ids || []
})

const pipeline = createDocumentResource({
  doctype: 'Release Pipeline',
  name: props.id,
  auto: !props.deployview,
})

const notifApiFields = {
  doctype: 'Press Notification',
  fields: [
    'name',
    'title',
    'message',
    'document_name',
    'class',
    'assistance_url',
  ],
  filters: { document_type: 'Deploy Candidate Build', is_actionable: true },
}

const errors = createListResource(notifApiFields)
const warnings = createListResource(notifApiFields)

watch(
  () => buildIds.value,
  (x) => {
    if (!x) return

    errors.update({
      cache: [
        'Press Notification Error',
        'Deploy Candidate Build',
        buildIds.value,
      ],
      filters: { document_name: ['in', buildIds.value], class: 'Error' },
    })
    errors.fetch()

    warnings.update({
      cache: [
        'Press Notification Warning',
        'Deploy Candidate Build',
        buildIds.value,
      ],
      filters: { document_name: ['in', buildIds.value], class: 'Warning' },
    })
    warnings.fetch()
  },
  { immediate: true }
)

const tabState = ref('Tasks')

const sidebarTabs = ref([
  { label: 'Tasks', icon: LucideWorkflow },
  { label: 'Issues', icon: LucideAlertCircle },
])

const badgeThemes = {
  Pending: 'gray',
  Running: 'blue',
  'Partial Success': 'yellow',
  Success: 'green',
  Failure: 'red',
  Retrying: 'yellow',
}

// ---------------------  Realtime stuff ----------------------
const handleDocUpdate = (x) => {
  if (x.doctype === 'Release Pipeline' && x.name === props.id)
    pipeline.reload()
}

if (!props.deployview) {
  onMounted(() => {
    socket.emit('doc_subscribe', 'Release Pipeline', props.id)
    socket.on('doc_update', handleDocUpdate)
  })

  onBeforeUnmount(() => {
    socket.emit('doc_unsubscribe', 'Release Pipeline', props.id)
    socket.off('doc_update', handleDocUpdate)
  })
}

const deployviewBuild = ref(null)
const dummyStages = ref([
  { label: "Pre-release checks", status: "Success" },
  { label: "Preparing for deployment", status: "Success" },
  { label: "Building", status: "Pending" },
  { label: "Deploying", status: "Pending" },
])

const updateDummyStage = (index, status) => {
  dummyStages.value[index].status = status
}

const updateDeployViewBuild = (data) => {
  deployviewBuild.value = data
}

const appVersions = () => {
  const deploy = deployviewBuild.value;
  renderDialog(
    h(AppVersionsDialog, {
      dc_name: deploy.name,
      group: deploy.group,
      status: deploy.status,
    }),
  );
}

const stopBuild = () => {
  const deploy = deployviewBuild.value

  confirmDialog({
    title: 'Fail Running Build',
    message: `
				Are you sure you want to fail this running build?<br><br>
				<div class="text-bg-base bg-surface-gray-2 p-2 rounded-md">
				This will <strong>stop the current build immediately</strong>.  
				All progress made so far will be <strong>discarded</strong>, and the next triggered build will start from scratch.
				<br><br>
				Use this option if a build is stuck, taking unusually long, or is expected to fail.
				</div>
				`,
    primaryAction: {
      label: 'Stop Build',
      variant: 'solid',
      theme: 'red',
      onClick({ hide }) {
        createResource({
          url: 'press.api.bench.fail_build',
          params: { dn: deploy.name },
        })
          .fetch()
          .then(() => {
            hide();
          })
          .catch(() => {
            hide();
            toast.error(
              'Unable to stop build please wait for the status to be updated',
            );
          });
      },
    },
  });
}
</script>

<template>
  <main class="pipeline-page flex flex-col gap-4 py-3 px-5 w-full h-[calc(100dvh-6rem)]">
    <!-- header -->
    <div class="flex gap-2 items-center">
      <router-link :to="`/groups/${name}/${deployview? 'deploys':'pipelines'}`">
        <lucide-chevron-left class="size-4" />
      </router-link>

      <h2 class="text-ink-gray-9"> {{ deployview ? deployviewBuild?.deploy_candidate : "Pipeline" }} {{
        pipeline?.doc?.name }}</h2>

      <Badge :label="deployview ? deployviewBuild?.status : pipeline?.doc?.status"
        :theme="badgeThemes[deployview ? deployviewBuild?.status : pipeline?.doc?.status] || 'gray'"
        class="mr-auto" />

      <Tabs variant="solid" v-if="!deployview && buildIds.length > 1"
        :tabs="pipeline?.doc?.steps?.stages[2]?.builds?.map((x) => ({ label: x.architecture, value: x.name }))"
        v-model="activeBuildId" class=" [&_[role=tablist]]:w-fit" />

        <Button
						@click="stopBuild"
						v-if="deployview && deployviewBuild?.status === 'Running'"
						theme="red"
					>
						Stop Deploy
					</Button>

      <Dropdown v-if="dropdownOptions?.length" :options="dropdownOptions">
        <Button>
          <lucide-more-horizontal class="size-4" />
        </Button>
      </Dropdown>
    </div>

    <!-- status cards -->
    <section class="grid grid-cols-4 gap-3 [&_b]:text-ink-gray-4 [&_b]:font-normal text-sm -mt-1">
      <div class="flex flex-col gap-2 border p-4 rounded ">
        <b> Created by </b>
        <span class="text-ink-gray-9">{{ deployview ? deployviewBuild?.owner : pipeline?.doc?.owner }} </span>
      </div>

      <div class="flex flex-col gap-2 border p-4 rounded">
        <b> Start </b>
        <span> {{ date(deployview ? deployviewBuild?.build_start : pipeline?.doc?.steps?.start) || '-' }} </span>
      </div>

      <div class="flex flex-col gap-2 border p-4 rounded">
        <b> End </b>
        <span> {{ date(deployview ? deployviewBuild?.build_end : pipeline?.doc?.steps?.end) || '-' }} </span>
      </div>

      <div class="flex flex-col gap-2 border p-4 rounded">
        <b> Duration </b>
        <span>
          {{ deployview ? duration(deployviewBuild?.build_duration) || '-' : secsToDuration(pipeline?.doc?.steps?.duration) || '-' }}
        </span>
      </div>
    </section>

    <!-- deploy steps + output -->
    <div class="flex rounded border p-3 pt-1 flex-1 min-h-0">
      <Scrollbar class="px-0.5 pr-3 transition-all duration-500 shrink-0" :class="output.val ? 'w-[30rem]' : 'w-full'">
        <Tabs class="w-full sticky top-0 z-10 bg-surface-white mb-2" tablistClass="!px-0" :tabs="sidebarTabs"
          v-model="tabState">
          <template #suffix="{ tab }">
            <span v-if='tab.label == "Issues"' class="bg-surface-gray-2 py-0.5 px-1 rounded text-xs leading-none">
              {{ (errors?.data?.length || 0) + (warnings?.data?.length || 0) }}</span>
          </template>
        </Tabs>

        <Stages v-if="tabState == 'Tasks'" :stages="deployview ? dummyStages : pipeline?.doc?.steps?.stages" :buildIds
          :activeBuildId :updateDummyStage="deployview ? updateDummyStage : null"
          :updateDeployViewBuild="deployview ? updateDeployViewBuild : null" :deployview />

        <!-- list of errors -->
        <template v-else>
          <div
            v-for='x in [...errors?.data || [], ...warnings?.data || []]?.filter(x => x.document_name == activeBuildId)'
            class="flex flex-col gap-1">
            <Collapsable headerCss="py-3" class="mb-3">
              <template #header>
                <StatusIcon :status="x.class == 'Error' ? 'Failed' : 'Warning'" />
                {{ x.title }}
                {{ x.class }}
              </template>

              <div v-html="x.message" class="leading-relaxed rounded p-3 ml-3 mb-3 text-sm"
                :class='x.class == "Error" ? " bg-surface-red-1 text-ink-red-4" : "bg-surface-amber-1 text-ink-amber-3"' />

              <div class="w-full flex justify-end" v-if='x.assistance_url'>
                <a :href="x.assistance_url" target="_blank"
                  class="bg-surface-gray-1 p-1.5 px-2.5 rounded hover:opacity-70">
                  Fix
                </a>
              </div>
            </Collapsable>
          </div>
        </template>
      </Scrollbar>

      <!-- output -->
      <div v-show="output.val"
        class="overflow-hidden bg-surface-gray-1 dark:bg-surface-cards p-3 mt-2 rounded transition-all duration-500 flex-1">
        <div class="flex items-center gap-2 pb-2 border-outline-gray-2 mb-3 text-ink-gray-6">
          <span>Output</span>
          <CopyBtn :text="output?.val || ''" class="ml-auto" />
          <button @click="setOutput({ val: null, status: null })">
            <lucide-x class="size-4" />
          </button>
        </div>

        <pre class="font-mono text-xs overflow-auto -m-3 p-2" :class='output.status == "Failure" ? "bg-surface-red-1 text-ink-red-3" :
          ""'>{{ output.val }}</pre>
      </div>
    </div>
  </main>
</template>

<style>
body:has(.pipeline-page) #scrollContainer {
  overflow: hidden;
  height: 100%;
}
</style>
