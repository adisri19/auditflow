from apps.audit.models import AuditLog

def log_action(request, record, action, before_state=None, after_state=None):
    actor = request.user if request and request.user.is_authenticated else None
    
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

    return AuditLog.objects.create(
        tenant=record.tenant,
        activity_record=record,
        actor=actor,
        action=action,
        before_state=before_state,
        after_state=after_state,
        ip_address=ip
    )
