from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.http import JsonResponse
import json
import datetime

from .models import User, Post, Comment, Like, Follow


def index(request):
    return render(request, "network/index.html")


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")

@login_required
def post(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    data = json.loads(request.body)
    content = data.get('content')
    if content == '':
        return JsonResponse({"error": "Post requires content"}, status = 400 )
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Must be authenticated to post"}, status = 400)
    post = Post(
        author = request.user,
        content = content,
        timestamp = datetime.datetime.now(),
        likes = 0
    )
    post.save()
    return JsonResponse({"message": "Post Success", "status": 200}, status=200)

def get_posts(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    # posts = Post.objects.all()
    # posts = posts.order_by("-timestamp").all()
    # return JsonResponse([post.serialize() for post in posts], safe=False)

    data = json.loads(request.body)
    page = data.get('page')
    items_per_page = 10 
    start_index = (page - 1) * items_per_page
    end_index = page * items_per_page
    
    posts = Post.objects.all()
    total_posts = posts.count()

    posts = posts.order_by("-timestamp").all()
    posts_subset = posts[start_index:end_index]
    return JsonResponse({
        "data": [post.serialize() for post in posts_subset],
        "total_posts": total_posts
    }, safe=False)

def get_posts_by_user(request, username):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    user = User.objects.get(username=username)
    posts = Post.objects.filter(author=user)
    posts = posts.order_by("-timestamp").all()

    data = json.loads(request.body)
    page = data.get('page')
    items_per_page = 10 
    start_index = (page - 1) * items_per_page
    end_index = page * items_per_page
    
    total_posts = posts.count()
    posts_subset = posts[start_index:end_index]
    return JsonResponse({
        "data": [post.serialize() for post in posts_subset],
        "total_posts": total_posts
    }, safe=False)


    

@login_required
def like(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    post = Post.objects.get(id = post_id)
    like_exists = Like.objects.filter(user=request.user, post=post).exists()
    if like_exists:
        post.likes -= 1
        like = Like.objects.filter(user=request.user, post=post)
        like.delete()
    else:
        post.likes += 1
        like = Like(
            user=request.user,
            post=post
        )
        like.save()
    post.save()
    return JsonResponse({"message": "Like Success", "status": 200, "likes" : post.likes}, status=200)

@login_required
def isliked(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    post = Post.objects.get(id = post_id)
    like_exists = Like.objects.filter(user=request.user, post=post).exists()
    return JsonResponse({"message": "Like Success", "status": 200, "isliked" : like_exists}, status=200)

def user(request, username):
    user = User.objects.get(username = username)
    followers = Follow.objects.filter(following=user).count()
    following = Follow.objects.filter(follower=user).count()
    if request.user.is_authenticated:
        unfollow = Follow.objects.filter(follower=request.user, following=user).exists()
    else:
        unfollow = False
    return render(request, "network/user.html", {
        "user_data" : user,
        "followers": followers,
        "following": following,
        "unfollow": unfollow
    })

@login_required
def follow(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    data = json.loads(request.body)
    following_username = data.get('user_to_follow')
    following_user = User.objects.get(username=following_username)
    already_exists = Follow.objects.filter(follower = request.user, following = following_user).exists()
    if already_exists:
        return JsonResponse({"error": "Already following this user"}, status=400)
    follow_object = Follow(
        follower = request.user,
        following = following_user
    )
    follow_object.save()
    return JsonResponse({"message": "Follow Sucess", "status": 200}, status=200)

@login_required
def unfollow(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    data = json.loads(request.body)
    unfollowing_username = data.get('user_to_unfollow')
    unfollowing_user = User.objects.get(username=unfollowing_username)
    already_exists = Follow.objects.filter(follower = request.user, following = unfollowing_user).exists()
    if not already_exists:
        return JsonResponse({"error": "Cannot unfollow a user you don't follow"}, status=400)
    follow_object = Follow.objects.get(follower = request.user,following = unfollowing_user)
    follow_object.delete()
    return JsonResponse({"message": "Unfollow Sucess", "status": 200}, status=200)

@login_required
def get_posts_following(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    users_followed_by_current_user = request.user.following.all()
    posts = Post.objects.filter(author__in=users_followed_by_current_user)
    posts = posts.order_by("-timestamp").all()
    data = json.loads(request.body)
    page = data.get('page')
    items_per_page = 10 
    start_index = (page - 1) * items_per_page
    end_index = page * items_per_page
    
    total_posts = posts.count()
    posts_subset = posts[start_index:end_index]
    return JsonResponse({
        "data": [post.serialize() for post in posts_subset],
        "total_posts": total_posts
    }, safe=False)

@login_required
def following(request):
    return render(request, 'network/following.html')

@login_required
def edit(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    data = json.loads(request.body)
    content = data.get('new_content')
    if content == '':
        return JsonResponse({"error": "Post requires content"}, status = 400 )
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Must be authenticated to post"}, status = 400)
    post = Post.objects.get(id = post_id)
    post.content = content
    post.save()
    return JsonResponse({"message": "Post Success", "status": 200}, status=200)