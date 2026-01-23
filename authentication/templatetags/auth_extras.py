from django import template

register = template.Library()

@register.simple_tag
def can_manage_user(actor, target):
    """
    1. On ne peut pas se modifier soi-même.
    2. CEO > Tout le monde.
    3. Superuser > User lambda.
    4. Superuser != CEO et Superuser != Superuser.
    """
    if actor == target:
        return False
        
    is_actor_ceo = actor.groups.filter(name="CEO").exists()
    is_target_ceo = target.groups.filter(name="CEO").exists()
    is_target_superuser = target.is_superuser

    if is_actor_ceo:
        return True
    
    if is_target_ceo or is_target_superuser:
        return False
        
    return True
