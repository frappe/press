<template>
	<div class="mx-auto max-w-2xl rounded-lg border p-8">
		<div class="prose prose-sm max-w-none">
			<h1 class="text-2xl font-semibold">Welcome to Frappe Cloud</h1>
			<p>
				Frappe Cloud makes it easy to manage sites and apps like ERPNext in an
				easy to use dashboard with powerful features like automatic backups,
				custom domains, SSL certificates, custom apps, automatic updates and
				more.
			</p>
		</div>
		<p class="mt-6 text-base text-gray-800">
			Complete the following steps to get started:
		</p>
		<div class="mt-4 space-y-6">
			<div class="rounded-md">
				<div>
					<div class="flex items-center justify-between space-x-2">
						<div class="flex items-center space-x-2">
							<TextInsideCircle>1</TextInsideCircle>
							<span class="text-base font-medium">
								{{
									$team.doc.is_saas_user
										? 'Trial site created'
										: 'Account created'
								}}
							</span>
						</div>

						<div
							class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
						>
							<i-lucide-check class="h-3 w-3 text-white" />
						</div>
					</div>
					<div v-if="$team.doc.is_saas_user" class="pl-7">
						<p class="mt-2 text-p-base text-gray-800">
							Your trial will expire on [date]. After that you won't be able to
							access your site. Set up a payment method to enjoy uninterrupted
							service.
						</p>
					</div>
				</div>
			</div>
			<div class="rounded-md">
				<div v-if="!$team.doc.payment_mode">
					<div class="flex items-center space-x-2">
						<TextInsideCircle>2</TextInsideCircle>
						<span class="text-base font-medium"> Set up payment method </span>
					</div>

					<div class="pl-7">
						<p class="mt-2 text-p-base text-gray-800">
							If you select Postpaid as your payment method, you need to add a
							card on file. If you do this, we give you
							<span class="font-medium">{{ free_credits }}</span>
							free credits so that you can create sites and test them without
							any upfront cost.
						</p>
						<p class="mt-2 text-p-base text-gray-800">
							If you don't want to add your card on file, you can select Prepaid
							as your payment method and buy credits upfront.
						</p>

						<div class="mt-4 flex items-center space-x-2">
							<Button @click="showAddCardDialog = true">Postpaid</Button>
							<Button @click="showBuyCreditsDialog = true">Prepaid</Button>
						</div>
					</div>
				</div>
				<div v-else>
					<div class="flex items-center justify-between space-x-2">
						<div class="flex items-center space-x-2">
							<TextInsideCircle>2</TextInsideCircle>
							<span class="text-base font-medium">
								Payment method set as {{ $team.doc.payment_mode }}
							</span>
						</div>
						<div
							class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
						>
							<i-lucide-check class="h-3 w-3 text-white" />
						</div>
					</div>
					<div class="mt-1.5 pl-7 text-p-base text-gray-800">
						Account balance: {{ $format.userCurrency($team.doc.balance) }}
					</div>
				</div>
			</div>
			<div
				v-if="!$team.doc.is_saas_user"
				class="rounded-md"
				:class="{ 'pointer-events-none opacity-50': !$team.doc.payment_mode }"
			>
				<div class="flex items-center space-x-2">
					<TextInsideCircle>3</TextInsideCircle>
					<div class="text-base font-medium">Create a site</div>
				</div>

				<div class="pl-7">
					<p class="mt-2 text-p-base text-gray-800">
						You can now create sites and benches from the dashboard. Go ahead
						and try it.
					</p>
					<Button class="mt-2" :route="{ name: 'NewSite' }">
						Create a new site
					</Button>
				</div>
			</div>
		</div>
		<Dialog
			v-model="showAddCardDialog"
			:options="{ title: 'Add card for postpaid setup' }"
		>
			<template #body-content>
				<StripeCard2 />
			</template>
		</Dialog>
		<BuyPrepaidCreditsDialog
			v-model="showBuyCreditsDialog"
			:minimumAmount="minimumAmount"
			@success="onBuyCreditsSuccess"
		/>
	</div>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import TextInsideCircle from './TextInsideCircle.vue';

export default {
	name: 'Onboarding',
	components: {
		StripeCard2: defineAsyncComponent(() =>
			import('../components/StripeCard.vue')
		),
		BuyPrepaidCreditsDialog: defineAsyncComponent(() =>
			import('../components/BuyPrepaidCreditsDialog.vue')
		),
		TextInsideCircle
	},
	data() {
		return {
			showAddCardDialog: false,
			showBuyCreditsDialog: false
		};
	},
	methods: {
		onBuyCreditsSuccess() {
			this.$team.reload();
			this.showBuyCreditsDialog = false;
		}
	},
	computed: {
		free_credits() {
			return this.$format.userCurrency(
				this.$team.doc.currency == 'INR'
					? window.free_credits_inr
					: window.free_credits_usd
			);
		},
		minimumAmount() {
			return this.$team.doc.currency == 'INR' ? 100 : 5;
		}
	}
};
</script>
