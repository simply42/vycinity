# VyCinity

Backend for configuring VyOS' routers using a central, semantic REST interface. The state of this project is currently alpha, do not use this in production!

## How to use this and how development is done

This is a [Django App](https://www.djangoproject.com/). You need to add this to a Django-project to make use of this software. Currently this App is in a so early stage, there are no packages. This is planned when the whole app is more mature. You can try it out but the produced API is still not stable until annouced here. 

For a list of unmodified dependencies visit [requirements.txt](requirements.txt). Install them using `python3 -m pip install` or similar. After that, add the app and its dependencies into the list of your installed apps in the settings of the django settings:

```
INSTALLED_APPS = [
    # other apps here...
    'rest_framework',
    'polymorphic',
    'django.contrib.contenttypes',  # often already included
    'vycinity'
]
```

## OpenAPI Schema

This app makes use of the integrated api documentation mechanism resulting in a OpenAPI schema. After installing the dependencies, create the schema using the following command:

```
cd <your project>
python3 ./manage.py generateschema >schema.yml
```

## Licensing and Copyright

This app is developed in 2021 for WorNet AG, WorNet AG is the copyright holder, see [LICENSE](LICENSE) and [COPYING](COPYING) for details about licensing.