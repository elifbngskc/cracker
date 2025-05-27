from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, ProfileForm
from tracker.models import Profile
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from .tokens import email_verification_token
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth import login
from email.utils import formataddr



def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            current_site = get_current_site(request)
            mail_subject = 'Activate your account'
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = email_verification_token.make_token(user)

            activation_link = reverse('activate', kwargs={'uidb64': uid, 'token': token})
            activation_url = f"http://{current_site.domain}{activation_link}"

            message = render_to_string('users/activation_email.html', {
                'user': user,
                'activation_url': activation_url,
            })

            email = EmailMessage(
                mail_subject,
                message,
                from_email=formataddr(("Cracker App", "info@crackerapp.atelieralice.net")),
                to=[user.email]
            )
            email.content_subtype = 'html'  # This ensures the email is rendered as HTML
            email.send()

            messages.success(request, 'Account created! Please confirm your email to activate your account.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, 'Your account has been activated!')
        return redirect('profile')
    else:
        messages.error(request, 'Activation link is invalid or expired.')
        return redirect('login')

@login_required
def profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    ideal_wt = profile.ideal_weight_devine()


    context = {
        'profile': profile,
        'daily_calories': round(profile.daily_calories()),
        'daily_macros': profile.daily_macros(),
        "ideal_weight": ideal_wt,}
    
    return render(request, 'users/profile.html', context)

def edit_profile(request):
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'users/edit_profile.html', {'form': form})