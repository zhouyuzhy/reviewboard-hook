from rest_framework import serializers

class Result(object):
    def __init__(self, result):
        self.result = result

class ResultSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Result
        fields = ('result')

