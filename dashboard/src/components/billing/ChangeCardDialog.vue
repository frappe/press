<template>
	<div>
		<Dialog
			v-model="show"
			:options="{ title: 'Choose active card' }"
			:disableOutsideClickToClose="confirmDialogOpened"
		>
			<template #body-content>
				<div v-if="cards.data?.length" class="flex flex-col gap-2.5">
					<div
						v-for="card in cards.data"
						:key="card.name"
						class="flex justify-between gap-2 rounded p-2.5 text-base text-gray-900 hover:bg-gray-100"
					>
						<div class="flex gap-2">
							<component :is="cardBrandIcon(card.brand)" class="my-auto" />
							<div>
								<div class="flex h-7 items-center gap-1 font-medium">
									<div>{{ card.name_on_card }}</div>
									<div>&middot;</div>
									<div class="flex gap-1 text-gray-700">
										<div>Card ending in ••••</div>
										<div>{{ card.last_4 }}</div>
									</div>
									<Badge
										v-if="card.is_default"
										class="ml-1.5"
										label="Default"
										variant="outline"
										theme="green"
									/>
								</div>
								<div class="text-gray-600">
									Expiry
									{{
										card.expiry_month < 10
											? `0${card.expiry_month}`
											: card.expiry_month
									}}/{{ card.expiry_year }}
								</div>
							</div>
						</div>
						<div v-if="cards.data.length > 1 && !card.is_default">
							<Dropdown
								:options="[
									{
										label: 'Set as default',
										onClick: () => setAsDefault(card.name),
										condition: () => !card.is_default,
									},
									{ label: 'Remove', onClick: () => removeCard(card.name) },
								]"
							>
								<Button icon="more-horizontal" variant="ghost" />
							</Dropdown>
						</div>
					</div>
				</div>
			</template>
			<template #actions>
				<Button
					label="Add new card"
					class="w-full"
					variant="solid"
					@click="emit('addCard')"
				>
					<template #prefix>
						<FeatherIcon name="plus" class="h-4" />
					</template>
				</Button>
			</template>
		</Dialog>
	</div>
</template>
<script setup>
// import { createDialog } from '../dialogs.js';
import {
	Dropdown,
	Badge,
	Dialog,
	Button,
	FeatherIcon,
	createResource,
} from 'frappe-ui';
import { cardBrandIcon, confirmDialog } from '../../utils/components';
import { ref } from 'vue';

const emit = defineEmits(['success', 'addCard']);

const show = defineModel();

const cards = createResource({
	url: 'press.api.billing.get_payment_methods',
	cache: 'cards',
	auto: true,
});

const setAsDefault = (card) => {
	createResource({
		url: 'press.api.billing.set_as_default',
		params: { name: card },
		auto: true,
		onSuccess: () => {
			cards.reload();
			emit('success');
		},
	});
};

const confirmDialogOpened = ref(false);
const removeCard = (card) => {
	confirmDialogOpened.value = true;
	confirmDialog({
		title: 'Remove Card',
		message: 'Are you sure you want to remove this card?',
		primaryAction: {
			label: 'Remove',
			variant: 'solid',
			theme: 'red',
			onClick: ({ hide }) => {
				createResource({
					url: 'press.api.billing.remove_payment_method',
					params: { name: card },
					auto: true,
					onSuccess: () => {
						cards.reload();
						confirmDialogOpened.value = false;
						hide();
					},
				});
			},
		},
		onSuccess: () => {
			confirmDialogOpened.value = false;
		},
	});
};
</script>
