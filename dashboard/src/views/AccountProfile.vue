<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Profile</h2>
			<p class="text-gray-600">Your profile information</p>
			<div class="w-full sm:w-1/2 mt-6 text-sm">
				<div>
					<span class="text-gray-800">Photo</span>
					<div class="mt-2 flex items-center">
						<Avatar
							size="lg"
							:label="account.user.first_name"
							:imageURL="account.user.image"
						/>
						<input
							ref="userImage"
							type="file"
							accept="image/*"
							class="hidden"
							@change="onUserImage"
						/>
						<Button
							class="ml-4 border hover:bg-gray-100"
							:disabled="uploading"
							@click="$refs.userImage.click()"
						>
							<span v-if="uploading">
								Uploading {{ Math.floor((uploaded / total) * 100) }}%
							</span>
							<span v-else>Change</span>
						</Button>
					</div>
				</div>
				<div class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
					<label class="block">
						<span class="text-gray-800">First Name</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="text"
							v-model="account.user.first_name"
						/>
					</label>
					<label class="block">
						<span class="text-gray-800">Last Name</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="text"
							v-model="account.user.last_name"
						/>
					</label>
				</div>
				<label class="mt-4 block">
					<span class="text-gray-800">Email Address</span>
					<input
						class="mt-2 form-input block w-full shadow"
						type="text"
						v-model="account.user.email"
					/>
				</label>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Notifications</h2>
			<p class="text-gray-600">
				We send only important changes, but you can choose what you want to hear
				about.
			</p>
			<div class="w-full sm:w-1/2 mt-6">
				<div class="block">
					<div>
						<div class="py-2">
							<label class="inline-flex items-center">
								<input type="checkbox" class="form-checkbox" checked />
								<span class="ml-2">Weekly usage summary</span>
							</label>
						</div>
						<div class="py-2">
							<label class="inline-flex items-center">
								<input type="checkbox" class="form-checkbox" />
								<span class="ml-2">Critical action required</span>
							</label>
						</div>
						<div class="py-2">
							<label class="inline-flex items-center">
								<input type="checkbox" class="form-checkbox" />
								<span class="ml-2">Site goes down</span>
							</label>
						</div>
					</div>
				</div>
			</div>
		</section>
		<div class="border-t mt-10 py-4">
			<Button
				class="bg-brand hover:bg-blue-600 text-white"
				@click="$store.account.updateProfile"
			>
				Save changes
			</Button>
			<Button class="ml-2 border hover:bg-gray-100">Cancel</Button>
		</div>
	</div>
</template>

<script>
import FileUploader from '@/store/fileUploader';

export default {
	name: 'AccountProfile',
	props: ['account'],
	data() {
		return {
			uploader: null,
			userImage: null,
			uploading: false,
			uploaded: 0,
			total: 0
		};
	},
	methods: {
		onUserImage(e) {
			let file = e.target.files[0];
			this.uploadFile(file);
		},
		async uploadFile(file) {
			this.uploader = new FileUploader();
			this.uploader.on('start', () => {
				this.uploading = true;
			});
			this.uploader.on('progress', data => {
				this.uploaded = data.uploaded;
				this.total = data.total;
			});
			this.uploader.on('error', () => {
				this.uploading = false;
			});
			this.uploader.on('finish', () => {
				this.uploading = false;
			});
			let fileDoc = await this.uploader.upload(file, {
				doctype: 'User',
				docname: this.$store.account.user.name
			});
			if (fileDoc.file_url) {
				await this.$call('press.api.account.update_profile_picture', {
					image_url: fileDoc.file_url
				});
				await this.$store.account.fetchAccount();
			}
		}
	}
};
</script>
