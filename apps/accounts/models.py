from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Extends the built-in user with a role used for access control."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        MANAGER = "manager", "Manager"
        ACCOUNTANT = "accountant", "Accountant"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MANAGER)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Staff profile"
        verbose_name_plural = "Staff profiles"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.user.is_superuser


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, "profile"):
        Profile.objects.create(
            user=instance,
            role=Profile.Role.ADMIN if instance.is_superuser else Profile.Role.MANAGER,
        )
