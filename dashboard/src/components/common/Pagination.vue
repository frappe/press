<script setup lang="ts">
import LucideLeft from '~icons/lucide/chevron-left';
import LucideRight from '~icons/lucide/chevron-right';
import LucideChevronsLeft from '~icons/lucide/chevrons-left';
import LucideChevronsRight from '~icons/lucide/chevrons-right';
import LucideElipsis from '~icons/lucide/ellipsis';

import {
	PaginationEllipsis,
	PaginationFirst,
	PaginationLast,
	PaginationList,
	PaginationListItem,
	PaginationNext,
	PaginationPrev,
	PaginationRoot,
} from 'reka-ui';

interface Props {
	totalPages: number;
	limit?: number;
}

withDefaults(defineProps<Props>(), {
	limit: 10,
});
</script>

<template>
	<PaginationRoot
		:total="totalPages"
		:sibling-count="1"
		:items-per-page="limit"
		show-edges
		class="text-sm"
	>
		<PaginationList
			v-slot="{ items }"
			class="flex items-center gap-2 text-ink-gray-6"
		>
			<PaginationFirst
				class="p-2 hover:bg-surface-gray-1 transition disabled:opacity-50 rounded"
			>
				<LucideChevronsLeft class="size-4" />
			</PaginationFirst>

			<PaginationPrev
				class="p-2 hover:bg-surface-gray-1 transition disabled:opacity-50 rounded"
			>
				<LucideLeft class="size-4" />
			</PaginationPrev>

			<template v-for="(page, index) in items">
				<PaginationListItem
					v-if="page.type === 'page'"
					:key="index"
					class="size-7 bg-surface-gray-2 rounded data-[selected]:bg-surface-gray-5 data-[selected]:text-ink-gray-1 hover:bg-surface-gray-1 transition"
					:value="page.value"
				>
					{{ page.value }}
				</PaginationListItem>

				<PaginationEllipsis v-else :key="page.type" :index="index" class="p-2">
					<LucideElipsis class="size-3.5" />
				</PaginationEllipsis>
			</template>

			<PaginationNext
				class="p-2 hover:bg-surface-gray-1 transition disabled:opacity-50 rounded"
			>
				<LucideRight class="size-4" />
			</PaginationNext>

			<PaginationLast
				class="p-2 hover:bg-surface-gray-1 transition disabled:opacity-50 rounded"
			>
				<LucideChevronsRight class="size-4" />
			</PaginationLast>
		</PaginationList>
	</PaginationRoot>
</template>
