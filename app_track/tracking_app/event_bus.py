
import logging
from django.utils import timezone
from .models import AutomationRule, AutomationLog
from .tasks import execute_automation_action

logger = logging.getLogger(__name__)

def evaluate_condition(condition, payload):
    field = condition.get('field')
    op = condition.get('operator')
    expected = condition.get('value')
    
    actual = payload.get(field)
    if actual is None:
        return False
        
    try:
        if op == 'equals':
            return str(actual).lower() == str(expected).lower()
        elif op == 'contains':
            return str(expected).lower() in str(actual).lower()
        elif op == 'gt':
            return float(actual) > float(expected)
        elif op == 'lt':
            return float(actual) < float(expected)
    except Exception as e:
        logger.error(f"EventBus Evaluation Error: {e}")
        return False
        
    return False

def dispatch_event(tenant, event_type, payload):
    """
    Central Event Bus.
    Evaluates rules and dispatches Celery tasks.
    """
    if not tenant:
        return
        
    rules = AutomationRule.objects.filter(tenant=tenant, trigger_type=event_type, is_active=True)
    
    for rule in rules:
        # Evaluate all conditions (AND logic)
        conditions_met = True
        for cond in rule.conditions:
            if not evaluate_condition(cond, payload):
                conditions_met = False
                break
                
        if conditions_met:
            # Trigger Actions via Celery
            for action in rule.actions:
                execute_automation_action.delay(
                    rule_id=rule.id,
                    tenant_id=tenant.id,
                    action=action,
                    payload=payload
                )
