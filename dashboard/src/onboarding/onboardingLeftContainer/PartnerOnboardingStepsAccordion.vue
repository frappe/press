<script setup>
import { ref } from 'vue';
import { Button } from 'frappe-ui';
import CompanyInformationModal from '@/onboarding/onboardingLeftContainer/modal/CompanyInformationModal.vue';
import LucideChevronDown from '~icons/lucide/chevron-down';
import LucideCircleCheck from '~icons/lucide/circle-check';
import LucideCircleDashed from '~icons/lucide/circle-dashed';
import LucideLock from '~icons/lucide/lock';
import {
	FAccordionRoot,
	FAccordionItem,
	FAccordionHeader,
	FAccordionTrigger,
	FAccordionContent,
} from '@/onboarding/accordion';

const openStep = ref('step-profile');

const steps = [
	{
		value: 'step-register',
		title: 'Register as a Frappe Partner',
		required: true,
		status: 'completed',
		description: null,
		summaryRight: null,
		actionLabel: null,
	},
	{
		value: 'step-profile',
		title: 'Complete your company profile',
		required: true,
		status: 'pending',
		description:
			'Before you continue, we need to know more about your company to understand how your company can benefit from becoming a Frappe Partner.',
		summaryRight: null,
		actionLabel: 'Fill out company information',
	},
	{
		value: 'step-certificates',
		title: 'Link at least two Frappe School certificates',
		required: true,
		status: 'pending',
		description:
			'Partners must have at least two full-time team members who are certified in ERPNext or the Frappe Framework. Certifications can be earned through Frappe School.Once a certification has been issued, link the certificate to your company. We will send a validation email to the email address attached to the certificate. Once approved, you will see changes reflected here.',
		summaryRight: null,
		actionLabel: null,
	},
	{
		value: 'step-mrr',
		title: 'Log an MRR of at least $100 on Frappe Cloud',
		required: true,
		status: 'pending',
		description:
			'Create sites and manage hosting for your customers that use Frappe apps on Frappe Cloud consistently to cross this threshold. Based on your Billing details, we will automatically update this step’s completion.',
		summaryRight: '$0 / $100 MRR',
		actionLabel: null,
	},
	{
		value: 'step-terms',
		title: 'Accept Partnership terms',
		required: true,
		status: 'pending',
		description: null,
		summaryRight: null,
		actionLabel: null,
	},
	{
		value: 'step-logo',
		title: 'Add your company logo',
		required: false,
		status: 'pending',
		description: null,
		summaryRight: null,
		actionLabel: null,
	},
];

const canSubmit = ref(false);
const companyInfoModalOpen = ref(false);
</script>

<template>
	<div class="flex w-full flex-col gap-6">
		<CompanyInformationModal v-model="companyInfoModalOpen" />
		<FAccordionRoot v-model="openStep">
			<FAccordionItem
				v-for="step in steps"
				:key="step.value"
				:value="step.value"
				class="border-b border-outline-gray-modals last:border-b-0"
			>
				<FAccordionHeader>
					<FAccordionTrigger class="py-6">
						<span
							v-if="step.status === 'completed'"
							class="inline-flex shrink-0 text-green-600"
							aria-hidden="true"
						>
							<LucideCircleCheck class="size-4" />
						</span>
						<span
							v-else
							class="inline-flex shrink-0 text-ink-gray-5"
							aria-hidden="true"
						>
							<LucideCircleDashed class="size-4" />
						</span>

						<span class="min-w-0 flex-1">
							<span
								class="text-base font-medium"
								:class="{
									'text-ink-gray-5 line-through': step.status === 'completed',
									'text-ink-gray-8': step.status !== 'completed',
								}"
							>
								{{ step.title }}
								<template v-if="step.required">
									<span class="text-red-600"> *</span>
								</template>
								<template v-else>
									<span class="font-normal text-ink-gray-5"> Optional</span>
								</template>
							</span>
						</span>

						<span
							v-if="step.summaryRight"
							class="shrink-0 whitespace-nowrap pr-2 text-sm font-normal text-ink-gray-6"
						>
							{{ step.summaryRight }}
						</span>

						<LucideChevronDown
							class="size-4 shrink-0 text-ink-gray-6 transition-transform duration-200 group-data-[state=open]:rotate-180"
						/>
					</FAccordionTrigger>
				</FAccordionHeader>

				<FAccordionContent v-if="step.description || step.actionLabel">
					<!-- TODO:step description if contains multiple lines needs to displayed in a list format -->
					<p
						v-if="step.description"
						class="mb-4 max-w-prose self-stretch text-ink-gray-6 text-p-base font-normal leading-normal tracking-wide"
					>
						{{ step.description }}
					</p>
					<Button
						v-if="step.actionLabel"
						variant="solid"
						:label="step.actionLabel"
						@click="companyInfoModalOpen = true"
					/>
				</FAccordionContent>
			</FAccordionItem>
		</FAccordionRoot>

		<div class="flex justify-start">
			<Button
				variant="solid"
				class="w-full sm:w-auto"
				:disabled="!canSubmit"
				:iconLeft="LucideLock"
				label="Submit for approval"
			/>
		</div>
	</div>
</template>
