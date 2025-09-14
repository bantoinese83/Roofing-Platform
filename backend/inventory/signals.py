from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from quotes.models import QuoteItem
from jobs.models import Job
from .models import InventoryItem, StockTransaction


@receiver(post_save, sender=QuoteItem)
def update_inventory_on_quote_item_save(sender, instance, created, **kwargs):
    """
    Update inventory stock when a quote item is created or modified.
    This is a placeholder - actual stock updates would happen when jobs are completed.
    """
    pass


@receiver(post_save, sender=Job)
def update_inventory_on_job_completion(sender, instance, created, **kwargs):
    """
    Update inventory stock when a job is marked as completed.
    This would typically deduct materials used from inventory.
    """
    if instance.status == 'completed' and not created:
        # Check if this is a status change to completed
        try:
            old_job = Job.objects.get(pk=instance.pk)
            if old_job.status != 'completed':
                # Job was just completed - deduct materials from inventory
                _deduct_materials_for_job(instance)
        except Job.DoesNotExist:
            pass


def _deduct_materials_for_job(job):
    """
    Deduct materials used for a completed job from inventory.
    This is a simplified implementation - in a real system, you'd track
    actual materials used per job.
    """
    # This would typically involve:
    # 1. Getting the materials associated with the job type
    # 2. Calculating quantities used
    # 3. Updating inventory stock

    # For now, this is a placeholder
    pass


@receiver(pre_save, sender=InventoryItem)
def track_inventory_changes(sender, instance, **kwargs):
    """
    Track inventory changes for audit purposes.
    """
    if instance.pk:
        try:
            old_instance = InventoryItem.objects.get(pk=instance.pk)
            if old_instance.current_stock != instance.current_stock:
                # Stock level changed - this should be tracked via update_stock method
                # rather than direct field modification
                pass
        except InventoryItem.DoesNotExist:
            pass
