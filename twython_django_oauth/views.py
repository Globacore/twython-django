from django.contrib.auth import authenticate, login, logout as django_logout
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.conf import settings
from django.core.urlresolvers import reverse

from twython import Twython

# If you've got your own Profile setup, see the note in the models file
# about adapting this to your own setup.
from twython_django_oauth.models import TwitterProfile


def logout(request, redirect_url=settings.LOGOUT_REDIRECT_URL):
    """
        Nothing hilariously hidden here, logs a user out. Strip this out if your
        application already has hooks to handle this.
    """
    django_logout(request)
    return HttpResponseRedirect(request.build_absolute_uri(redirect_url))


def begin_auth(request):
    """
        The view function that initiates the entire handshake.
        For the most part, this is 100% drag and drop.
    """
    # Instantiate Twython with the first leg of our trip.
    twitter = Twython(
        twitter_token=settings.TWITTER_KEY,
        twitter_secret=settings.TWITTER_SECRET,
        callback_url=request.build_absolute_uri(reverse('twython_django_oauth.views.thanks'))
    )

    # Request an authorization url to send the user to...
    auth_props = twitter.get_authentication_tokens(force_login=True)

    # Then send them over there, durh.
    request.session['request_token'] = auth_props
    return HttpResponseRedirect(auth_props['auth_url'])


def thanks(request, redirect_url=settings.LOGIN_REDIRECT_URL):
    """
        A user gets redirected here after hitting Twitter and authorizing your
        app to use their data.

        ***
            This is the view that stores the tokens you want
            for querying data. Pay attention to this.
        ***
    """
    # Now that we've got the magic tokens back from Twitter, we need to exchange
    # for permanent ones and store them...
    twitter = Twython(
        twitter_token=settings.TWITTER_KEY,
        twitter_secret=settings.TWITTER_SECRET,
        oauth_token=request.session['request_token']['oauth_token'],
        oauth_token_secret=request.session['request_token']['oauth_token_secret'],
    )

    # Retrieve the tokens we want...
    authorized_tokens = twitter.get_authorized_tokens(request.GET['oauth_verifier'])
    user_id = int(authorized_tokens['user_id'])

    try:
        profile = TwitterProfile.objects.get(user_id=user_id)
        profile.oauth_token = authorized_tokens['oauth_token']
        profile.oauth_secret = authorized_tokens['oauth_token_secret']
        profile.screen_name = authorized_tokens['screen_name']
        profile.save()
    except TwitterProfile.DoesNotExist:
        profile = TwitterProfile()
        profile.user = request.user
        profile.oauth_token = authorized_tokens['oauth_token']
        profile.oauth_secret = authorized_tokens['oauth_token_secret']
        profile.screen_name = authorized_tokens['screen_name']
        profile.user_id = authorized_tokens['user_id']
        profile.save()

    return HttpResponseRedirect(reverse(redirect_url))


def user_timeline(request):
    """
        An example view with Twython/OAuth hooks/calls to fetch data about the user
        in question. Pretty self explanatory if you read through it...
    """
    user = request.user.twitterprofile
    twitter = Twython(
        twitter_token=settings.TWITTER_KEY,
        twitter_secret=settings.TWITTER_SECRET,
        oauth_token=user.oauth_token,
        oauth_token_secret=user.oauth_secret
    )
    user_tweets = twitter.getHomeTimeline()
    return render_to_response('tweets.html', {'tweets': user_tweets})
