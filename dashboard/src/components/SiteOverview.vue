<template>
	<div
		v-if="$site?.doc"
		class="grid grid-cols-1 items-start gap-5 lg:grid-cols-2"
	>
		<CustomAlerts
			:disable-last-child-bottom-margin="true"
			container-class="col-span-1 lg:col-span-2"
			ctx_type="Site"
			:ctx_name="[$site?.doc?.name, $site?.doc.server, $site?.doc?.cluster]"
		/>
		<AlertBanner
			v-if="$site?.doc?.creation_failed"
			class="col-span-1 lg:col-span-2"
			type="error"
			:title="`La création du site a échoué. Vous pouvez restaurer le site à partir d'une sauvegarde (d'un autre site) ou supprimer ce site pour en créer un nouveau. Le site sera automatiquement supprimé après ${$site?.doc?.creation_failure_retention_days} jours s'il n'est pas restauré.`"
		> </AlertBanner>

		<AlertBanner
			v-if="$site?.doc?.status === 'Suspended' && $site?.doc?.suspension_reason"
			class="col-span-1 lg:col-span-2"
			type="error"
			:title="`Raison de la suspension : ${$site?.doc?.suspension_reason || 'Non spécifié'}`"
		>
			<Button
				class="ml-auto min-w-[7rem]"
				variant="outline"
				link="https://docs.frappe.io/cloud/faq/site#my-site-is-suspended-what-do-i-do"
			>
				More Info
			</Button>
		</AlertBanner>

		<AlertBanner
			v-if="$site?.doc?.status === 'Active' && $site?.doc?.site_usage_exceeded"
			class="col-span-1 lg:col-span-2"
			type="warning"
			title="Les limites d'utilisation de la base de données ou du disque sont dépassées. Améliorez votre plan ou réduisez l'utilisation pour éviter la suspension."
		>
			<Button
				class="ml-auto min-w-[7rem]"
				variant="outline"
				link="https://docs.frappe.io/cloud/faq/site#my-site-is-suspended-what-do-i-do"
			>
				More Info
			</Button>
		</AlertBanner>

		<AlertBanner
			v-if="$site.doc.is_monitoring_disabled && $site.doc.status !== 'Archived'"
			class="col-span-1 lg:col-span-2"
			title="Site monitoring is disabled, which means we won’t be able to notify you of any downtime. Please re-enable monitoring at your earliest convenience."
			:id="$site.name"
			type="warning"
		> </AlertBanner>
		<DismissableBanner
			v-else-if="$site.doc.eol_versions.includes($site.doc.version)"
			class="col-span-1 lg:col-span-2"
			title="Votre site est sur une version en fin de vie. Passez à la dernière version pour bénéficier du support, des dernières fonctionnalités et des mises à jour de sécurité."
			:id="`${$site.name}-eol`"
		>
			<Button
				class="ml-auto min-w-[7rem]"
				variant="outline"
				link="https://docs.frappe.io/cloud/sites/version-upgrade"
			>
				Upgrade Now
			</Button>
		</DismissableBanner>
		<DismissableBanner
			v-else-if="
				$site.doc.current_plan &&
				!$site.doc.current_plan?.private_benches &&
				$site.doc.group_public &&
				!$site.doc.current_plan?.is_trial_plan &&
				$site.doc.status !== 'Archived'
			"
			class="col-span-1 lg:col-span-2"
			title="Your site is currently on a shared bench. Upgrade plan to enjoy <a href='https://frappecloud.com/shared-hosting#benches' class='underline' target='_blank'>more benefits</a>."
			:id="$site.name"
			type="gray"
		>
			<Button class="ml-auto" variant="outline" @click="showPlanChangeDialog">
				Changer de plan
			</Button>
		</DismissableBanner>

		<DismissableBanner
			v-else-if="
				$site.doc.current_plan &&
				$site.doc.current_plan?.private_benches &&
				$site.doc.group_public &&
				$site.doc.status !== 'Archived'
			"
			class="col-span-1 lg:col-span-2"
			title="Your site is eligible to move to a private bench with server scripts and custom apps support enabled."
			:id="$site.name"
		>
			<Button class="ml-auto" variant="outline" @click="moveToPrivateBench">
				Passer au Bench privé
			</Button>
		</DismissableBanner>

		<div class="col-span-1 rounded-md border lg:col-span-2">
			<div class="grid grid-cols-2 lg:flex lg:*:flex-grow">
				<div class="border-b border-r p-5 lg:border-b-0">
					<div class="flex h-full items-center justify-between">
						<div>
							<div class="text-base text-ink-gray-7">Plan actuel</div>

							<div class="mt-2 flex justify-between">
								<div>
									<div class="leading-4">
										<span class="flex items-center text-base text-ink-gray-9">
											<template v-if="$site.doc.is_dedicated_server">
												Site sur serveur dédié
											</template>

											<template v-else-if="$site.doc.trial_end_date">
												{{ trialDays($site.doc.trial_end_date) }}
											</template>

											<template v-else-if="currentPlan">
												{{ $format.planTitle(currentPlan) }}

												<span v-if="currentPlan.price_dzd && $isMobile">
													/mo
												</span>

												<span v-if="currentPlan.price_dzd && !$isMobile">
													/mois
												</span>
											</template>

											<template v-else> Aucun plan défini </template>

											<div
												class="ml-2 text-sm leading-3 text-ink-gray-6"
												v-if="
											currentPlan &&
											currentPlan.support_included &&
											!currentPlan.is_trial_plan
											"
											>
												<Tooltip text="Support produit inclus">
													<lucide-badge-check class="h-4 w-4" />
												</Tooltip>
											</div>
										</span>
									</div>
								</div>
							</div>
						</div>
						<template v-if="!$site.doc.is_dedicated_server">
							<Button @click="showPlanChangeDialog">
								{{ currentPlan?.is_trial_plan ? 'Mettre à jour' : 'Changer' }}
							</Button>
						</template>
						<template v-else>
							<Tooltip
								text="Aucun plan individuel nécessaire pour les sites sur serveurs dédiés"
							>
								<LucideHelpCircle class="size-4" />
							</Tooltip>
						</template>
					</div>
				</div>
				<div
					v-if="$site.doc.is_dedicated_server"
					class="border-b p-5 lg:border-b-0 lg:border-r"
				>
					<div
						class="flex items-center justify-between text-base text-ink-gray-7"
					>
						<span>Calcul</span>
						<div class="h-7"></div>
					</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.cpu / currentPlan.cpu_time_per_day) * 100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-ink-gray-6">
									{{ currentUsageLoading ? '—' : currentUsage.cpu }}
									{{ $format.plural(currentUsage.cpu, 'hour', 'hours') }}
									<template
										v-if="currentPlan && !$site.doc.is_dedicated_server"
									>
										of {{ currentPlan?.cpu_time_per_day }} hours
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="border-r p-5">
					<div
						class="flex items-center justify-between text-base text-ink-gray-7"
					>
						<div class="flex w-full">
							<div class="flex-grow">Stockage objet</div>

							<Tooltip
								text="Inclut les téléchargements de fichiers privés et publics et les sauvegardes"
							>
								<LucideHelpCircle class="inline size-4 ml-2" />
							</Tooltip>

							<div class="h-7"></div>
						</div>
					</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.storage / currentPlan.max_storage_usage) * 100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-ink-gray-6">
									{{ currentUsageLoading
											? '—'
											: formatBytes(currentUsage.storage) }}
									<template
										v-if="currentPlan && !$site.doc.is_dedicated_server"
									>
										of {{ formatBytes(currentPlan.max_storage_usage) }}
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="p-5">
					<div
						class="min-h-[1.75rem] flex items-center justify-between space-x-2"
					>
						<span class="text-base text-ink-gray-7">Base de données</span>
						<div class="flex items-center space-x-2">
							<Button
								v-if="
									(currentPlan
										? (currentUsage.database / currentPlan.max_database_usage) *
											100
										: 0) >= 80
								"
								variant="ghost"
								link="https://docs.frappe.io/cloud/faq/site#what-is-using-up-all-my-database-size"
								icon="help-circle"
							/>
							<Button
								variant="ghost"
								icon="refresh-ccw"
								@click="refreshDatabaseUsage"
								:loading="refreshingDatabaseUsage"
							/>
						</div>
					</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.database / currentPlan.max_database_usage) *
										100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-ink-gray-6">
									{{ currentUsageLoading
											? '—'
											: formatBytes(currentUsage.database) }}
									<template
										v-if="currentPlan && !$site.doc.is_dedicated_server"
									>
										of
										{{ formatBytes(currentPlan.max_database_usage) }}
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-ink-gray-9">Informations du site</h2>
			</div>
			<div>
				<div
					v-for="d in siteInformation"
					:key="d.label"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-surface-gray-1"
				>
					<div class="w-1/3 text-base text-ink-gray-6">{{ d.label }}</div>
					<div
						class="flex w-2/3 items-center space-x-2 text-base text-ink-gray-9"
					>
						<div v-if="d.prefix">
							<component :is="d.prefix" />
						</div>
						<span> {{ d.value }} </span>
						<div v-if="d.suffix">
							<component :is="d.suffix" />
						</div>
					</div>
				</div>
			</div>
		</div>

		<SiteDailyUsage :site="site" />

		<!-- Tags -->
		<div class="col-span-1 flex items-center space-x-2 lg:col-span-2">
			<Badge
				v-for="tag in $site.doc.tags"
				:key="tag.tag"
				:label="tag.tag_name"
				size="lg"
				class="group"
			>
				<template #suffix>
					<button
						@click="removeTag(tag)"
						class="ml-1 hidden transition group-hover:block"
					>
						<lucide-x class="mt-0.5 h-3 w-3" />
					</button>
				</template>
			</Badge>
			<Badge
				variant="outline"
				size="lg"
				label="Ajouter un tag"
				class="cursor-pointer"
				@click="showAddTagDialog"
			>
				<template #suffix>
					<lucide-plus class="h-3 w-3" />
				</template>
			</Badge>
		</div>
	</div>
