from accounts.models import User
from api.serializers import UserSerializer


def get_users(tenant):
  query_set = User.objects.all().filter(tenant__name=tenant)
  users = UserSerializer(query_set, many=True).data

  return users;


  