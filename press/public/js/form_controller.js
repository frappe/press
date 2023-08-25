class FormController {
	constructor(id, options) {
		this.id = id;
		this.options = options || {};
		this.$container = $(document.getElementById(id));
		this.no_of_steps = this.$container.find('form.form-step').length;
		this.setup_signup();
	}

	setup_signup() {
		// bind form submit events
		this.bind_form_submit();

		// show the last form
		let last_form_step = Number(localStorage.getItem(this.cacheKey));
		if (last_form_step && this.options.save_state) {
			this.show_form(last_form_step);
		} else {
			this.show_form(1);
		}

		// show msgprints in alert box
		this.handle_msgprint();
	}

	bind_form_submit() {
		$(this.$container)
			.find('form.form-step')
			.on('submit', (e) => {
				e.preventDefault();
				e.stopPropagation();

				let $form = $(e.target);
				let step_number = $form.data('step');
				let handler = this.get_object_from_attr($form, 'action');

				let values = this.get_form_values($form);
				if (!this.validate_form_values(values)) {
					// return if form has invalid values
					return;
				}
				let promise = handler($form, values);
				if (!promise || !promise.then) {
					promise = Promise.resolve();
				}
				promise.then(() => {
					let next_step = step_number + 1;
					if (next_step > this.no_of_steps) {
						localStorage.removeItem(this.cacheKey);
					} else {
						localStorage.setItem(this.cacheKey, next_step);
						this.show_form(step_number + 1);
					}
				});
			})
			.on('click', '.btn-back', (e) => {
				let $form = $(e.target).closest('.form-step');
				let step_number = $form.data('step');
				this.show_form(step_number - 1);
			});
	}

	get_object_from_attr($element, attr_name) {
		let object_name = $element.data(attr_name);
		let object = window[object_name];
		if (!object) {
			console.warn(`Global object "${attr_name}" not found`);
		}
		return object;
	}

	get cacheKey() {
		return `${this.id}--last_form-step`;
	}

	get_form_values($form) {
		let $inputs = $form.find('input[name], select[name], textarea[name]');
		let obj = {};
		$inputs.each((i, el) => {
			let $input = $(el);
			let value = $input.val();
			if ($input.is(':checkbox')) {
				value = $input.is(':checked');
			}
			obj[$input.prop('name')] = value;
		});
		return obj;
	}

	validate_form_values(values) {
		let is_valid = true;
		for (let field in values) {
			let value = values[field];
			let error = this.validate_value(field, value, values);

			if (error) {
				this.show_input_error(field, error);
				is_valid = false;
			} else {
				this.show_input_error(field, '');
			}
		}
		return is_valid;
	}

	validate_value(key, value, values) {
		let validators = this.get_object_from_attr(this.$container, 'validators');
		let validator = validators[key];
		let error = validator ? validator(value, values) : '';

		if (!error && value === '') {
			let $input = $(`[name=${key}]`);
			if ($input.attr('required')) {
				let id = $input.attr('id');
				let label = $(`label[for=${id}]`).text();
				error = `${label} cannot be blank`;
			}
		}
		return error;
	}

	show_form(number) {
		$('.form-alert-info, .form-alert-error').toggle(false);
		$('[data-step]').hide();
		$(`[data-step=${number}]`).show();

		// update indicator
		Array.from(new Array(number).fill(0)).forEach((d, i) => {
			let index = i + 1;
			$('.step-indicator:nth-child(' + index + ')')
				.addClass(index < number ? 'completed' : 'current')
				.removeClass(index < number ? 'current' : 'completed');
		});
	}

	handle_msgprint() {
		frappe.msgprint = (messages) => {
			if (!Array.isArray(messages)) {
				messages = [messages];
			}
			let info = '';
			let error = '';
			messages
				.map((m) => {
					try {
						return JSON.parse(m);
					} catch (e) {
						return { message: m };
					}
				})
				.forEach((m) => {
					if (m.raise_exception) {
						error += m.message + '<br />';
					} else {
						info += m.message + '<br />';
					}
				});
			$('.form-alert-info').html(info).toggle(Boolean(info));
			$('.form-alert-error').html(error).toggle(Boolean(error));
			$('#accountRequestButton').prop('disabled', false);
			$('#accountRequestButton').html('Create Account');
		};
		$('.form-alert-info, .form-alert-error').toggle(false);
	}

	show_input_feedback(name, message, is_error) {
		let $input = $(`[name="${name}"]`);
		$input.removeClass('is-invalid is-valid');
		let $error_message = $input.parent().find('.invalid-feedback');
		let $success_message = $input.parent().find('.valid-feedback');
		if ($error_message.length === 0) {
			$error_message = $('<div class="invalid-feedback">').appendTo(
				$input.parent(),
			);
		}
		if ($success_message.length === 0) {
			$success_message = $('<div class="valid-feedback">').appendTo(
				$input.parent(),
			);
		}
		$input.addClass(is_error ? 'is-invalid' : 'is-valid');
		$error_message.text(is_error ? message : '');
		$success_message.text(!is_error ? message : '');
	}

	show_input_error(name, message) {
		let $input = $(`[name="${name}"]`);
		$input.removeClass('is-invalid is-valid');
		let $message = $input.parent().find('.invalid-feedback');
		if ($message.length === 0) {
			$message = $('<div class="invalid-feedback">').appendTo($input.parent());
		}
		if (message) {
			$input.addClass('is-invalid');
			$message.text(message);
		} else {
			$message.text('');
		}
	}
}
