from django import forms
from django.conf import settings

from django.contrib.auth.models import User

from friends.models import FriendshipInvitation

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None


class UserForm(forms.Form):

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(UserForm, self).__init__(*args, **kwargs)


class InviteFriendForm(UserForm):

    to_user = forms.CharField(widget=forms.HiddenInput)
    message = forms.CharField(
        label="Message",
        required=False,
        widget=forms.Textarea(attrs={"cols": "20", "rows": "5"})
    )

    def clean_to_user(self):
        to_username = self.cleaned_data["to_user"]
        try:
            User.objects.get(username=to_username)
        except User.DoesNotExist:
            raise forms.ValidationError(u"Unknown user.")
        return self.cleaned_data["to_user"]

    def clean(self):
        to_user = User.objects.get(username=self.cleaned_data["to_user"])
        previous_invitations_to = FriendshipInvitation.objects.invitations(
            to_user=to_user,
            from_user=self.user,
        )
        if previous_invitations_to.count() > 0:
            raise forms.ValidationError(
                u"Already requested friendship with %s" % to_user.username
            )
        # check inverse
        previous_invitations_from = FriendshipInvitation.objects.invitations(
            to_user=self.user,
            from_user=to_user,
        )
        if previous_invitations_from.count() > 0:
            raise forms.ValidationError(
                u"%s has already requested friendship with you" % to_user.username
            )
        return self.cleaned_data

    def save(self):
        to_user = User.objects.get(username=self.cleaned_data["to_user"])
        message = self.cleaned_data["message"]
        invitation = FriendshipInvitation(
            from_user=self.user,
            to_user=to_user,
            message=message,
            status="2"
        )
        invitation.save()
        if notification:
            notification.send([to_user], "friends_invite", {"invitation": invitation})
            notification.send([self.user], "friends_invite_sent", {
                "invitation": invitation
            })
        self.user.message_set.create(
            message="Friendship requested with %s" % to_user.username
        )  # @@@ make link like notification
        return invitation
