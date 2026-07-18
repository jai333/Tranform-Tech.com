import re
import os

def update_model(filepath, models_to_update, tenant_import=""):
    with open(filepath, 'r') as f:
        content = f.read()

    if tenant_import and tenant_import not in content:
        content = content.replace("from django.db import models", f"from django.db import models\n{tenant_import}")

    for model in models_to_update:
        pattern = rf"(class {model}\(models\.Model\):.*?)(?=\n    def |\nclass |\n$)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            cls_content = match.group(1)
            if "tenant = models.ForeignKey(" not in cls_content:
                if "sales_models" in filepath:
                    fk_str = "\n    tenant = models.ForeignKey('tracking_app.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='%(class)ss')\n"
                else:
                    fk_str = "\n    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='%(class)ss')\n"
                
                new_cls_content = cls_content + fk_str
                content = content.replace(cls_content, new_cls_content)

    with open(filepath, 'w') as f:
        f.write(content)

update_model("tracking_app/models.py", ["Candidate", "Job", "Ticket"])
update_model("tracking_app/sales_models.py", ["Lead", "Account"])
print("Updated models with tenant FK")
