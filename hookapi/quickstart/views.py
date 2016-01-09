from rest_framework.decorators import detail_route, list_route
from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
import serializers
import hook

class HookView(viewsets.ViewSet):
    """
    A view that returns the count of active users in JSON.
    """

    #http://10.5.111.166:8000/hooks/rbt.json
    @list_route(methods=['get'], url_path='rbt')
    def get(self, request, format=None):
        rev = request.GET['rev']
        repos = request.GET['repos']
        hook.main(repos, rev)
        content = {'msg':'success'}
        return Response(content)

