import frappe
from frappe.model.document import Document
import yaml
import jinja2

class BareMetalVMTemplate(Document):
    def validate(self):
        self.validate_templates()
    
    def validate_templates(self):
        """Validate cloud-init templates"""
        templates = {
            'user_data_template': self.user_data_template,
            'meta_data_template': self.meta_data_template,
            'network_config_template': self.network_config_template
        }
        
        for template_name, template_content in templates.items():
            if not template_content:
                continue
                
            try:
                # Validate YAML syntax
                if template_name != 'meta_data_template':  # meta-data can be plain text
                    yaml.safe_load(template_content)
                
                # Validate Jinja2 syntax
                env = jinja2.Environment()
                env.parse(template_content)
            except yaml.YAMLError as e:
                frappe.throw(f"Invalid YAML in {template_name}: {str(e)}")
            except jinja2.TemplateError as e:
                frappe.throw(f"Invalid Jinja2 syntax in {template_name}: {str(e)}")
    
    def render_templates(self, context):
        """Render cloud-init templates with given context"""
        env = jinja2.Environment()
        templates = {
            'user_data': self.user_data_template,
            'meta_data': self.meta_data_template,
            'network_config': self.network_config_template
        }
        
        rendered = {}
        for name, template in templates.items():
            if not template:
                continue
            try:
                rendered[name] = env.from_string(template).render(context)
            except Exception as e:
                frappe.throw(f"Error rendering {name}: {str(e)}")
        
        return rendered 