</template>
<script>
import { getCachedDocumentResource, Progress, Tooltip } from 'frappe-ui'
import { defineAsyncComponent, h } from 'vue'
import { toast } from 'vue-sonner'
import InfoIcon from '~icons/lucide/info'
import { renderDialog } from '../utils/components'
import { trialDays } from '../utils/site'
import { getToastErrorMessage } from '../utils/toast'
import AlertBanner from './AlertBanner.vue'
import CustomAlerts from './CustomAlerts.vue'
import DismissableBanner from './DismissableBanner.vue'
import SiteDailyUsage from './SiteDailyUsage.vue'

export default {
	name: 'SiteOverview',
	props: ['site'],
	components: {
		SiteDailyUsage,
		Progress,
		AlertBanner,
		DismissableBanner,
		CustomAlerts,
	},
	data() {
		return {
			isSetupWizardComplete: true,
			refreshingDatabaseUsage: false,
		}
	},
	mounted() {
		if (this.$site?.doc?.status === 'Active') {
			this.$site.isSetupWizardComplete.submit().then((res) => {
				this.isSetupWizardComplete = res
			})
		}
	},
	methods: {
		showPlanChangeDialog() {
			let SitePlansDialog = defineAsyncComponent(
				() => import('../components/ManageSitePlansDialog.vue'),
			)
			renderDialog(h(SitePlansDialog, { site: this.site }))
		},
		moveToPrivateBench() {
			let SiteMigrationDialog = defineAsyncComponent(
				() => import('./site/SiteMigration.vue'),
			)
			const defaultBenchName = this.$site?.doc?.group_title
				? `${this.$site.doc.group_title} - Cloned`
				: null
			renderDialog(
				h(SiteMigrationDialog, {
					site: this.site,
					defaultAction: 'Move Site To Different Server / Bench',
					defaultNewBenchName: defaultBenchName,
				}),
			)
		},
		showEnableMonitoringDialog() {
			let SiteEnableMonitoringDialog = defineAsyncComponent(
				() => import('./site/SiteEnableMonitoringDialog.vue'),
			)
			renderDialog(h(SiteEnableMonitoringDialog, { site: this.site }))
		},
		formatBytes(v) {
			return this.$format.bytes(v, 2, 2)
		},
		loginAsAdmin() {
			this.$site.loginAsAdmin
				.submit({ reason: '' })
				.then((url) => window.open(url, '_blank'))
		},
		loginAsTeam() {
			if (this.$site.doc?.additional_system_user_created) {
				this.$site.loginAsTeam
					.submit({ reason: '' })
					.then((url) => window.open(url, '_blank'))
			} else {
				this.loginAsAdmin()
			}
		},
		removeTag(tag) {
			toast.promise(
				this.$site.removeTag.submit({
					tag: tag.tag_name,
				}),
				{
					loading: 'Suppression du tag...',
					success: `Tag ${tag.tag_name} retiré`,
					error: (e) => getToastErrorMessage(e),
				},
			)
		},
		showAddTagDialog() {
			const TagsDialog = defineAsyncComponent(
				() => import('../dialogs/TagsDialog.vue'),
			)
			renderDialog(h(TagsDialog, { doctype: 'Site', docname: this.site }))
		},
		trialDays,
		refreshDatabaseUsage() {
			this.refreshingDatabaseUsage = true
			this.$resources.refreshDatabaseUsage.submit()
		},
	},
	resources: {
		currentUsage() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'get_current_usage',
					}
				},
				auto: true,
			}
		},
		refreshDatabaseUsage() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'refresh_database_usage',
					}
				},
				onSuccess: (e) => {
					let isSynced = e?.message?.synced ?? true
					let refreshAfterSeconds = e?.message?.refresh_after_seconds ?? 0
					let refreshAfterMinutes = Math.ceil(refreshAfterSeconds / 60)
					if (isSynced) {
						this.refreshingDatabaseUsage = false
						let message = refreshAfterSeconds
							? `Utilisation de la base de données actualisée. Vous pouvez actualiser à nouveau après ${refreshAfterMinutes} minute(s).`
							: 'Utilisation de la base de données actualisée.'
						toast.success(message)
						this.$resources.currentUsage.reload()
					} else {
						setTimeout(() => {
							this.$resources.refreshDatabaseUsage.reload()
						}, 3000)
					}
				},
				auto: false,
			}
		},
	},
	computed: {
		siteInformation() {
			return [
				{
					label: 'Propriétaire',
					value: this.$site.doc?.owner_email,
				},
				{
					label: 'Créé par',
					value: this.$site.doc?.signup_by || this.$site.doc?.owner,
				},
				{
					label: 'Créé le',
					value: this.$format.date(
						this.$site.doc?.signup_time || this.$site.doc?.creation,
					),
				},
				{
					label: 'Région',
					value: this.$site.doc?.cluster.title,
					prefix: h('img', {
						src: this.$site.doc?.cluster.image,
						alt: this.$site.doc?.cluster.title,
						class: 'h-4 w-4',
					}),
				},
				{
					label: 'Inbound IP',
					value: this.$site.doc?.inbound_ip,
					suffix: h(
						Tooltip,
						{
							text: 'Utilisez ceci pour ajouter des enregistrements A pour votre site',
						},
						() => h(InfoIcon, { class: 'h-4 w-4 text-ink-gray-5' }),
					),
				},
				{
					label: 'Outbound IP',
					value: this.$site.doc?.outbound_ip,
					suffix: h(
						Tooltip,
						{
							text: 'Utilisez ceci pour ajouter notre serveur en liste blanche sur un service tiers',
						},
						() => h(InfoIcon, { class: 'h-4 w-4 text-ink-gray-5' }),
					),
				},
			]
		},
		currentPlan() {
			if (!this.$site?.doc?.current_plan || !this.$team?.doc) return null

			const currency = this.$team.doc.currency
			return {
				price:
					currency === 'DZD'
						? this.$site.doc.current_plan.price_dzd
						: this.$site.doc.current_plan.price_usd,
				price_per_day:
					currency === 'DZD'
						? this.$site.doc.current_plan.price_per_day_dzd
						: this.$site.doc.current_plan.price_per_day_usd,
				currency: currency === 'DZD' ? 'د.ج' : '$',
				...this.$site.doc.current_plan,
			}
		},
		currentUsage() {
			return (
				this.$resources?.currentUsage?.data?.message ?? {
					cpu: 0,
					storage: 0,
					database: 0,
				}
			)
		},
		currentUsageLoading() {
			return this.$resources?.currentUsage?.loading ?? true
		},
		$site() {
			return getCachedDocumentResource('Site', this.site)
		},
	},
}
</script>
