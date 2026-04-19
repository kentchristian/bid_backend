from rest_framework import serializers


def field_lookup(slug_field, Model, source=None):
  extra_kwargs = {}

  if source is not None:
    extra_kwargs['source'] = source
  
  item = serializers.SlugRelatedField(
    slug_field=slug_field,
    queryset=Model.objects.all()
    **extra_kwargs
  )
  return item
